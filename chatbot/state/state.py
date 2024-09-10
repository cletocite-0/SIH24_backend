from io import BytesIO
from typing import List

from typing_extensions import TypedDict

from fastapi import UploadFile


class GraphState(TypedDict):
    """
    Represents the state of our graph.

    Attributes:
        question: question
        generation: LLM generation
        documents: list of documents
    """

    user_id: str
    question: str
    generation: str
    documents: List[str]
    # pdf: BytesIO
    breakpoint: str
    pdf: str
    video: UploadFile
    support_type: str
    priority: str
    troubleshooting_steps: str
