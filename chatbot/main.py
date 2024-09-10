import os
import io
from fastapi import FastAPI, WebSocket, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional
from pprint import pprint
from pdfminer.high_level import extract_text
from graph.graph import graph
import json

app = FastAPI()


# Define a Pydantic model for request validation
class QueryRequest(BaseModel):
    user_id: str
    question: str
    pdf: Optional[UploadFile] = None
    mp3: Optional[UploadFile] = None
    video: Optional[UploadFile] = None


@app.websocket("/ws/query")
async def query_via_websocket(websocket: WebSocket):
    await websocket.accept()
    graph_app = graph()

    while True:
        try:
            # Wait for the message from the client
            data = await websocket.receive_text()

            # Parse incoming message
            request_data = json.loads(data)
            user_id = request_data.get("user_id")
            question = request_data.get("question")
            pdf = request_data.get("pdf")  # Assuming base64-encoded or some format
            video = request_data.get("video")  # Assuming base64-encoded or some format

            # Handle uploaded files (if any)
            if pdf:
                file_path = os.path.join("_files", "uploaded_pdf.pdf")
                with open(file_path, "wb") as f:
                    f.write(pdf)  # Assuming pdf is sent as bytes
                print("PDF content received")

            if video:
                video_path = os.path.join("_videos", "uploaded_video.mp4")
                with open(video_path, "wb") as f:
                    f.write(video)  # Assuming video is sent as bytes
                print(f"Video content received and saved to {video_path}")

            # Pass the data to the graph for processing
            for output in graph_app.stream(
                {
                    "user_id": user_id,
                    "question": question,
                    "pdf": file_path if pdf else None,
                    "video": video_path if video else None,
                }
            ):
                for key, value in output.items():
                    # Send node information back via WebSocket
                    await websocket.send_text(f"Node '{key}': {value}")
                    pprint(f"Node '{key}': {value}")

            # Final generation response
            await websocket.send_text(f"Generation: {value['generation']}")
            pprint(value["generation"])

        except Exception as e:
            await websocket.send_text(f"Error: {str(e)}")
            break

    await websocket.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
