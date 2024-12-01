import google.generativeai as genai

from agents.agents import Agent
from prompts.prompts import Enum

from utils.utils import extract_pdf_text


async def response_generator(state):
    """
    Generates a response using the generative model.

    Args:
        state (dict): The state containing the query and message.

    Returns:
        dict: A dictionary containing the generated response.
    """
    model = genai.GenerativeModel("gemini-pro", streaming=True)
    response_draft = state["query"] + state["message"]
    response_chunk = await model.generate_content(response_draft)
    return {"response": response_chunk}


def axel(state):
    """
    Invokes the Axel agent to generate a response.

    Args:
        state (dict): The state containing the role and query.

    Returns:
        dict: A dictionary containing the next action and message.
    """
    Axel = Agent(
        agent_name="Axel",
        agent_prompt=Enum.AXEL.value,
        agent_model="gemini-1.5-flash-8b",
        tools=[
            genai.protos.Tool(
                google_search_retrieval=genai.protos.GoogleSearchRetrieval(
                    genai.protos.DynamicRetrievalConfig(
                        mode=genai.protos.DynamicRetrievalConfig.Mode.MODE_DYNAMIC,
                        dynamic_threshold=0.3,
                    )
                ),
            ),
        ],
    )

    response = Axel.invoke(
        query_role=state["role"],
        query=state["query"],
    )

    return {"next": response["next"], "message": response["message"]}


def master_agent(state):
    """
    Invokes the Master Agent to generate a response.

    Args:
        state (dict): The state containing the role and message.

    Returns:
        dict: A dictionary containing the next action, message, and optionally action steps.
    """
    MasterAgent = Agent(
        agent_name="Master Agent",
        agent_prompt=Enum.MASTER_AGENT.value,
        agent_model="gemini-1.5-pro",
    )

    response = MasterAgent.invoke(query_role=state["role"], query=state["message"])

    if response["next"] == "tooling":
        return {
            "next": response["next"],
            "message": response["message"],
            "action_steps": response["action_steps"],
        }

    return {"next": response["next"], "message": response["message"]}


def reviewer(state):
    """
    Invokes the Reviewer agent to generate a response.

    Args:
        state (dict): The state containing the role, message, and optionally a PDF.

    Returns:
        dict: A dictionary containing the next action and message.
    """
    Reviewer = Agent(
        agent_name="Reviewer",
        agent_prompt=Enum.REVIEWER.value,
        agent_model="gemini-1.5-pro",
    )

    if state["pdf"] != None:
        pass

    response = Reviewer.invoke(query_role=state["role"], query=state["message"])

    return {"next": response["next"], "message": response["message"]}


def tooling(state):
    """
    Placeholder function for the Tooling agent.

    Args:
        state (dict): The state containing the role and message.
    """
    Tooling = Agent(
        agent_name="Tooling",
        agent_prompt=Enum.TOOLING.value,
        agent_model="gemini-flash-8b",
    )


def metadata_index(state):
    """
    Placeholder function for metadata indexing.

    Args:
        state (dict): The state containing the role and message.
    """
    pass
