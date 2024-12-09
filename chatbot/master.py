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
from graph.graph import graph
from dotenv import load_dotenv
import os
from jose import JWTError
import jwt
from pydantic import BaseModel
from typing import Optional
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends
from reportlab.pdfgen import canvas
from io import BytesIO
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Depends, Form, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional
from concurrent.futures import ThreadPoolExecutor
import asyncio

app = FastAPI()

# Create directories if not exist
os.makedirs("files", exist_ok=True)
os.makedirs("videos", exist_ok=True)

# Define allowed origins
origins = [
    "http://localhost:5173",  # Local development
    "http://192.168.31.169:5173",
]

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # Allows requests from any origin
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

db_config = {
    "user": "root",
    "password": "CowTheGreat",
    "host": "localhost",
    "database": "sihfinale",
}

# Load environment variables from the .env file
load_dotenv()

# db_config = {
#     "user": os.getenv("MYSQL_ADDON_USER"),
#     "password": os.getenv("MYSQL_ADDON_PASSWORD"),
#     "host": os.getenv("MYSQL_ADDON_HOST"),
#     "database": os.getenv("MYSQL_ADDON_DB"),
# }

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

class Update2FAStatus(BaseModel):
    email: str
    g_2fa_status: bool

class UpdateEmailStatus(BaseModel):
    email: str
    em_retrieval_status: bool
    app_password: str


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
# @app.post("/login")
# async def login(request: LoginRequest):
#     user = get_user_by_email(request.email)
#     if not user:
#         raise HTTPException(status_code=400, detail="Invalid email or password")

#     # Check if the password matches the one in the database
#     if request.password != user["password"]:
#         raise HTTPException(status_code=400, detail="Invalid email or password")

#     # Generate a JWT token
#     token = create_access_token({"sub": user["email"]})
#     print(f"Token sent to client: {token}")  # Log the token before returning
#     return {"access_token": token, "token_type": "bearer"}

# Add state to store user data
app.state.user_data = {}

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

    # Include user data in the response
    user_data = {
        "id": user["id"],
        "email": user["email"],
        "name": user["name"],
        "position": user["position"],
        "g_2fa_status": user["g_2fa_status"],
        "em_retrieval_status": user["em_retrieval_status"],
        "app_password": user["app_password"]
    }

    return {
        "access_token": token,
        "token_type": "bearer",
        "user_data": user_data  # Attach user data here
    }

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


# @app.post("/query")
# async def receive_message(
#     user: dict = Depends(get_current_user),  # Ensure the user is authenticated
#     user_id: str = Form(...),
#     question: str = Form(...),
#     pdf: Optional[UploadFile] = File(None),
#     video: Optional[UploadFile] = File(None),
# ):
#     graph_app = graph()
#     print("Query received")
#     connection = get_db_connection()

    # # Create session title based on the question
    # booltitle = 1
    # if booltitle:
    #     booltitle = 0
    #     session_tit = question[0:15]

#     if not connection:
#         raise HTTPException(status_code=500, detail="Failed to connect to the database")

#     try:
#         cursor = connection.cursor()

#         # Insert the user's message into the database
#         user_message_query = "INSERT INTO messages (session_id, session_title, sender, text, name) VALUES (%s, %s, %s, %s, %s)"
#         cursor.execute(
#             user_message_query, ("1", session_tit, "user", question, "cow")
#         )  # Use authenticated user's name
#         connection.commit()
#         print("DB UPDATED")

#         file_path = None
#         video_path = None
#         # Access the uploaded files
#         if pdf:
#             file_path = os.path.join("_files", pdf.filename)
#             with open(file_path, "wb") as f:
#                 content = await pdf.read()  # Read the file content asynchronously
#                 f.write(content)

#             print(f"PDF content received and saved to {file_path}.")

#         if video:
#             video_path = os.path.join("_videos", video.filename)
#             with open(video_path, "wb") as f:
#                 content = await video.read()  # Read the video content asynchronously
#                 f.write(content)

#             print(f"Video content received and saved to {video_path}.")

#         config = {"configurable": {"thread_id": "2"}}
#         bot_reply = ""  # Initialize bot_reply as an empty string

#         async def event_stream():
#             nonlocal bot_reply  # Access the bot_reply string
#             async for event in graph_app.astream_events(
#                 {
#                     "user_id": user_id,
#                     "question": question,
#                     "pdf": file_path,
#                     "video": video_path,
#                 },
#                 version="v1",
#                 config=config,
#             ):
#                 if event["event"] == "on_chat_model_stream":
#                     chunk = event["data"]["chunk"].content
#                     bot_reply += chunk  # Append each chunk to bot_reply
#                     print(chunk)
#                     yield chunk
                    
            
            # connection = get_db_connection()
            # cursor = connection.cursor()
#             # After streaming, insert bot's reply into the database
#             bot_message_query = "INSERT INTO messages (session_id, session_title, sender, text, name) VALUES (%s, %s, %s, %s, %s)"
#             cursor.execute(
#                 bot_message_query, ("1", session_tit, "bot", bot_reply, "cow")
#             )  # Use authenticated user's name
#             connection.commit()

#         return StreamingResponse(event_stream(), media_type="text/event-stream")

#     except mysql.connector.Error as e:
#         raise HTTPException(status_code=500, detail=f"Database error: {e}")
#     finally:
#         cursor.close()
#         connection.close()

executor = ThreadPoolExecutor(max_workers=10) 

@app.post("/query")
async def receive_message(
    user: dict = Depends(get_current_user),
    user_id: str = Form(...),
    question: str = Form(...),
    name: str = Form(...),
    pdf: Optional[UploadFile] = File(None),
    video: Optional[UploadFile] = File(None),
):
    graph_app = graph()
    print(f"Query received from user: {name}")

    # Create session title based on the question
    booltitle = 1
    if booltitle:
        booltitle = 0
        session_tit = question[0:15]

    def save_file(uploaded_file: UploadFile, folder: str):
        file_path = os.path.join(folder, uploaded_file.filename)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.file.read())
        return file_path

    async def process_request():
        try:
            connection = await asyncio.to_thread(get_db_connection)  # Offload DB connection to a thread
            cursor = connection.cursor()

            # Insert user's message into the database
            await asyncio.to_thread(
                cursor.execute,
                "INSERT INTO messages (session_id, session_title, sender, text, name) VALUES (%s, %s, %s, %s, %s)",
                ("1", session_tit, "user", question, name),
            )
            connection.commit()

            file_path, video_path = None, None
            if pdf:
                file_path = await asyncio.to_thread(save_file, pdf, "_files")
                print(f"PDF saved to {file_path}")
            if video:
                video_path = await asyncio.to_thread(save_file, video, "_videos")
                print(f"Video saved to {video_path}")

            config = {"configurable": {"thread_id": "2"}}
            bot_reply = ""

            async def event_stream():
                nonlocal bot_reply
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
                        bot_reply += chunk
                        print(chunk)
                        yield chunk

                connection = get_db_connection()
                cursor = connection.cursor()

                # Insert bot reply into the database
                await asyncio.to_thread(
                    cursor.execute,
                    "INSERT INTO messages (session_id, session_title, sender, text, name) VALUES (%s, %s, %s, %s, %s)",
                    ("1", session_tit, "bot", bot_reply, name),
                )
                connection.commit()

            return StreamingResponse(event_stream(), media_type="text/event-stream")

        except mysql.connector.Error as e:
            raise HTTPException(status_code=500, detail=f"Database error: {e}")
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

    # Use asyncio to process the request concurrently
    return await process_request()


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


# @app.get("/sessions")
# async def fetch_unique_sessions():
#     connection = get_db_connection()
#     if not connection:
#         raise HTTPException(status_code=500, detail="Failed to connect to the database")

#     try:
#         cursor = connection.cursor(dictionary=True)
#         # Fetch unique session titles
#         cursor.execute("SELECT DISTINCT session_title FROM messages")
#         sessions = cursor.fetchall()

#     except mysql.connector.Error as e:
#         raise HTTPException(status_code=500, detail=f"Database error: {e}")
#     finally:
#         cursor.close()
#         connection.close()

#     return {"sessions": sessions}

@app.post("/sessions")
async def fetch_unique_sessions(request: Request):
    # Parse the request body to get the user dictionary
    try:
        body = await request.json()
        user = body.get("user", {})
        user_name = user.get("name")  # Extract the user's name
        print(f"Received user data: {user}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid request body: {e}")

    if not user_name:
        raise HTTPException(status_code=400, detail="User name is required")

    connection = get_db_connection()
    if not connection:
        raise HTTPException(status_code=500, detail="Failed to connect to the database")

    try:
        cursor = connection.cursor(dictionary=True)
        # Use parameterized query to safely include the user name
        query = "SELECT DISTINCT session_title FROM messages WHERE name = %s"
        cursor.execute(query, (user_name,))
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

@app.post("/update-2fa-status")
async def update_2fa_status(request: Update2FAStatus):
    try:
        print(f"Received request to update 2FA for email: {request.email} with status: {request.g_2fa_status}")
        connection = get_db_connection()
        cursor = connection.cursor()

        # Update query
        cursor.execute(
            "UPDATE users SET g_2fa_status = %s WHERE email = %s",
            (int(request.g_2fa_status), request.email),  # Convert bool to int (0 or 1)
        )
        connection.commit()

        if cursor.rowcount == 0:
            print(f"No user found with email: {request.email}")
            raise HTTPException(status_code=404, detail="User not found")

        print(f"2FA status updated successfully for email: {request.email}")
        return {"message": "2FA status updated successfully"}
    
    except Exception as e:
        print(f"Error occurred: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        connection.close()

@app.post("/update-email-retrieval-status")
async def update_email_retrieval_status(request: UpdateEmailStatus):
    try:
        print(f"Received request to update 2FA for email: {request.email} with status: {request.em_retrieval_status}")
        connection = get_db_connection()
        cursor = connection.cursor()

        # Update query
        cursor.execute(
            "UPDATE users SET em_retrieval_status = %s, app_password=%s WHERE email = %s",
             (int(request.em_retrieval_status), request.app_password  ,request.email), 
              # Convert bool to int (0 or 1)
        )
        connection.commit()

        if cursor.rowcount == 0:
            print(f"No user found with email: {request.email}")
            raise HTTPException(status_code=404, detail="User not found")

        print(f"Email Status updated successfully for email: {request.email}")
        return {"message": "Email status updated successfully"}
    
    except Exception as e:
        print(f"Error occurred: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        connection.close()

@app.get("/download_chat/{name}")
async def download_chat(name: str):
    # Step 1: Fetch messages from the database
    connection = get_db_connection()  # Replace with your DB connection
    cursor = connection.cursor()
    cursor.execute("SELECT sender, text, timestamp FROM messages WHERE name=%s", (name,))
    messages = cursor.fetchall()
    connection.close()

    # Step 2: Generate PDF
    pdf_buffer = BytesIO()
    pdf = canvas.Canvas(pdf_buffer)
    pdf.drawString(100, 800, "Chat Conversation")  # Title
    y = 780
    for sender, text, timestamp in messages:
        pdf.drawString(50, y, f"{timestamp} - {sender}: {text}")
        y -= 20  # Adjust line height
        if y < 50:  # Prevent text overflow
            pdf.showPage()
            y = 800

    pdf.save()
    pdf_buffer.seek(0)

    # Step 3: Send PDF as a response
    headers = {
        'Content-Disposition': f'attachment; filename="chat_{name}.pdf"'
    }
    return Response(pdf_buffer.getvalue(), media_type='application/pdf', headers=headers)

# Run the FastAPI app using Uvicorn or Gunicorn if deployed on a server
if __name__ == "__main__":
    uvicorn.run("master:app", host="0.0.0.0", port=8080, reload=True)
