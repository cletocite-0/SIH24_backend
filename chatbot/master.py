# from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi import FastAPI, File, Form, UploadFile, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import io
import uuid
import mysql.connector
from typing import List
import uvicorn
from typing import Optional
from pprint import pprint
from pdfminer.high_level import extract_text
import requests
import json
from bs4 import BeautifulSoup

from utils.utils import add_route, remove_route, get_cloudid, fetch_page_content
from utils.webhooks import *

# from graph.graph import graph
from graph.graph_v2 import graph
from dotenv import load_dotenv
import os
from jose import JWTError
import jwt
from pydantic import BaseModel
from typing import Optional
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends

app = FastAPI()

# Create directories if not exist
os.makedirs("files", exist_ok=True)
os.makedirs("videos", exist_ok=True)

# CORS configuration
origins = ["http://localhost:5173"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MySQL configuration
# db_config = {
#     "user": "root",
#     "password": "CowTheGreat",
#     "host": "localhost",
#     "database": "sihfinale",
# }

# db_config = {
#     "user": "unfnny1o9zn09z9a",
#     "password": "Yzfw1C8GG1k0H4w0aiEb",
#     "host": "b1urg5hqy4fizvsrfabz-mysql.services.clever-cloud.com",
#     "database": "b1urg5hqy4fizvsrfabz",
# }

# Load environment variables from the .env file
load_dotenv()

db_config = {
    "user": os.getenv("MYSQL_ADDON_USER"),
    "password": os.getenv("MYSQL_ADDON_PASSWORD"),
    "host": os.getenv("MYSQL_ADDON_HOST"),
    "database": os.getenv("MYSQL_ADDON_DB"),
}

# Mock secret key for JWT encoding/decoding
SECRET_KEY = "secretkey123"
ALGORITHM = "HS256"


# Pydantic model for login request
class LoginRequest(BaseModel):
    email: str
    password: str


# Dependency to get the user based on token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


# Create a database connection
def get_db_connection():
    return mysql.connector.connect(**db_config)


# Pydantic model for login request
class LoginRequest(BaseModel):
    email: str
    password: str


class UpdateSessionTitleRequest(BaseModel):
    session_id: str
    new_title: str


# Database query function to get the user by email
def get_user_by_email(email: str):
    try:
        # Establish a connection to the database
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)

        # Query the database for the user by email
        query = "SELECT * FROM users WHERE email = %s"
        cursor.execute(query, (email,))
        user = cursor.fetchone()

        cursor.close()
        connection.close()

        return user
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return None


# Function to generate JWT token
def create_access_token(data: dict):
    token = jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)
    print(f"Generated JWT: {token}")
    return token


# Dependency to get current user based on the token
def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = get_user_by_email(email)
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")


# Login endpoint
@app.post("/login")
async def login(request: LoginRequest):
    user = get_user_by_email(request.email)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid email or password")

    # Check if the password matches the one in the database
    if request.password != user["password"]:
        raise HTTPException(status_code=400, detail="Invalid email or password")

    # Generate a JWT token
    token = create_access_token({"sub": user["email"]})
    print(f"Token sent to client: {token}")  # Log the token before returning
    return {"access_token": token, "token_type": "bearer"}


# Route to generate a new session ID
@app.get("/session")
async def generate_session():
    session_id = str(uuid.uuid4())
    return {"session_id": session_id}


# Route to handle incoming messages and bot response
class QueryRequest(BaseModel):
    session_id: str
    session_title: str = "Default Title"
    user_id: str
    question: str
    pdf: Optional[UploadFile] = None
    video: Optional[UploadFile] = None


@app.post("/query")
async def receive_message(
    user: dict = Depends(get_current_user),  # Ensure the user is authenticated
    user_id: str = Form(...),
    question: str = Form(...),
    pdf: Optional[UploadFile] = File(None),
    video: Optional[UploadFile] = File(None),
):
    graph_app = graph()
    print("Query received")
    connection = get_db_connection()

    # Create session title based on the question
    booltitle = 1
    if booltitle:
        booltitle = 0
        session_tit = question[0:15]

    if not connection:
        raise HTTPException(status_code=500, detail="Failed to connect to the database")

    try:
        cursor = connection.cursor()

        # Insert the user's message into the database
        user_message_query = "INSERT INTO messages (session_id, session_title, sender, text, name) VALUES (%s, %s, %s, %s, %s)"
        cursor.execute(
            user_message_query, ("1", session_tit, "user", question, "cow")
        )  # Use authenticated user's name
        connection.commit()
        print("DB UPDATED")

        file_path = None
        video_path = None
        # Access the uploaded files
        if pdf:
            file_path = os.path.join("_files", pdf.filename)
            with open(file_path, "wb") as f:
                content = await pdf.read()  # Read the file content asynchronously
                f.write(content)

            print(f"PDF content received and saved to {file_path}.")

        if video:
            video_path = os.path.join("_videos", video.filename)
            with open(video_path, "wb") as f:
                content = await video.read()  # Read the video content asynchronously
                f.write(content)

            print(f"Video content received and saved to {video_path}.")

        config = {"configurable": {"thread_id": "2"}}
        bot_reply = ""  # Initialize bot_reply as an empty string

        async def event_stream():
            nonlocal bot_reply  # Access the bot_reply string
            async for event in graph_app.astream_events(
                {
                    "user_id": user_id,
                    "question": question,
                    "pdf": file_path,
                    "video": video_path,
                },
                version="v1",
                config=config,
            ):
                if event["event"] == "on_chat_model_stream":
                    chunk = event["data"]["chunk"].content
                    bot_reply += chunk  # Append each chunk to bot_reply
                    print(chunk)
                    yield chunk

            connection = get_db_connection()
            cursor = connection.cursor()
            # After streaming, insert bot's reply into the database
            bot_message_query = "INSERT INTO messages (session_id, session_title, sender, text, name) VALUES (%s, %s, %s, %s, %s)"
            cursor.execute(
                bot_message_query, ("1", session_tit, "bot", bot_reply, "cow")
            )  # Use authenticated user's name
            connection.commit()

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    except mysql.connector.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    finally:
        cursor.close()
        connection.close()


@app.get("/messages/{session_id}")
async def fetch_messages(session_id: str):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # Retrieve all messages for the session
    cursor.execute(
        "SELECT sender, text FROM messages WHERE session_id = %s", (session_id,)
    )
    messages = cursor.fetchall()

    cursor.close()
    connection.close()

    return {"messages": messages}


@app.get("/sessions")
async def fetch_unique_sessions():
    connection = get_db_connection()
    if not connection:
        raise HTTPException(status_code=500, detail="Failed to connect to the database")

    try:
        cursor = connection.cursor(dictionary=True)
        # Fetch unique session titles
        cursor.execute("SELECT DISTINCT session_title FROM messages")
        sessions = cursor.fetchall()

    except mysql.connector.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    finally:
        cursor.close()
        connection.close()

    return {"sessions": sessions}


# Route to update session title
@app.put("/update-session-title")
async def update_session_title(request: UpdateSessionTitleRequest):
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        # Update the session title in the database
        update_query = "UPDATE messages SET session_title = %s WHERE session_id = %s"
        cursor.execute(update_query, (request.new_title, 1))
        connection.commit()

    except mysql.connector.Error as err:
        raise HTTPException(
            status_code=500, detail=f"Error updating session title: {err}"
        )
    finally:
        cursor.close()
        connection.close()

    return {"message": "Session title updated successfully"}


# Route to fetch messages by session title
@app.get("/messages/title/{session_title}")
async def fetch_messages_by_title(session_title: str):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # Retrieve all messages for the session title
    cursor.execute(
        "SELECT session_id, sender, text FROM messages WHERE session_title = %s",
        (session_title,),
    )
    messages = cursor.fetchall()

    cursor.close()
    connection.close()

    return {"messages": messages}


# Route to handle PDF, video, and YouTube URL submission
@app.post("/submit")
async def submit_data(
    pdf: UploadFile = File(None), video: UploadFile = File(None), url: str = Form(None)
):
    pdf_path, video_path = None, None

    # Save PDF file
    if pdf:
        pdf_path = os.path.join("chatbot/_files", pdf.filename)
        with open(pdf_path, "wb") as f:
            f.write(pdf.file.read())

    # Save video file
    if video:
        video_path = os.path.join("chatbot/_videos", video.filename)
        with open(video_path, "wb") as f:
            f.write(video.file.read())

    response_message = {
        "message": "Data received successfully",
        "pdf_path": pdf_path if pdf else "No PDF uploaded",
        "video_path": video_path if video else "No video uploaded",
        "youtube_url": url if url else "No YouTube URL provided",
    }

    return response_message

    # Search for session titles based on a query string


@app.get("/search/")
async def search_session_titles(query: str = Query(..., min_length=1)):
    connection = get_db_connection()
    if not connection:
        raise HTTPException(status_code=500, detail="Failed to connect to the database")

    try:
        cursor = connection.cursor(dictionary=True)
        # SQL Query to find session titles that contain the search term
        search_query = "SELECT DISTINCT session_title FROM messages WHERE text LIKE %s"
        cursor.execute(search_query, (f"%{query}%",))
        sessions = cursor.fetchall()

        if not sessions:
            return {"message": "No sessions found."}

    except mysql.connector.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    finally:
        cursor.close()
        connection.close()

    return {"sessions": [session["session_title"] for session in sessions]}


class WebhookPayload(BaseModel):
    eventType: str = None
    page: dict = None


@app.post("/confluence-webhook")
async def handle_confluence_webhook(payload: WebhookPayload):
    if not payload:
        raise HTTPException(status_code=400, detail="No payload provided")

    event_type = payload.eventType

    if event_type == "page_created":
        page_info = payload.page or {}
        page_id = page_info.get("id")
        page_title = page_info.get("title")
        print(f"New Page Created: {page_title}")

        if page_id:
            cloudid = get_cloudid()
            if cloudid:
                content = fetch_page_content(cloudid, page_id)
                if content:
                    print(f"Page Content: {content}")
                else:
                    print("Failed to fetch page content.")
            else:
                print("Failed to retrieve cloudid.")

    print(
        "Full Webhook Payload:", json.dumps(payload.dict(), indent=2)
    )  # Using json.dumps for formatted output
    return {"status": "received"}


@app.post("/configure")
async def configure_webhook(trigger_name: str):
    webhook_path = f"/webhook/{trigger_name}"  # Unique webhook path
    try:
        add_route(
            app, webhook_path, trigger_name, method_name=f"{trigger_name}_listener"
        )
        return {
            "message": f"{trigger_name} Webhook configured",
            "webhook_url": webhook_path,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# An API endpoint to remove a webhook listener
@app.post("/remove")
async def remove_webhook(webhook_path: str):
    try:
        remove_route(app, webhook_path)
        return {"message": f"{webhook_path} Webhook removed"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Run the FastAPI app using Uvicorn or Gunicorn if deployed on a server
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
