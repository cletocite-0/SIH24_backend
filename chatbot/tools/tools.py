from email.mime.text import MIMEText
import os
from pathlib import Path
from datetime import datetime, timedelta
import smtplib
import google.generativeai as genai
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import io
from PyPDF2 import PdfReader
import requests
from bs4 import BeautifulSoup
import json
import pytz
import re
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


def fetch_from_confluence(params):
    ATLASSIAN_API_URL = "https://api.atlassian.com"

    ACCESS_TOKEN = "eyJraWQiOiJhdXRoLmF0bGFzc2lhbi5jb20tQUNDRVNTLTk0ZTczYTkwLTUxYWQtNGFjMS1hOWFjLWU4NGUwNDVjNDU3ZCIsImFsZyI6IlJTMjU2In0.eyJqdGkiOiIxOGQxZTkzZS02YTI3LTQxZTItYmVhNS1mYTg3ZDNlYmRlZmMiLCJzdWIiOiI3MTIwMjA6NDE1ZmVlNGYtNjdiMy00YmQ0LTlmZTQtZTNhNTY2ZDllYWRlIiwibmJmIjoxNzMzOTIwMDEzLCJpc3MiOiJodHRwczovL2F1dGguYXRsYXNzaWFuLmNvbSIsImlhdCI6MTczMzkyMDAxMywiZXhwIjoxNzMzOTIzNjEzLCJhdWQiOiJIQjZGT2dFVzI2Y1JWQ2dZeTR1ZDlZMllZMjlQNHV2YyIsImh0dHBzOi8vYXRsYXNzaWFuLmNvbS9vYXV0aENsaWVudElkIjoiSEI2Rk9nRVcyNmNSVkNnWXk0dWQ5WTJZWTI5UDR1dmMiLCJodHRwczovL2lkLmF0bGFzc2lhbi5jb20vc2Vzc2lvbl9pZCI6IjUxZTExZWVkLWI3MzktNGM4ZC05Y2I1LWNlNzZiYWFhYTQxYyIsImh0dHBzOi8vaWQuYXRsYXNzaWFuLmNvbS9hdGxfdG9rZW5fdHlwZSI6IkFDQ0VTUyIsImh0dHBzOi8vYXRsYXNzaWFuLmNvbS9maXJzdFBhcnR5IjpmYWxzZSwiaHR0cHM6Ly9hdGxhc3NpYW4uY29tL3N5c3RlbUFjY291bnRJZCI6IjcxMjAyMDphZTliMTJjNy01M2ZiLTQwM2EtYjI0ZS0wYWVhNDYwZTZmY2EiLCJodHRwczovL2lkLmF0bGFzc2lhbi5jb20vdWp0IjoiYjQ5ODM1MDYtMDVjNi00OTA2LWFhNjktNzI0M2M4ZmRjYmEyIiwiaHR0cHM6Ly9hdGxhc3NpYW4uY29tL3ZlcmlmaWVkIjp0cnVlLCJodHRwczovL2lkLmF0bGFzc2lhbi5jb20vcHJvY2Vzc1JlZ2lvbiI6InVzLWVhc3QtMSIsImh0dHBzOi8vYXRsYXNzaWFuLmNvbS9lbWFpbERvbWFpbiI6ImdtYWlsLmNvbSIsImNsaWVudF9pZCI6IkhCNkZPZ0VXMjZjUlZDZ1l5NHVkOVkyWVkyOVA0dXZjIiwiaHR0cHM6Ly9hdGxhc3NpYW4uY29tLzNsbyI6dHJ1ZSwiaHR0cHM6Ly9pZC5hdGxhc3NpYW4uY29tL3ZlcmlmaWVkIjp0cnVlLCJzY29wZSI6InJlYWQ6Y29uZmx1ZW5jZS1jb250ZW50LmFsbCByZWFkOmNvbmZsdWVuY2UtY29udGVudC5zdW1tYXJ5IHNlYXJjaDpjb25mbHVlbmNlIiwiaHR0cHM6Ly9hdGxhc3NpYW4uY29tL3N5c3RlbUFjY291bnRFbWFpbERvbWFpbiI6ImNvbm5lY3QuYXRsYXNzaWFuLmNvbSIsImh0dHBzOi8vYXRsYXNzaWFuLmNvbS9zeXN0ZW1BY2NvdW50RW1haWwiOiIyNWNmNWEyYS01MjJiLTQ2NjAtYjM1ZS0xY2NhY2MyNWZjOWRAY29ubmVjdC5hdGxhc3NpYW4uY29tIn0.cPgPOBRUlz6KM4YMXJDSRUVn3WLzioahcyMweDzJZ27OWtChPQxUMAoJOAKXgyfDpyDLyG3cEiiMIzTEEwKCQ2ZxqAldVvyHFbLVLSczr16aK3o5N31hHrZdx5pkE0C8UFliRYn4dt19r2YwIxB6d-X48cixkkSIzmOHHceUsatq_gRLI6JPPjQEYOo1NmKTr1RwrmhY3nfk5xHRpS4NXI3Xcnp7Kz4_a5zoY91bOW008b7J6CV6K3oXWmerrWNLqeHfl3HCBKDX7kwv7sBgNjOksJeSDinXbGnL3Anj6Fk7v8iZKTXdl08GqPV5UW1zIS2s1BUYFMku4s1CFa7sbA"  # Replace with your OAuth access token

    page_id = params["page_id"]
    cloudid = params["cloudid"]

    """Fetch the page content using cloudid and parse it with BeautifulSoup."""
    url = f"{ATLASSIAN_API_URL}/ex/confluence/{cloudid}/rest/api/content/{page_id}?expand=body.storage"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Accept": "application/json"}

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

            # Extract text content from the HTML
            text_content = soup.get_text(separator="\n").strip()
            return {"generation": text_content}
    except Exception as e:
        print(f"Error: {e}")
        return {"generation": f"Failed to fetch content from Confluence. Error {e}"}


def fetch_from_gdrive(params):
    SCOPES = ["https://www.googleapis.com/auth/drive"]

    def authenticate_google_drive():
        creds = None
        pickel_file = "D:\\Studies\\Projects\\Hackathon\\SIH24\\SIH24_backend\\chatbot\\tools\\token.pickle"

        if os.path.exists(pickel_file):
            with open(pickel_file, "rb") as token:
                creds = pickle.load(token)
                print("Loaded existing credentials from token.pickle")
        if not creds or not creds.valid:
            print("No valid credentials or expired credentials. Re-authenticating...")
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    "D:\\Studies\\Projects\\Hackathon\\SIH24\\SIH24_backend\\chatbot\\tools\\gdrive_search_cred.json",
                    SCOPES,
                )
                creds = flow.run_local_server(port=0)
            with open(pickel_file, "wb") as token:
                pickle.dump(creds, token)
                print("New credentials saved to token.pickle")
        return build("drive", "v3", credentials=creds)

    def fetch_file_by_name(file_name, folder_id):
        print(f"Fetching file: {file_name} from folder ID: {folder_id}")
        service = authenticate_google_drive()
        results = (
            service.files()
            .list(
                q=f"name='{file_name}' and '{folder_id}' in parents",
                spaces="drive",
                fields="files(id, name)",
                pageSize=1,
            )
            .execute()
        )
        files = results.get("files", [])
        if not files:
            print(f"Error: No file found with the name: {file_name}")
            raise FileNotFoundError(f"No file found with the name: {file_name}")
        file_id = files[0]["id"]
        print(f"File ID found: {file_id}")
        request = service.files().get_media(fileId=file_id)
        file_path = f"{file_name}.pdf"
        with open(file_path, "wb") as f:
            downloader = io.BytesIO()
            downloader.write(request.execute())
            f.write(downloader.getbuffer())
        print(f"File saved to: {file_path}")
        return file_path

    def pdf_to_text(file_path):
        print(f"Converting PDF to text: {file_path}")
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        print(f"Extracted text length: {len(text)} characters")
        return text

    folder_id = "1z-vpBPF-6i8Khq2WA2OoCZWod0Ot0k2S"
    for tools in params["action_steps"]:
        if tools["tool_node"] == "fetch_from_gdrive":
            tool_param = tools["parameters"]
    file_path = fetch_file_by_name(tool_param["file_id"], folder_id)
    text = pdf_to_text(file_path)

    return {"next": "reviewer", "generation": text}


def gmeet(details):
    SCOPES = ["https://www.googleapis.com/auth/calendar"]
    TOKEN_FILE = "D:\\Studies\\Projects\\Hackathon\\SIH24\\SIH24_backend\\chatbot\\tools\\token_meeting.pickle"
    CREDENTIALS_FILE = "D:\\Studies\\Projects\\Hackathon\\SIH24\\SIH24_backend\\chatbot\\tools\\meeting_cred.json"

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

    # print("Details: ", details)
    for step in details["action_steps"]:
        if step["tool_node"] == "gmeet":
            meeting_date = step["parameters"]["date"]
            meeting_time = step["parameters"]["time"]
            attendees_list = step["parameters"]["attendees"]
            subject = step["parameters"]["subject"]
            duration = step["parameters"]["duration"]
            print("Meeting Date:", meeting_date)
            print("Meeting Time:", meeting_time)
            print("Attendees:", attendees_list)
            print("Subject:", subject)
            print("Duration (hours):", duration)
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


def send_email(params):
    # params = {
    #     "user_id": "12345",
    #     "ticket_id": "T12345",
    #     "support_type": "Hardware",
    #     "issue_description": "My laptop is not turning on.",
    #     "troubleshooting_steps": "1. Check the power adapter.\n2. Press the power button.",
    #     "user_name": "Alice",
    #     "priority": "High",
    # }
    # ticket_id = params["ticket_id"]
    # support_type = params["support_type"]
    # issue_description = params["issue_description"]
    # troubleshooting_steps = params["troubleshooting_steps"]
    # user_name = params["user_name"]
    # priority = params["priority"]
    for step in params["action_steps"]:
        if step["tool_node"] == "send_email":
            subject = step["parameters"]["subject"]
            body = step["parameters"]["body"]
            receiver_email = step["parameters"]["receiver"]
            print("Subject:", subject)
            print("Body:", body)
    sender_email = "cletocite@gmail.com"
    sender_password = "glsrwxltluaycrrs"  # App password or your email password

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
        return {"generation": "Email sent successfully."}
    except Exception as e:
        print(f"Failed to send email. Error: {e}")
        return {"generation": f"Failed to send email. Error: {e}"}


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
        def _init_(self, uri, user, password):
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