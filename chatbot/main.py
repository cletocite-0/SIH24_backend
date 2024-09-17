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
    video: Optional[UploadFile] = File(None),
):
    graph_app = graph()

    file_path = None
    video_path = None
    # Access the uploaded files
    if pdf:
        file_path = os.path.join("_files", pdf.filename)
        # Save the file
        with open(file_path, "wb") as f:
            content = await pdf.read()  # Read the file content asynchronously
            f.write(content)  # Write the file content to the defined path

        print(f"PDF content recieved and saved to {file_path}.")

    if video:
        video_path = os.path.join("_videos", video.filename)
        # Save the video file
        with open(video_path, "wb") as f:
            content = await video.read()  # Read the file content asynchronously
            f.write(content)  # Write the video content to the defined path

        print(f"Video content received and saved to {video_path}.")

    config = {"configurable": {"thread_id": "2"}}

    output = ""

    try:
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
                output += event["data"]["chunk"].content
                print(output)
    except Exception as e:
        print(f"Error during streaming: {str(e)}")
        print(e)
    print(output)

    # for output in graph_app.stream(
    #     {
    #         "user_id": user_id,
    #         "question": question,
    #         "pdf": pdf,
    #         "video": video,
    #     }
    # ):
    #     print(output)
    #     for key, value in output.items():
    #         # Node
    #         pprint(f"Node '{key}':")
    #         # Optional: print full state at each node
    #         # pprint.pprint(value["keys"], indent=2, width=80, depth=None)

    #     pprint("\n---\n")
    #     print("\n")

    # # Final generation
    # pprint(value["generation"])

    # return {"generation": value["generation"]}

    # print(output)
    # return {"generation": output["generation"]}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
