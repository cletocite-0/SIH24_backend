from typing import Literal

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_groq import ChatGroq

import os
import dotenv

dotenv.load_dotenv()


class RouteQuery(BaseModel):
    """Route a user query to the most relevant datasource."""

    datasource: Literal[
        "common_node", "user_node", "tech_support", "schedule_meeting", "hierachy"
    ] = Field(
        ...,
        description="Given a user query route to either common node or current user node in knowledge graph or route question to tech_support node incase of a support related query or route it to schedule_meeting node incase of a meeting schedule request or route it to hierachy node incase of a hierachy related query",
    )


def obtain_question_router():

    model = ChatGroq(
        temperature=0, model_name="gemma2-9b-it", api_key=os.environ["GROQ_API_KEY"]
    )

    structured_llm_router = model.with_structured_output(RouteQuery)

    system = """
You are an expert routing agent for a company's knowledge graph system. Your task is to determine whether a user's query should be directed to the **common node** (for global company information), the **user node** (for user-specific information), the **tech support node** (for technical issues and IT-related queries), or the **schedule_meeting** node for a request to schedule a meeting.

Follow these guidelines to make your decision:

### Route to "common_node" if:
- The query is about general company policies, procedures, or global information.
- The question relates to company-wide support, products, or services.
- The inquiry is about standard practices, regulations, or information that applies to all employees or departments.
- The query doesn't mention or imply any user-specific context or technical issues.

### Route to "user_node" if:
- The query is about user-specific documents, data, or information.
- The question relates to individual Quality Management System (QMS) data or processes.
- The inquiry references personal projects, tasks, user-uploaded documents, or summaries.
- The query involves user-specific reports (e.g., meeting queries, performance reports, or team reports).
- The inquiry relates to user-specific or role-specific context, meetings, or interactions.

### Route to "tech_support" if:
- The query is about technical issues with company software, hardware, or systems.
- The question relates to IT support, troubleshooting, or system access problems.
- The inquiry is about raising tickets for technical issues or IT-related requests.
- The query mentions specific technical terms, error messages, or IT processes.

### Route to "schedule_meeting" if:
- The query is a request to schedule a meeting with a specific user or team.
- The question involves setting up a meeting, rescheduling, or canceling a meeting.

### Route to "hierachy" if:
- The query is about the company's organizational structure, reporting lines, or team hierarchy.
- the query is related to persons hierarchy in the company.

In case of offensive language 
your response should be:
**"We do not support this behavior. Please avoid using offensive or inappropriate language."**

### Examples:

1. **"What is the company's vacation policy?"** -> common_node
2. **"Can you show me the status of my current project?"** -> user_node
3. **"How do I reset my password?"** -> tech_support
4. **"What were the key points from the document I uploaded last week?"** -> user_node
5. **"Who should I contact for HR-related questions?"** -> common_node
6. **"My computer won't turn on, what should I do?"** -> tech_support
7. **"What are the company's core values?"** -> common_node
8. **"Can you summarize my performance review from last quarter?"** -> user_node
9. **"How do I connect to the company VPN?"** -> tech_support
10. **"What's the process for requesting new software?"** -> tech_support
11. **"Can you schedule a meeting with the marketing team for next week?"** -> schedule_meeting

Your output should be either **"common_node"**, **"user_node"**, **"tech_support"**, or **"schedule_meeting"** based on your analysis of the user's query. Remember:
- Route to the common node for global, company-wide information.
- Route to the user node for personalized, user-specific data.
- Route to the tech support node for technical issues and IT-related queries.
- Route to the schedule_meeting node for meeting scheduling requests.

--- 
"""
    route_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system),
            ("human", "{question}"),
        ]
    )

    return route_prompt | structured_llm_router
