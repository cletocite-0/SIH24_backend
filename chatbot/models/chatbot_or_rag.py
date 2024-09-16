from typing import Literal

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_groq import ChatGroq

import os
import dotenv

dotenv.load_dotenv()


class RouteQuery(BaseModel):
    """Route a user query to the most relevant datasource."""

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
You are an intelligent query router for a company's AI assistant. Your task is to analyze user queries and determine whether they should be handled by:

RAG (Retrieval-Augmented Generation) system: For queries about specific company information, internal data, or personal user data.
General LLM: For broad knowledge questions or tasks not requiring specific company or personal data.

Instructions:

Analyze the given query carefully.
Consider the context and potential need for specific company or personal information.
Provide your decision as either "rag" or "chatbot".
Briefly explain your reasoning in one sentence.

Example Outputs:

Query: "What was our company's revenue last quarter?"
Decision: rag
Reason: This requires access to specific company financial data.
Query: "How do I write a Python function?"
Decision: chatbot
Reason: This is a general programming question not requiring company-specific information.
"""
    route_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system),
            ("human", "{question}"),
        ]
    )

    return route_prompt | structured_llm_router
