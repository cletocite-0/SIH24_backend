import asyncio
from email.mime.text import MIMEText
import smtplib
from langchain.text_splitter import TokenTextSplitter
from langchain.schema import Document
from langchain_groq import ChatGroq
from sklearn.metrics.pairwise import cosine_similarity
import google.generativeai as genai
from neo4j import GraphDatabase
import pdfplumber
from io import BytesIO
import dotenv, os
from datetime import datetime, timedelta
import google.generativeai as genai
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import json
import pytz
import re
import os
import pickle
import time
from pathlib import Path

from models.route_query import obtain_question_router
from models.route_summ_query import obtain_summ_usernode_router
from models.chatbot_or_rag import obtain_chatbot_rag_router

import whisper
from moviepy.editor import VideoFileClip

from utils.utils import (
    get_jina_embeddings,
    get_relevant_context,
    store_embeddings_in_neo4j,
    generate_ticket_id,
    extract_pdf_text,
    send_to_gemini,
    create_graph,
    upload_to_firebase,
)

dotenv.load_dotenv()

model_audio = whisper.load_model("small")

genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

# Initialize the generative model
model = genai.GenerativeModel("gemini-pro")


def chatbot_rag_router(state):
    print("---CHATBOT--- or ---RAG---")
    question = state["question"]

    question_router = obtain_chatbot_rag_router()

    source = question_router.invoke({"question": question})
    if source.datasource == "rag":
        print("---RAG---")
        return {"next": "route", "question": question}
    elif source.datasource == "chatbot":
        print("---CHATBOT---")
        return {"next": "chatbot", "question": question}


async def chatbot(state):
    # response = model.generate_content(state["question"], stream=True)
    model = ChatGroq(
        temperature=0,
        model_name="gemma2-9b-it",
        api_key=os.environ["GROQ_API_KEY"],
        streaming=True,
    )
    prompt = f""" You are an enterprise assistant for GAIL and make sure all your replies are centered around helping the user with their queries and for queries which are greetings reply with something related to the fact that he is a gail employee and ask what he wants help with either tech support, pdf/meeing video summarization or email drafting, email sending or any other query related to GAIL and their policies/rulebooks.
    Format your message in a polite and respectful manner and make sure to provide the user with the necessary information and use emotes to make the conversation more engaging and make it as comprehensive and descriptive as possible.
    {state['question']}
                """
    print("\n\n")
    response = await model.ainvoke(prompt)
    return {"generation": response}


def check_uploads(state):
    question = state["question"]
    print("---CHECK FOR UPLOADS---")
    if state["pdf"] != None:
        return "update_knowledge_graph"
    elif state["video"] != None:
        return "video_processing"
    else:
        return "chatbot_rag_router"


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

    # pattern = r"^Schedule meeting @(\d{1,2}:\d{2}\s(?:AM|PM))\s(\d{2}/\d{2}/\d{4})\swith\s((?:[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,},?\s*)+)about\s(.+)$"

    # match = re.match(pattern, state["question"])

    # if match:
    #     time, date, emails, subject = match.groups()
    #     return "schedule_meeting"

    question_router = obtain_question_router()

    source = question_router.invoke({"question": question})
    if source.datasource == "user_node":
        print("---ROUTE QUERY TO USER NODE IN NEO4J---")
        return {"next": "user_node", "question": question}
    elif source.datasource == "common_node":
        print("---ROUTE QUERY TO COMMON NODE IN NEO4J---")
        return {"next": "common_node", "question": question}
    elif source.datasource == "tech_support":
        print("---ROUTE QUERY TO TECH SUPPORT---")
        return {"next": "tech_support", "question": question}
    elif source.datasource == "schedule_meeting":
        print("---ROUTE QUERY TO SCHEDULE MEETING NODE---")
        return {"next": "schedule_meeting", "question": question}
    elif source.datasource == "hierachy":
        print("---ROUTE QUERY TO HIERACHY NODE---")
        return {"next": "hierachy", "question": question}


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
    elif source.routeoutput == "generate_image_graph":
        print("---ROUTE QUERY TO IMAGE GRAPH---")
        return {"next": "generate_image_graph", "question": question}


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


async def generate(state):
    """
    Generate answer from retrieved documentation.

    Args:
        state (dict): The current graph state

    Returns:
        state (dict): New key added to state, generation, that contains LLM generation
    """
    print("---GENERATE---")

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

    Incase of Meeting summarizations I want you to summarize the meeting in a proper format and make it more readable and beautiful and also identify the key points of the meeting.

    Return your answer in Markdown format with bolded headings, italics and underlines etc. as necessary.
    Use as much markdown as possible to format your response.
    Use ## for headings and ``` code blocks for code.
    ```
    """
    model = ChatGroq(
        temperature=0,
        model_name="gemma2-9b-it",
        # api_key=os.environ["GROQ_API_KEY"],
        api_key="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",
        streaming=True,
    )

    response = await model.ainvoke(prompt)
    return {"generation": response}


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
    if state["pdf"]:
        file_path = state["pdf"]
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                raw_text = page.extract_text()
                if raw_text:
                    document = Document(page_content=raw_text)
                    documents.append(document)
    else:
        documents = state["documents"]

    return {"question": state["question"], "documents": documents}


def update_knowledge_graph(state):

    # pdf_file = BytesIO(state["pdf"])
    print("---UPDATE KNOWLEDGE GRAPH---")
    documents = []
    # Process the PDF
    if state["pdf"]:
        file_path = state["pdf"]
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                raw_text = page.extract_text()
                if raw_text:
                    document = Document(page_content=raw_text)
                    documents.append(document)
    else:
        raw_text = state["documents"]["text"]
        if raw_text:
            documents.append(Document(page_content=raw_text))

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
    # video = state["video"]
    # video_path = f"_videos/{video.filename}"
    # audio = state["video"].filename[:-4] + ".mp3"
    # output_audio_path = f"_audio/{audio}"

    video_path = state["video"]
    output_audio_path = "_audio/output_audio.mp3"
    # Load the video file
    video_clip = VideoFileClip(video_path)

    # Extract the audio from the video
    audio_clip = video_clip.audio

    # Save the extracted audio to a file
    audio_clip.write_audiofile(output_audio_path)

    # Close the clips
    audio_clip.close()
    video_clip.close()

    print("STARTING")
    transcribed_text = model_audio.transcribe("_audio/output_audio.mp3")
    print("TRANSCRIBED")

    return {"question": state["question"], "documents": transcribed_text}


async def tech_support(state):
    troubleshooting_prompt = (
        f"Please provide at least three detailed troubleshooting steps for addressing  issues related to '{state['question']}'. "
        f"Format your response with clear instructions, starting with 'Please try the following troubleshooting steps:'"
    )

    model = ChatGroq(
        temperature=0,
        model_name="gemma2-9b-it",
        api_key=os.environ["GROQ_API_KEY"],
        streaming=True,
    )
    print("\n\n")
    response = await model.ainvoke(troubleshooting_prompt)
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

    return {"generation": state["generation"]}


async def meeting_shu(state):
    SCOPES = ["https://www.googleapis.com/auth/calendar"]
    TOKEN_FILE = "token.pickle"
    CREDENTIALS_FILE = "chatbot\nodes\cred.json"

    def generate_answer(prompt):
        try:
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"Error generating answer: {e}")
            return None

    def extract_meeting_details(text):
        prompt = f"""
        Extract the following details from the text:
        - Date of the meeting (in DD/MM/YYYY format or 'today' or 'tomorrow')
        - Time of the meeting (in 12-hour format HH:MM AM/PM)
        - List of attendees (as a list of email addresses)
        - Summary of the meeting

        Provide the extracted details as a JSON object with the following keys:
        - "date": The date of the meeting.
        - "time": The time of the meeting.
        - "attendees": A list of email addresses.
        - "summary": A brief summary of the meeting.

        Text: "{text}"
        """
        answer = generate_answer(prompt)
        print(f'Gemini response: "{answer}"')  # Include quotes for better visibility

        if not answer:
            print("No response from Gemini.")
            return None

        # Clean the response
        cleaned_answer = re.sub(
            r"^```json", "", answer
        )  # Remove start code block delimiter
        cleaned_answer = re.sub(
            r"```$", "", cleaned_answer
        )  # Remove end code block delimiter
        cleaned_answer = cleaned_answer.strip()
        print(f'Cleaned response: "{cleaned_answer}"')  # Debugging line

        try:
            details = json.loads(cleaned_answer)
            if not isinstance(details, dict):
                raise ValueError("Response is not a JSON object")
            print(f"Parsed details: {details}")  # Debugging line
            return details
        except json.JSONDecodeError as e:
            print(f"JSON decoding error: {e}")
            return None
        except ValueError as e:
            print(f"Value error: {e}")
            return None

    def authenticate_google_calendar():
        creds = None
        # Check if token.pickle exists (stored token for re-use)
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, "rb") as token:
                creds = pickle.load(token)

        # If there are no valid credentials available, prompt the user to log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_FILE, SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save the credentials for the next run
            with open(TOKEN_FILE, "wb") as token:
                pickle.dump(creds, token)

        service = build("calendar", "v3", credentials=creds)
        return service

    def convert_date_and_time(date_str, time_str):
        now = datetime.now(pytz.timezone("Asia/Kolkata"))

        if date_str.lower() == "today":
            meeting_date = now.date()
        elif date_str.lower() == "tomorrow":
            meeting_date = now.date() + timedelta(days=1)
        else:
            try:
                meeting_date = datetime.strptime(date_str, "%d/%m/%Y").date()
            except ValueError:
                print(f"Invalid date format: {date_str}")
                return None, None

        try:
            meeting_time = datetime.strptime(time_str, "%I:%M %p").strftime("%H:%M")
        except ValueError:
            print(f"Invalid time format: {time_str}")
            return None, None

        start_time = datetime.combine(
            meeting_date, datetime.strptime(meeting_time, "%H:%M").time()
        )
        end_time = start_time + timedelta(hours=1)

        print(f"Converted start time: {start_time.isoformat()}")
        print(f"Converted end time: {end_time.isoformat()}")

        return start_time.isoformat(), end_time.isoformat()

    def schedule_meeting(service, start_time, end_time, attendees, summary="Meeting"):
        event = {
            "summary": summary,
            "start": {
                "dateTime": start_time,
                "timeZone": "Asia/Kolkata",  # Change this to your timezone
            },
            "end": {
                "dateTime": end_time,
                "timeZone": "Asia/Kolkata",  # Change this to your timezone
            },
            "attendees": [{"email": email} for email in attendees],
            "reminders": {
                "useDefault": True,
            },
        }
        event = service.events().insert(calendarId="primary", body=event).execute()
        print(f'Event created: {event.get("htmlLink")}')

    def main_fun(user_input):
        details = extract_meeting_details(user_input)

        if details:
            print(f"Extracted details: {details}")  # Debugging line

            # Use correct keys from the parsed JSON
            meeting_date = details.get("date") or details.get("meeting_date")
            meeting_time = details.get("time") or details.get("meeting_time")
            attendees = details.get("attendees", [])
            summary = details.get("summary", "Meeting")

            if not meeting_date or not meeting_time:
                print("Date or time information missing.")
                return

            start_time, end_time = convert_date_and_time(meeting_date, meeting_time)

            if start_time and end_time:
                # Authenticate
                service = authenticate_google_calendar()

                # Retry loop for scheduling the meeting
                max_retries = 5
                retry_delay = 5  # seconds
                for attempt in range(max_retries):
                    try:
                        schedule_meeting(
                            service, start_time, end_time, attendees, summary
                        )
                        print("Event created successfully.")
                        break  # Exit loop if successful
                    except Exception as e:
                        print(f"Error creating event: {e}")
                        if attempt < max_retries - 1:
                            print(f"Retrying in {retry_delay} seconds...")
                            time.sleep(retry_delay)
                        else:
                            print("Failed to create event after multiple attempts.")
            else:
                print("Failed to convert date and time.")
        else:
            print("Failed to extract meeting details.")

    main_fun(state["question"])

    prompt = f"""{state['question']}
                Meeting has been scheduled successfully and I only want you to return a summarization of successfull meeting scheduling of above meet.
                Properly format(Markdown) it to make to it more readable and beautiful.
                """

    model_groq = ChatGroq(
        temperature=0,
        model_name="gemma2-9b-it",
        api_key=os.environ["GROQ_API_KEY"],
        streaming=True,
    )
    print("\n\n")
    response = await model_groq.ainvoke(prompt)
    return {"generation": response}

    # return {"generation": "Meeting scheduled successfully."}


async def hierachy(state):
    NEO4J_URI = "neo4j+s://96436377.databases.neo4j.io"
    NEO4J_USERNAME = "neo4j"
    NEO4J_PASSWORD = "rF3N3WPa5NvIgUTfXZh1c-zvbcE2bWBz4k0thBVa-8M"

    # GOOGLE_API_KEY = "AIzaSyC5gv15479xiPka5pH4iYgphdPyrFKDuz4"
    class Neo4jClient:
        def __init__(self, uri, user, password):
            self.driver = GraphDatabase.driver(uri, auth=(user, password))

        def close(self):
            self.driver.close()

        def fetch_graph_data(self):
            query = """
            MATCH (n)
            OPTIONAL MATCH (n)-[r]->(m)
            RETURN n, r, m
            """
            with self.driver.session() as session:
                result = session.run(query)
                data = []
                for record in result:
                    nodes = (record["n"], record["m"])
                    relationships = record["r"]
                    data.append({"nodes": nodes, "relationships": relationships})
                return data

    # def generate_answer_graph(prompt):
    #     response = model.generate_content(prompt)
    #     return response.text

    client = Neo4jClient(NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD)
    try:
        graph_data = client.fetch_graph_data()
        # Convert graph data to a textual representation
        graph_document = str(graph_data)

        # person = input("Enter the person's name: ")
        prompt = f"""
        These are the nodes and relationships of the graph:
        document = {graph_document}

        Provide the hierarchy for the person '{state['question']}'. The hierarchy should trace their position up to the CEO, including all managers and seniors they report to. Format the output as follows:

        His desigination and folowing by Reports to - Name - Desiginamtion and try to indent it with there position.

        Use indentation to reflect the reporting structure. Please ensure the output is clear and organized, with some special formatting (Markdown) to cleanly render it in UI.
        """

        model = ChatGroq(
            temperature=0,
            model_name="gemma2-9b-it",
            api_key=os.environ["GROQ_API_KEY"],
            streaming=True,
        )
        print("\n\n")
        response = await model.ainvoke(prompt)
        return {"generation": response}

    finally:
        client.close()


def generate_image_graph(state):

    pdf_path = state["pdf"]
    user_query = state["question"]

    # Define the save directory and filename
    graph_dir = Path("./graph_img")
    graph_dir.mkdir(parents=True, exist_ok=True)
    file_name = "output_graph.png"
    file_path = graph_dir / file_name

    # Extract text from PDF
    pdf_text = extract_pdf_text(pdf_path)

    # Send to Gemini for graph instructions
    graph_instructions, description = send_to_gemini(
        pdf_text, user_query, graph_dir, file_name
    )
    # print(f"Gemini provided instructions:\n{graph_instructions}")

    # Generate and save the graph
    generated_file_path = create_graph(graph_instructions, file_path)

    if generated_file_path:
        # Upload the graph to Firebase and get the download URL
        public_url = upload_to_firebase(
            generated_file_path, "your-firebase-storage-bucket"
        )
        # print(f"Graph uploaded to Firebase. Accessible at: {public_url}")
        # print(f"Graph Description: {description}")
        print(public_url)
        return {"generation": public_url + description}
