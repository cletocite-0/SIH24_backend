import os
from pathlib import Path
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

from langchain_groq import ChatGroq
from neo4j import GraphDatabase

from utils.utils import (
    create_graph,
    extract_pdf_text,
    send_to_gemini,
    upload_to_firebase,
)


def fetch_from_confluence():
    return "confluence"


def fetch_from_gdrive():
    return "gdrive"


def gmeet(details):
    SCOPES = ["https://www.googleapis.com/auth/calendar"]
    TOKEN_FILE = "token_meeting.pickle"
    CREDENTIALS_FILE = "cred.json"

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

    def convert_date_and_time(date_str, time_str, duration):
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
        end_time = start_time + timedelta(hours=duration)

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
        return f'Event created: {event.get("htmlLink")}'

    meeting_date = details["parameters"]["date"]
    meeting_time = details["parameters"]["time"]
    attendees_list = details["parameters"]["attendees"]
    subject = details["parameters"]["subject"]
    duration = int(details["parameters"]["duration"])
    if not meeting_date or not meeting_time:
        print("Date or time information missing.")
        return
    start_time, end_time = convert_date_and_time(meeting_date, meeting_time, duration)

    if start_time and end_time:
        # Authenticate
        service = authenticate_google_calendar()

        # Retry loop for scheduling the meeting
        max_retries = 5
        retry_delay = 5  # seconds
        for attempt in range(max_retries):
            try:
                return {
                    "message": schedule_meeting(
                        service, start_time, end_time, attendees_list, subject
                    )
                }
            except Exception as e:
                print(f"Error creating event: {e}")
                if attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    return "Failed to create event after multiple attempts." + e
    else:
        print("Failed to convert date and time.")


def send_mail():
    return "mail"


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


async def fetch_reporting_chain(state):
    NEO4J_URI = os.getenv("NEO4J_URI_HIERARCHY")
    NEO4J_USERNAME = os.getenv("NEO4J_USERNAME_HIERARCHY")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD_HIERARCHY")

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
        )
        print("\n\n")
        response = model.invoke(prompt)
        return {"generation": response}

    finally:
        client.close()
