from typing import Literal

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_groq import ChatGroq

import os
import dotenv

dotenv.load_dotenv()


class RouteQuery(BaseModel):
    """Route a user query to the most relevant datasource."""

    datasource: Literal["common_node", "user_node", "tech_support"] = Field(
        ...,
        description="Given a user query route to either common node or current user node in knowledge graph or route question to tech_support node incase of a support related query..",
    )


def obtain_question_router():

    model = ChatGroq(
        temperature=0, model_name="gemma2-9b-it", api_key=os.environ["GROQ_API_KEY"]
    )

    structured_llm_router = model.with_structured_output(RouteQuery)

    system = """Certainly, I'll modify the prompt to include routing to a "tech_support" node as well. Here's the updated version:

You are an expert routing agent for a company's knowledge graph system. Your task is to determine whether a user's query should be directed to the common node (for global company information), the user node (for user-specific information), or the tech support node (for technical issues and IT-related queries) in the knowledge graph.
Follow these guidelines to make your decision:

Route to "common_node" if:

The query is about general company policies, procedures, or global information.
The question relates to company-wide support, products, or services.
The inquiry is about standard practices, regulations, or information that applies to all employees or departments.
The query doesn't mention or imply any user-specific context or technical issues.

Route to "user_node" if:

The query is about user-specific documents, data, or information.
The question relates to individual Quality Management System (QMS) data or processes.
The inquiry references personal projects, tasks, or user-uploaded documents.
The query implies or explicitly mentions individual or role-specific context.

Route to "tech_support" if:

The query is about technical issues with company software, hardware, or systems.
The question relates to IT support, troubleshooting, or system access problems.
The inquiry is about raising tickets for technical issues or IT-related requests.
The query mentions specific technical terms, error messages, or IT processes.

Examples:

"What is the company's vacation policy?" -> common_node
"Can you show me the status of my current project?" -> user_node
"How do I reset my password?" -> tech_support
"What were the key points from the document I uploaded last week?" -> user_node
"Who should I contact for HR-related questions?" -> common_node
"My computer won't turn on, what should I do?" -> tech_support
"What are the company's core values?" -> common_node
"Can you summarize my performance review from last quarter?" -> user_node
"How do I connect to the company VPN?" -> tech_support
"What's the process for requesting new software?" -> tech_support

Your output should be either "common_node", "user_node", or "tech_support" based on your analysis of the user's query. Remember, route to the common node for global, company-wide information, to the user node for personalized, user-specific data, and to the tech support node for technical issues and IT-related queries.
        """
    route_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system),
            ("human", "{question}"),
        ]
    )

    return route_prompt | structured_llm_router
