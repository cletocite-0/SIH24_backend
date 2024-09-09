from typing import Literal

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_groq import ChatGroq

import os
import dotenv

dotenv.load_dotenv()


class RouteQuery(BaseModel):
    """Route a user query to the most relevant datasource."""

    datasource: Literal["common_node", "user_node"] = Field(
        ...,
        description="Given a user query route to either common node or current user node in knowledge graph.",
    )


def obtain_question_router():

    model = ChatGroq(
        temperature=0, model_name="gemma2-9b-it", api_key=os.environ["GROQ_API_KEY"]
    )

    structured_llm_router = model.with_structured_output(RouteQuery)

    system = """You are an expert at routing a user question to retrive documents linked with a common node or current user node in the knowledge graph. 
    The common node is linked with documents (chunks) related to global company knowledge inlcuding policies,support or other company specific information.  The user node is linked with documents (chunks) related to user-specific knowledge which contains data regarding user QMS or user uploaded documents.
        """
    route_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system),
            ("human", "{question}"),
        ]
    )

    return route_prompt | structured_llm_router
