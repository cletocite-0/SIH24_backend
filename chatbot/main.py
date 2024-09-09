import io

from fastapi import FastAPI, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional
from pprint import pprint
from pdfminer.high_level import extract_text
import os
from graph.graph import graph

app = FastAPI()


# Define a Pydantic model for request validation
class QueryRequest(BaseModel):
    user_id: str
    question: str
    pdf: Optional[UploadFile] = None
    mp3: Optional[UploadFile] = None
    video: Optional[UploadFile] = None


@app.post("/query")
async def query(
    user_id: str = Form(...),
    question: str = Form(...),
    pdf: Optional[UploadFile] = File(None),
    mp3: Optional[UploadFile] = File(None),
    video: Optional[UploadFile] = File(None),
):
    graph_app = graph()
    # Access the uploaded files
    filename = Optional[str]
    if pdf:
        filename = pdf.filename
        # pdf_content = await pdf.read()
        # print(pdf_content)
        # pdf_stream = io.BytesIO(pdf_content)
        # Process the PDF content
        # pdf_text = extract_text(io.BytesIO(pdf_content))
        file_path = os.path.join("_files", pdf.filename)
        # Save the file
        with open(file_path, "wb") as f:
            content = await pdf.read()  # Read the file content asynchronously
            f.write(content)  # Write the file content to the defined path

        print("PDF content recieved")

    if mp3:
        mp3_content = await mp3.read()
        # Process the MP3 content
        print("MP3 content recieved")

    if video:
        video_content = await video.read()
        # Process the video content
        print("Video content recieved")

    for output in graph_app.stream(
        {
            "user_id": user_id,
            "question": question,
            "pdf": pdf,
            "mp3": mp3,
            "video": video,
        }
    ):
        for key, value in output.items():
            # Node
            pprint(f"Node '{key}':")
            # Optional: print full state at each node
            # pprint.pprint(value["keys"], indent=2, width=80, depth=None)
        pprint("\n---\n")
        print("\n")

    # Final generation
    pprint(value["generation"])

    return {"generation": value["generation"]}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
