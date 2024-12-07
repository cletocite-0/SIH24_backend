import google.generativeai as genai
from langchain_text_splitters import TokenTextSplitter

from agents.agents import Agent
from prompts.prompts import Prompt

from utils.utils import extract_pdf_text, pdf_to_documents, get_jina_embeddings


async def response_generator(state):
    """
    Generates a response using the generative model.

    Args:
        state (dict): The state containing the query and message.

    Returns:
        dict: A dictionary containing the generated response.
    """
    model = genai.GenerativeModel("gemini-pro", generation_config={"stream": True})
    response_draft = "just say hi bruh"
    response_chunk = await model.generate_content(response_draft)
    response_chunk = response_chunk.text.strip()
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
        agent_prompt=Prompt.AXEL.value,
        agent_model="gemini-1.5-flash-8b",
    )

    response = Axel.invoke(
        query_role="user",
        query=state["question"],
    )

    return {"next": "response_generator", "message": response, "role": "axel"}


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
        agent_prompt=Prompt.MASTER_AGENT.value,
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
        agent_prompt=Prompt.REVIEWER.value,
        agent_model="gemini-1.5-pro",
    )

    if state["pdf"] != None:
        pdf_text = extract_pdf_text(state["pdf"])

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
        agent_prompt=Prompt.TOOLING.value,
        agent_model="gemini-flash-8b",
    )

    response = Tooling.invoke(query_role=state["role"], query=state["action_steps"])

    return {
        "next": response["next"],
        "tooling_parameters": response["tooling_parameters"],
    }


def metadata_index(state):
    """
    Placeholder function for metadata indexing.

    Args:
        state (dict): The state containing the role and message.
    """

    print("Checking metadata index...")
    pass


def update_metadata_index(state):
    """
    Placeholder function for updating metadata indexing.

    Args:
        state (dict): The state containing the role and message.
    """

    print("Updating metadata index...")

    pass

