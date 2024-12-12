import os
import google.generativeai as genai
from langchain_groq import ChatGroq
from langchain_text_splitters import TokenTextSplitter
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import requests
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import os
import pickle
import io
import google.generativeai as genai
from PyPDF2 import PdfReader
from bs4 import BeautifulSoup
from neo4j import GraphDatabase
from neo4j import GraphDatabase
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import requests
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import os
import pickle
import io
import google.generativeai as genai
from PyPDF2 import PdfReader
from bs4 import BeautifulSoup


from agents.agents import Agent
from prompts.prompts import Prompt

from utils.utils import (
    extract_pdf_text,
    parse_json_string,
)

from nodes.nodes import update_knowledge_graph

response_generator_history = {}


async def response_generator(state):
    """
    Generates a response using the generative model.

    Args:
        state (dict): The state containing the query and message.

    Returns:
        dict: A dictionary containing the generated response.
    """
    # model = genai.GenerativeModel("gemini-1.5-pro")
    # chat_session = model.start_chat(history=[])
    # response = chat_session.send_message(state["question"], stream=True)
    # for chunk in response:
    #     print(chunk.text)
    #     yield chunk.text

    print("response_generator invoked")

    model = ChatGroq(
        temperature=0,
        model_name="gemma2-9b-it",
        api_key="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",
        streaming=True,
    )
    print(state["message"])

    response = await model.ainvoke(f"Draft response : \n{state['message']}")
    return {"generation": response}
    # response_generator_history["USER"] = state["question"]
    # response_generator_history["AI"] = response
    # print(response_generator_history)


def axel(state):
    """
    Invokes the Axel agent to generate a response.

    Args:
        state (dict): The state containing the role and query.

    Returns:
        dict: A dictionary containing the next action and message.
    """
    print("Axel invoked")
    if state["pdf"]:
        print("Upload has been detected")
        return {
            "next": "reviewer",
            "message": "I have detected an upload, Reviewer please assess the document.",
            "role": "axel",
            "generation": "",
        }

    Axel = Agent(
        agent_name="Axel",
        agent_prompt=Prompt.AXEL.value,
        agent_model="gemini-1.5-flash",
    )

    response = Axel.invoke(
        query_role="user",
        query=state["question"],
    )
    print(response.text)
    response = parse_json_string(response.text)

    return {
        "next": response["next"],
        "message": response["message"],
        "role": "axel",
    }


def master_agent(state):
    """
    Invokes the Master Agent to generate a response.

    Args:
        state (dict): The state containing the role and message.

    Returns:
        dict: A dictionary containing the next action, message, and optionally action steps.
    """
    print("Master Agent invoked")
    MasterAgent = Agent(
        agent_name="Master Agent",
        agent_prompt=Prompt.MASTER_AGENT.value + Prompt.TOOL_WIKI.value,
        agent_model="gemini-1.5-flash",
        temperature=0.5,
    )

    print(state["message"])
    response = MasterAgent.invoke(query_role=state["role"], query=state["message"])

    print(response.text)
    response = parse_json_string(response.text)
    print(response)

    if response["next"] == "tooling":
        return {
            "next": response["next"],
            "message": response["message"],
            "action_steps": response["action_steps"],
        }

    return {
        "next": response["next"],
        "message": response["message"],
        "role": "master_agent",
    }


def reviewer(state):
    """
    Invokes the Reviewer agent to generate a response.

    Args:
        state (dict): The state containing the role, message, and optionally a PDF.

    Returns:
        dict: A dictionary containing the next action and message.
    """
    print("Reviewer invoked")
    Reviewer = Agent(
        agent_name="Reviewer",
        agent_prompt=Prompt.REVIEWER.value,
        agent_model="gemini-1.5-flash",
    )

    guide = ""
    query = state["question"]
    if state["pdf"] != None:
        pdf_text = extract_pdf_text(state["pdf"])
        query += (
            "DOCUMENT HAS BEEN UPLOADED. PLEASE REVIEW THE DOCUMENT AND ANSWER THE QUESTIONS IF ALL GUIDELINES ARE FOLLOWED"
            + pdf_text
        )
        guide = "Focus only on the content and the areas of improvement as specified and do not try and revise the document but only ask user to revise the document, You can make as descriptive as possible, but do not try to revise the document. "

    response = Reviewer.invoke(
        query_role=state["role"], query=query + state["generation"]
    )
    print(response)
    response = parse_json_string(response.text)
    if response["message"]:
        response_message = response["message"]
    elif response["response_generator"]:
        response_message = response["response_generator"]
    return {
        "next": response["next"],
        "message": guide + response_message,
        "pdf": state["pdf"],
        "role": "reviewer",
    }


def tooling(state):
    """
    Placeholder function for the Tooling agent.

    Args:
        state (dict): The state containing the role and message.
    """
    print("Tooling invoked")
    # Tooling = Agent(
    #     agent_name="Tooling",
    #     agent_prompt=Prompt.TOOLING.value,
    #     agent_model="gemini-flash-8b",
    # )

    # response = Tooling.invoke(query_role=state["role"], query=state["action_steps"])

    # print(response.text)
    # response = parse_json_string(response.text)

    tool_node_list = []
    for tool_node in state["action_steps"]:
        tool_node_list.append(tool_node["tool_node"])
    print(tool_node_list)
    print("LET'S EXECUTE THE TOOLING NODES")
    return {
        "next": tool_node_list,
        "tooling_parameters": state["action_steps"],
    }


def metadata_index(state):
    query = state["message"]
    # Neo4j Configuration
    uri = "neo4j+s://e9d220be.databases.neo4j.io"
    username = "neo4j"
    password = "0vBNNbEI7HYXfZetC-xn94IBSu8zHXyadBTTK4NGwpM"
    driver = GraphDatabase.driver(uri, auth=(username, password))

    # Jina Configuration
    JINA_API_KEY = (
        "Bearer jina_03128ec8d6a64e1f8fbe67593d63fdf2RTLsmT5RN-Yl8kPePnT7b8sdpa9h"
    )
    JINA_URL = "https://api.jina.ai/v1/embeddings"

    # Fetch Jina Embeddings
    def get_jina_embeddings(texts):
        print(f"Fetching embeddings for {len(texts)} texts")
        headers = {"Content-Type": "application/json", "Authorization": JINA_API_KEY}
        data = {
            "model": "jina-clip-v1",
            "normalized": True,
            "embedding_type": "float",
            "input": [{"text": text} for text in texts],
        }
        response = requests.post(JINA_URL, headers=headers, json=data)
        if response.status_code == 200:
            response_json = response.json()
            embeddings = [item["embedding"] for item in response_json["data"]]
            print(f"Received {len(embeddings)} embeddings")
            return embeddings
        else:
            print(f"Error fetching embeddings: {response.status_code}, {response.text}")
            raise Exception(
                f"Error fetching embeddings: {response.status_code}, {response.text}"
            )

    # Perform Similarity Search in Neo4j
    def perform_similarity_search(query_embedding, similarity_threshold=0.2):
        # print(f"Performing similarity search for embedding: {query_embedding}")

        with driver.session() as session:
            print("Running Neo4j query to fetch metadata...")
            result = session.run(
                """
                MATCH (meta_data:meta_data)
                RETURN meta_data.author AS author, meta_data.title AS title, 
                    meta_data.embedding AS embedding, meta_data.source AS source,
                    meta_data.date AS date, meta_data.keywords AS keywords,meta_data.page_id AS page_id, meta_data.cloud_id AS cloud_id
            """
            )

            nodes = []
            embeddings = []
            for record in result:
                record_dict = {
                    "title": record["title"],
                    "embedding": record["embedding"],
                    "source": record["source"],
                    "date": (
                        record["date"] if record["date"] is not None else ""
                    ),  # Default empty string if None
                    "page_id": (
                        record["page_id"] if record["page_id"] is not None else ""
                    ),
                    "cloud_id": (
                        record["cloud_id"] if record["cloud_id"] is not None else ""
                    ),
                }
                nodes.append(record_dict)
                embeddings.append(record_dict["embedding"])

            print(f"Fetched {len(nodes)} nodes from Neo4j.")

            if not nodes:
                print("No nodes found in the database.")
                return []

            # Perform cosine similarity calculation
            embeddings = np.array(embeddings)
            query_embedding = np.array(query_embedding).reshape(1, -1)
            distances = cosine_similarity(query_embedding, embeddings).flatten()

            print(f"Cosine similarity scores: {distances}")

            # Filter nodes based on similarity threshold
            relevant_nodes = []
            for i, node in enumerate(nodes):
                similarity_score = distances[i]
                if similarity_score >= similarity_threshold:
                    node["similarity"] = similarity_score
                    relevant_nodes.append(node)

            # Sort relevant nodes by similarity score and date
            sorted_nodes = sorted(
                relevant_nodes, key=lambda x: (x["similarity"], x["date"]), reverse=True
            )

            print(f"Relevant nodes count: {len(sorted_nodes)}")

            if not sorted_nodes:
                print("No relevant nodes found.")
                return []  # Return empty list if no nodes meet the threshold

            # print(f"Top sorted nodes: {sorted_nodes[:3]}")  # Print top 3 for debugging
            return sorted_nodes

    # Main Workflow
    def process_workflow(user_query):
        print(f"Processing query: {user_query}")
        query_embedding = get_jina_embeddings([user_query])[0]
        top_nodes = perform_similarity_search(query_embedding)
        if not top_nodes:
            print("No relevant documents found.")
            return
        selected_node = top_nodes[0]
        return selected_node

    top_chunk = process_workflow(query)
    if top_chunk:
        del top_chunk["embedding"]
        update_metadata_index_message = "Following are the most relevant documents, use the tools to retrieve the document"
    # print(top_chunk)
    else:
        return {"next": "response_generator", "message": "No relevant documents found."}
    return {"message": update_metadata_index_message + f"{top_chunk}"}


def update_metadata_index(state):
    """
    Placeholder function for updating metadata indexing.
    Args:
        state (dict): The state containing the role and message.
    """

    print("Updating metadata index...")


def update_knowledge_graph(state):
    """
    Placeholder function for updating the knowledge graph.

    Args:
        state (dict): The state containing the role and message.
    """

    print("Updating knowledge graph...")