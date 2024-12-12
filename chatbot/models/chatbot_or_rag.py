from typing import Literal

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_groq import ChatGroq

import os
import dotenv

dotenv.load_dotenv()


class RouteQuery(BaseModel):
    # """Route a user query to the most relevant datasource."""

    # datasource: Literal["rag", "chatbot"] = Field(
    #     ...,
    #     description="Given a user query, route it to either the RAG model or the chatbot.",
    # )
    datasource: Literal["rag", "chatbot"] = Field(
        ...,
        description="Given a user query, route it to either the RAG model or the chatbot.",
    )


def obtain_chatbot_rag_router():

    model = ChatGroq(
        temperature=0, model_name="gemma2-9b-it", api_key=os.environ["GROQ_API_KEY"]
    )

    structured_llm_router = model.with_structured_output(RouteQuery)

    system = """Query Routing Prompt
You are an intelligent query router for GAIL company's AI assistant. Your task is to analyze user queries and determine whether they should be handled by:

RAG (Retrieval-Augmented Generation) system: For queries about specific company information, internal data, reporting chains (hierarchy), meeting scheduling, personal user data, technical support requests, all cybersecurity-related questions (especially those involving PDF or browser exploitation), all GAIL-specific questions, or questions related to the Whisper policy.
chatbot: For all greeting messages, programming queries, or any other queries that do not require access to specific company or personal information.

Analyze the given query carefully.
Consider the context and the potential need for specific company or personal information.
Provide your decision as either "rag" or "chatbot".
Briefly explain your reasoning in one sentence.
Example Outputs:

Query: "What was our company's revenue last quarter?"
Decision: rag
Reason: This requires access to specific company financial data.

Query: "How do I write a Python function?"
Decision: chatbot
Reason: This is a general programming question that does not require company-specific information.

Query: "Hey There"
Decision: chatbot
Reason: This is a general greeting and does not require any specific expertise.

Query: "What are some common methods for browser exploitation?"
Decision: rag
Reason: This falls under cybersecurity-related questions requiring specific expertise.

Query: "Can you give me examples of sorting algorithms?"
Decision: chatbot
Reason: This is a general knowledge question that can be efficiently answered by the chatbot.

Query: "What is the Whisper policy in our company?"
Decision: rag
Reason: This is a GAIL-specific query requiring internal company knowledge."""

    # system = "Give only rag as output"
    route_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system),
            ("human", "{question}"),
        ]
    )

    return route_prompt | structured_llm_router
