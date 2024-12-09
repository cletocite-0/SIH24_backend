import random
import subprocess
import tempfile
from typing import Callable
import uuid
import PyPDF2
from bs4 import BeautifulSoup
from fastapi import APIRouter, FastAPI
import pdfplumber
import requests
import os, dotenv
from langchain_community.document_loaders import YoutubeLoader
from langchain.text_splitter import TokenTextSplitter
from langchain.schema import Document
from neo4j import GraphDatabase
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import google.generativeai as genai
import requests
from io import BytesIO
import json
import websockets
import firebase_admin
from firebase_admin import credentials, storage

active_routes = {}


# Load environment variables from .env file
dotenv.load_dotenv()

# driver = GraphDatabase.driver(
#     os.environ["NEO4J_URI"],
#     auth=(os.environ["NEO4J_USERNAME"], os.environ["NEO4J_PASSWORD"]),
# )

uri = os.getenv("NEO4J_URI_EMBEDDINGS")  # Your Neo4j Aura URI
username = os.getenv("NEO4J_USERNAME_EMBEDDINGS")
password = os.getenv("NEO4J_PASSWORD_EMBEDDINGS")
driver = GraphDatabase.driver(uri, auth=(username, password))

# Get Firebase credentials from the environment
firebase_credentials_json = os.getenv("FIREBASE_CREDENTIALS_JSON")
firebase_credentials = json.loads(firebase_credentials_json)

# Initialize Firebase with the credentials from the environment
cred = credentials.Certificate(firebase_credentials)
firebase_admin.initialize_app(cred, {"storageBucket": "host-graph-image.appspot.com"})

# Access the storage bucket
bucket = storage.bucket()

# Atlassian API credentials
Atlassian_api_url = os.getenv("ATLASSIAN_API_URL")
Access_token = os.getenv("ACCESS_TOKEN")


def get_jina_embeddings(texts):
    url = "https://api.jina.ai/v1/embeddings"
    headers = {
        "Content-Type": "application/json",
        "Authorization": os.environ["JINA_AUTHORIZATION_KEY"],
    }
    data = {
        "model": "jina-clip-v1",
        "normalized": True,
        "embedding_type": "float",
        "input": [{"text": text} for text in texts],
    }

    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        response_json = response.json()
        embeddings = [item["embedding"] for item in response_json["data"]]
        return embeddings
    else:
        raise Exception(
            f"Error fetching embeddings: {response.status_code}, {response.text}"
        )


def perform_similarity_search(query_embedding, user_type, user_id=None, top_k=10):
    with driver.session() as session:
        if user_type == "common":
            result = session.run(
                """
                MATCH (c:Common)-[:HAS_DOCUMENT]->(d:Document)
                RETURN d.id AS id, d.content AS content, d.embedding AS embedding
            """
            )
        else:
            result = session.run(
                """
                MATCH (u:User)-[:HAS_USER]->(userID:UserID {id: $user_id})-[:HAS_DOCUMENT]->(d:Document)
                RETURN d.id AS id, d.content AS content, d.embedding AS embedding
            """,
                user_id=user_id,
            )

        documents = []
        embeddings = []

        for record in result:
            documents.append((record["id"], record["content"]))
            embeddings.append(record["embedding"])

        embeddings = np.array(embeddings)
        print(embeddings.shape)
        query_embedding = np.array(query_embedding).reshape(1, -1)
        distances = cosine_similarity(query_embedding, embeddings).flatten()

        # Get top_k results
        top_k_indices = np.argsort(distances)[-top_k:]
        top_docs = [
            (documents[i][0], documents[i][1], distances[i]) for i in top_k_indices
        ]

    return sorted(top_docs, key=lambda x: x[2], reverse=True)


# Function to get relevant context from the similarity search
def get_relevant_context(query_embedding, user_type, user_id=None):
    results = perform_similarity_search(query_embedding, user_type, user_id)
    context = ""
    for id, content, _ in results:
        context += content + "\n"
    return context


def store_embeddings_in_neo4j(documents, embeddings, user_id=None):
    with driver.session() as session:
        for i, (doc, embedding) in enumerate(zip(documents, embeddings)):
            session.run(
                """
                MERGE (u:User)
                MERGE (userID:UserID {id: $user_id})
                CREATE (d:Document {id: $id, content: $content, embedding: $embedding})
                MERGE (u)-[:HAS_USER]->(userID)
                MERGE (userID)-[:HAS_DOCUMENT]->(d)
                    """,
                user_id=user_id,
                id=i,
                content=doc.page_content,
                embedding=embedding,
            )


def get_prompt(context, query_text):
    return f"""
    You are a helpful assistant with access to specific documents. Please follow these guidelines:
    
    0. *Output*: Should be descriptive with respect to the question in three (3) lines.

    1. *Contextual Relevance*: Only provide answers based on the provided context. If the query does not relate to the context or if there is no relevant information, respond with "The query is not relevant to the provided context."

    2. *Language and Behavior*: Ensure that your response is polite and respectful. Avoid using any inappropriate language or making offensive statements.

    3. *Content Limitations*: Do not use or refer to any external data beyond the context provided.

    *Context*: {context}

    *Question*: {query_text}

    *Answer*:
    """


async def send_update_to_frontend(state, breakpoint_id):
    async with websockets.connect("ws://localhost:8765") as websocket:
        update = {"breakpoint_id": breakpoint_id, "state": state.to_dict()}
        await websocket.send(json.dumps(update))
        response = await websocket.recv()
        return json.loads(response)


def generate_ticket_id():
    return f"TICKET-{random.randint(1000,9999)}"


def send_to_gemini(pdf_text, user_query, save_dir, file_name):
    prompt = f"""
        You are given the following data from a PDF: {pdf_text}
        Based on the user's query: '{user_query}', provide executable Python code using matplotlib to generate the graph requested.
        
        The code should:
        1. Set a larger figure size to ensure all details are visible, e.g., figsize=(12, 8) or larger.
        2. Use a higher DPI to improve the image quality, e.g., dpi=150 or higher.
        3. Rotate x-axis labels by 45 degrees to avoid overlap and ensure readability, using plt.xticks(rotation=45, ha='right').
        4. Adjust x-axis label spacing if necessary to prevent overlap. Use plt.gca().xaxis.set_major_locator(plt.MaxNLocator(nbins=10)) or similar.
        5. Include plt.savefig() to save the graph to the folder '{save_dir}' with the filename '{file_name}'.
        6. Ensure the code is valid and will produce a clear, detailed graph.
        7. Dont include plt.show() anytime

        Only return valid Python code. Do not include explanations or numbered instructions, just the Python code snippet.
        """

    # Use Gemini API to get graph generation instructions
    model = genai.GenerativeModel("gemini-pro")
    response = model.generate_content(prompt)
    desc_prompt = f"""
        Summarize the following response in 3 sentences, highlighting key insights from the graph data. 
        Ensure there is no mention of "The graph is saved as an image file named 'output_graph.png' in the 'graph_img' directory." is excluded.
        This is the input text: {pdf_text}
        This is the Response: {response}
    """
    desc_response = model.generate_content(desc_prompt).text.strip()

    # Extract the code part (clean response)
    code_snippet = response.text.strip()
    print("Gemini Response Fetched")
    return code_snippet, desc_response


def extract_pdf_text(pdf_path):
    with open(pdf_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        print("PDF Text Extracted")
        return text


def pdf_to_documents(pdf_path):
    documents = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            raw_text = page.extract_text()
            if raw_text:
                document = Document(page_content=raw_text)
                documents.append(document)
    return documents


def upload_to_firebase(file_path, bucket_name):
    # Generate a unique file name using UUID
    unique_file_name = f"graphs/{uuid.uuid4().hex}.png"

    blob = bucket.blob(unique_file_name)
    blob.upload_from_filename(file_path)
    blob.make_public()
    return blob.public_url


def create_graph(instructions, file_path):
    # Clean the code snippet
    cleaned_instructions = (
        instructions.replace("```python", "").replace("```", "").strip()
    )

    # Print the cleaned instructions for debugging
    print("Cleaned Instructions")

    # Create a temporary file to hold the cleaned code snippet
    with tempfile.NamedTemporaryFile(delete=False, suffix=".py") as temp_file:
        temp_file.write(cleaned_instructions.encode("utf-8"))
        temp_file_path = temp_file.name

    try:
        # Execute the code from the temporary file
        result = subprocess.run(
            ["python", temp_file_path], capture_output=True, text=True
        )

        # Check if there were any errors during execution
        if result.returncode != 0:
            print(f"Error executing the code:\n{result.stderr}")
            return None

        print(f"Graph successfully generated and saved to {file_path}.")
        return file_path
    except Exception as e:
        print(f"Error generating the graph: {e}")
        return None
    finally:
        # Ensure the temporary file is removed even if an error occurs
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)


# app is mutable and so changes are reflected in master.py
# optional to return app
def add_route(app: FastAPI, path: str, method: Callable, method_name: str):
    """Add a route dynamically to the FastAPI app."""
    if path in active_routes:
        raise ValueError(f"Route {path} is already active.")

    # Create a new router for isolation
    router = APIRouter()

    # Add the route to the router
    router.add_api_route(path, method, methods=["POST"], name=method_name)

    # Include the router in the app
    app.include_router(router)

    # Store route info
    active_routes[path] = router


def remove_route(app: FastAPI, path: str):
    """Remove a route dynamically from the FastAPI app."""
    if path not in active_routes:
        raise ValueError(f"Route {path} is not active.")

    # Get the router associated with the path
    router = active_routes[path]

    # Remove the router from the app
    app.router.routes = [
        route for route in app.router.routes if route not in router.routes
    ]

    # Remove it from the registry
    del active_routes[path]


def get_cloudid():
    """Fetch the cloudid for your Atlassian instance."""
    url = f"{Atlassian_api_url}/oauth/token/accessible-resources"
    headers = {"Authorization": f"Bearer {Access_token}", "Accept": "application/json"}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        resources = response.json()
        for resource in resources:
            if (
                resource["name"] == "bhuvanannamalai73"
            ):  # Replace with your Confluence instance name
                print("cloud id :", resource["id"])
                return resource["id"]
    else:
        print(
            f"Failed to fetch cloudid. Status Code: {response.status_code}, Response: {response.text}"
        )
    return None


def fetch_page_content(cloudid, page_id):
    """Fetch the page content using cloudid and parse it with BeautifulSoup."""
    url = f"{Atlassian_api_url}/ex/confluence/{cloudid}/rest/api/content/{page_id}?expand=body.storage"
    headers = {"Authorization": f"Bearer {Access_token}", "Accept": "application/json"}

    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            html_content = (
                data.get("body", {})
                .get("storage", {})
                .get("value", "No content available")
            )

            # Parse the HTML content using BeautifulSoup
            soup = BeautifulSoup(html_content, "html.parser")

            # Extract and clean the content as needed
            for script in soup(["script", "style"]):
                script.decompose()

            cleaned_html = str(soup)
            print(f"Page Content Response (cleaned): {cleaned_html}")  # Debugging line
            return cleaned_html  # Return the cleaned HTML or text as needed
        else:
            print(
                f"Failed to fetch page content. Status Code: {response.status_code}, Response: {response.text}"
            )
    except Exception as e:
        print(f"Error while fetching page content: {e}")

    return None
