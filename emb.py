import requests
from langchain.text_splitter import TokenTextSplitter
from langchain.schema import Document
from neo4j import GraphDatabase
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import google.generativeai as genai

# Initialize Neo4j Aura connection
uri = "neo4j+s://332e43eb.databases.neo4j.io"  # Your Neo4j Aura URI
username = "neo4j"
password = "ZyvWu0bndBWMNu6lYlb5Fa3PkfsrWXes-gg0DPrAZLc"
driver = GraphDatabase.driver(uri, auth=(username, password))

# Initialize Gemini
GOOGLE_API_KEY = "AIzaSyDRIIeaCaEu45HX2ykLe64EQcA9gH4RIzI"
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-pro')

# Function to get embeddings from Jina AI API
def get_jina_embeddings(texts):
    url = 'https://api.jina.ai/v1/embeddings'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer jina_6f5c954572b64f59b9981f7e3c0bf550lTiWT5sW_gyTkoFQEaHQTRwZhmlW'
    }
    data = {
        'model': 'jina-clip-v1',
        'normalized': True,
        'embedding_type': 'float',
        'input': [{'text': text} for text in texts]
    }

    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code == 200:
        response_json = response.json()
        embeddings = [item['embedding'] for item in response_json['data']]
        return embeddings
    else:
        raise Exception(f"Error fetching embeddings: {response.status_code}, {response.text}")

# Function to create Neo4j nodes for each document and store embeddings
def store_embeddings_in_neo4j(documents, embeddings):
    with driver.session() as session:
        for i, (doc, embedding) in enumerate(zip(documents, embeddings)):
            session.run("""
                CREATE (d:Document {id: $id, content: $content, embedding: $embedding})
                """, id=i, content=doc.page_content, embedding=embedding)

# Function to perform similarity search using cosine similarity
def perform_similarity_search(query_embedding, top_k=10):
    with driver.session() as session:
        result = session.run("""
            MATCH (d:Document)
            RETURN d.id AS id, d.content AS content, d.embedding AS embedding
        """)
        documents = []
        embeddings = []

        for record in result:
            documents.append((record['id'], record['content']))
            embeddings.append(record['embedding'])

        embeddings = np.array(embeddings)
        query_embedding = np.array(query_embedding).reshape(1, -1)
        distances = cosine_similarity(query_embedding, embeddings).flatten()

        # Get top_k results
        top_k_indices = np.argsort(distances)[-top_k:]
        top_docs = [(documents[i][0], documents[i][1], distances[i]) for i in top_k_indices]

    return sorted(top_docs, key=lambda x: x[2], reverse=True)

# Function to get relevant context from the similarity search
def get_relevant_context(query_embedding):
    results = perform_similarity_search(query_embedding)
    context = ""
    for id, content, _ in results:
        context += content + "\n"
    return context

# Function to generate answer using Gemini
def generate_answer(prompt):
    response = model.generate_content(prompt)
    return response.text

# Function to process and store documents
def process_and_store_documents(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        raw_text = file.read()

    document = Document(page_content=raw_text)
    text_splitter = TokenTextSplitter(chunk_size=512, chunk_overlap=80)
    documents = text_splitter.split_documents([document])

    # Get the text content from documents to pass to Jina AI
    texts = [doc.page_content for doc in documents]

    # Fetch embeddings using Jina AI
    embeddings = get_jina_embeddings(texts)
    print("Embeddings fetched.")

    # Store the document embeddings in Neo4j
    store_embeddings_in_neo4j(documents, embeddings)
    print("Embeddings stored in Neo4j.")

# Main workflow
def main():
    # process_and_store_documents('letters.txt')

    # Get query embedding using Jina AI
    query_text = input("Enter Query: ")
    query_embedding = get_jina_embeddings([query_text])[0]  # Take the first embedding from the response

    # Get relevant context from Neo4j
    context = get_relevant_context(query_embedding)

    # Generate the response using Gemini
    prompt = f"""
    You are a helpful assistant with access to specific documents. Please follow these guidelines:
    
    0. **Output**: Should be descriptive with respect to the question in three (3) lines.

    1. **Contextual Relevance**: Only provide answers based on the provided context. If the query does not relate to the context or if there is no relevant information, respond with "The query is not relevant to the provided context."

    2. **Language and Behavior**: Ensure that your response is polite and respectful. Avoid using any inappropriate language or making offensive statements.

    3. **Content Limitations**: Do not use or refer to any external data beyond the context provided.

    **Context**: {context}

    **Question**: {query_text}

    **Answer**:
    """
    answer = generate_answer(prompt)

    print("Generated Answer:")
    print(answer)

if __name__ == "__main__":
    main()