from email.mime.text import MIMEText
import smtplib
from langchain.text_splitter import TokenTextSplitter
from langchain.schema import Document
from sklearn.metrics.pairwise import cosine_similarity
import google.generativeai as genai
import pdfplumber
from io import BytesIO
import dotenv, os

from models.route_query import obtain_question_router
from models.model_generation import obtain_rag_chain
from models.route_summ_query import obtain_summ_usernode_router

import whisper
from moviepy.editor import VideoFileClip

model_audio = whisper.load_model("small")

from utils.utils import (
    get_jina_embeddings,
    get_relevant_context,
    store_embeddings_in_neo4j,
    generate_ticket_id,
)

dotenv.load_dotenv()

genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

# Initialize the generative model
model = genai.GenerativeModel("gemini-pro")
model_audio = whisper.load_model("base")


def route(state):
    """
    Route question to to retrieve information from the user or common node in neo4j.

    Args:
        state (dict): The current graph state

    Returns:
        str: Next node to call
    """

    print("---ROUTE QUESTION---")
    question = state["question"]

    if state["pdf"] != None:
        return "update_knowledge_graph"
    elif state["video"] != None:
        return "video_processing"

    question_router = obtain_question_router()

    source = question_router.invoke({"question": question})
    if source.datasource == "user_node":
        print("---ROUTE QUERY TO USER NODE IN NEO4J---")
        return "user_node"
    elif source.datasource == "common_node":
        print("---ROUTE QUERY TO COMMON NODE IN NEO4J---")
        return "common_node"
    elif source.datasource == "tech_support":
        print("---ROUTE QUERY TO TECH SUPPORT---")
        return "tech_support"
    elif source.datasource == "bad_language":
        print("---ROUTE QUERY TO BAD LANGUAGE NODE---")
        return "bad_language"


def bad_language(state):
    """
    Route question to bad language node.

    Args:
        state (dict): The current graph state

    Returns:
        str: Next node to call
    """
    print("---BAD LANGUAGE NODE---")
    return {
        "generation": "The question contains offensive language. Please rephrase your query."
    }


def route_summarization_usernode(state):
    """
    Route summarization user node based on the given state.
    Args:
        state (dict): The state containing the question.
    Returns:
        dict: A dictionary indicating the next node and any additional data.
    """
    print("---ROUTE SUMMARIZATION USER NODE---")
    question = state["question"]
    summ_usernode_router = obtain_summ_usernode_router()
    source = summ_usernode_router.invoke({"question": question})

    if source.routeoutput == "neo4j_user_node":
        print("---ROUTE QUERY TO USER NODE IN NEO4J---")
        return {"next": "neo4j_user_node", "question": question}
    elif source.routeoutput == "generate":
        print("---ROUTE QUERY TO GENERATE---")
        print(source.routeoutput)
        return {"next": "summarize", "question": question}


def route_after_breakpoint(state):
    decision = state["decision"]
    breakpoint = state["breakpoint"]

    if decision == "proceed":
        if breakpoint == "1":
            return "breakpoint_2"
        elif breakpoint == "2":
            return "breakpoint_3"
        elif breakpoint == "3":
            return "final_node"
    elif decision == "retry":
        return f"breakpoint_{breakpoint}"
    else:
        return "END"


def neo4j_user_node(state):
    """
    Retrieves relevant documents from Neo4j database based on the user's query.
    Args:
        state (dict): The state containing the user's question and user ID.
    Returns:
        dict: A dictionary containing the retrieved documents and the original question.
    """

    query = state["question"]
    user_id = state["user_id"]
    query_embedding = get_jina_embeddings([query])[0]

    documents = get_relevant_context(query_embedding, "user", user_id)

    print(documents)

    return {"documents": documents, "question": query}


def neo4j_common_node(state):
    """
    Executes a Neo4j query to retrieve relevant documents based on the given state.
    Args:
        state (dict): The state containing the question and user ID.
    Returns:
        dict: A dictionary containing the retrieved documents and the original question.
    """

    query = state["question"]
    # user_id = state["user_id"]
    query_embedding = get_jina_embeddings([query])[0]

    documents = get_relevant_context(query_embedding, "common")

    return {"documents": documents, "question": query}


def generate(state):
    """
    Generate answer from retrieved documentation.

    Args:
        state (dict): The current graph state

    Returns:
        state (dict): New key added to state, generation, that contains LLM generation
    """
    print("---GENERATE---")
    question = state["question"]
    documents = state["documents"]

    # rag_chain = obtain_rag_chain()
    # # RAG generation
    # generation = rag_chain.invoke({"context": documents, "question": question})

    prompt = f"""
    You are a helpful assistant with access to specific documents. Please follow these guidelines:
    
    0. **Output**: Should be descriptive with respect to the question in three (3) lines.

    1. **Contextual Relevance**: Only provide answers based on the provided context. If the query does not relate to the context or if there is no relevant information, respond with "The query is not relevant to the provided context."

    2. **Language and Behavior**: Ensure that your response is polite and respectful. Avoid using any inappropriate language or making offensive statements.

    3. **Content Limitations**: Do not use or refer to any external data beyond the context provided.

    **Context**: {state['documents']}

    **Question**: {state['question']}

    **Answer**:

    Return your answer in markdown format (bold,italics,underline) as required
    """
    response = model.generate_content(prompt)

    return {
        "documents": documents,
        "question": question,
        "generation": response.parts[0].text,
    }


def summarize(state):
    """
    Summarize the retrieved documents.

    Args:
        state (dict): The current graph state

    Returns:
        state (dict): Updated state with summarization key
    """
    print("---SUMMARIZE---")
    documents = []
    file_path = f"_files/{state['pdf'].filename}"
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            raw_text = page.extract_text()
            if raw_text:
                document = Document(page_content=raw_text)
                documents.append(document)

    return {"question": state["question"], "documents": documents}


def update_knowledge_graph(state):

    # pdf_file = BytesIO(state["pdf"])
    print("---UPDATE KNOWLEDGE GRAPH---")
    # Process the PDF
    documents = []
    file_path = f"_files/{state['pdf'].filename}"
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            raw_text = page.extract_text()
            if raw_text:
                document = Document(page_content=raw_text)
                documents.append(document)

    # Split document
    text_splitter = TokenTextSplitter(chunk_size=512, chunk_overlap=80)
    documents = text_splitter.split_documents(documents)

    # documents = text_splitter.split_text(state["pdf"])

    # Get embeddings
    texts = [doc.page_content for doc in documents]
    embeddings = get_jina_embeddings(texts)

    # Store embeddings in Neo4j
    store_embeddings_in_neo4j(documents, embeddings, state["user_id"])

    return {"user_id": state["user_id"], "question": state["question"]}


def video_processing(state):
    """
    Process the video and extract text.

    Args:
        state (dict): The current graph state

    Returns:
        state (dict): Updated state with video key
    """
    print("---VIDEO PROCESSING---")
    video = state["video"]
    video_path = f"chatbot/_videos/{video.filename}"
    output_audio_path = f"chatbot/_audio/{video.filename}.mp3"

    # Load the video file
    video_clip = VideoFileClip(video_path)

    # Extract the audio from the video
    audio_clip = video_clip.audio

    # Save the extracted audio to a file
    audio_clip.write_audiofile(output_audio_path)

    # Close the clips
    audio_clip.close()
    video_clip.close()

    transcribed_text = model_audio.transcribe("output_audio.mp3")

    return {"question": state["question"], "documents": transcribed_text}

def tech_support(state):
    troubleshooting_prompt = (
        f"Please provide at least three detailed troubleshooting steps for addressing  issues related to '{state['question']}'. "
        f"Format your response with clear instructions, starting with 'Please try the following troubleshooting steps:'"
    )

    output = model.generate_content(troubleshooting_prompt)
    response = output.parts[0].text
    

    return {"generation": response}


def send_email(state):
    sender_email = "cletocite@gmail.com"
    receiver_email = "cletocite.techs@gmail.com"
    sender_password = "dxkbhzyaqaqcgrrq"  # App password or your email password

    ticket_id = generate_ticket_id()

    subject = f"TECH SUPPORT - TROUBLESHOOT - {ticket_id}"
    body = (
        f"Dear Tech Support Team,\n\n"
        f"Please find the details of the tech support request below:\n\n"
        f"User ID: {state['user_id']}\n"
        f"Ticket ID: {ticket_id}\n"
        # f"Priority: {priority}\n\n"
        # f"Support Type: {support_type}\n"
        # f"Issue Description: {issue_description}\n\n"
        f"Troubleshooting Steps Taken:\n{state['generation']}\n\n"
        f"Please review the provided information and take the necessary actions.\n\n"
        f"Thank you,\n"
        f"Tech Support Bot"
    )

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = receiver_email

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, receiver_email, msg.as_string())
        print("Email sent successfully.")
    except Exception as e:
        print(f"Failed to send email. Error: {e}")

    return {"generation": state['generation'] + "\n\n ## Sending mail to escalate issue"}
