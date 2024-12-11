import os
import google.generativeai as genai
from langchain_groq import ChatGroq
from langchain_text_splitters import TokenTextSplitter

from agents.agents import Agent
from prompts.prompts import Prompt

from utils.utils import (
    extract_pdf_text,
    parse_json_string,
)

from nodes.nodes import update_knowledge_graph


async def response_generator(state):
    """
    Generates a response using the generative model.

    Args:
        state (dict): The state containing the query and message.

    Returns:
        dict: A dictionary containing the generated response.
    """
    # model = genai.GenerativeModel("gemini-pro", generation_config={"stream": True})
    # response_draft = "just say hi bruh"
    # chat_session = model.start_chat(history=[])
    # response = chat_session.send_message(response_draft, stream=True)
    # for chunk in response:
    #     print(chunk.text)
    #     yield chunk.text

    print("response_generator invoked")

    model = ChatGroq(
        temperature=0,
        model_name="gemma2-9b-it",
        api_key=os.environ["GROQ_API_KEY"],
        streaming=True,
    )

    print(state["message"])
    response = await model.ainvoke(state["message"])
    return {"generation": response}


def axel(state):
    """
    Invokes the Axel agent to generate a response.

    Args:
        state (dict): The state containing the role and query.

    Returns:
        dict: A dictionary containing the next action and message.
    """
    print("Axel invoked")
    if state["pdf"] != None:
        print("Upload has been detected")
        return {
            "next": "reviewer",
            "message": "I have detected an upload, Reviewer please assess the document.",
            "role": "axel",
        }

    Axel = Agent(
        agent_name="Axel",
        agent_prompt=Prompt.AXEL.value,
        agent_model="gemini-1.5-flash",
    )

    response = Axel.invoke(
        query_role="user",
        query=state["question"],
    )
    print(response.text)
    response = parse_json_string(response.text)

    return {
        "next": response["next"],
        "message": response["message"],
        "role": "axel",
    }


def master_agent(state):
    """
    Invokes the Master Agent to generate a response.

    Args:
        state (dict): The state containing the role and message.

    Returns:
        dict: A dictionary containing the next action, message, and optionally action steps.
    """
    print("Master Agent invoked")
    MasterAgent = Agent(
        agent_name="Master Agent",
        agent_prompt=Prompt.MASTER_AGENT.value + Prompt.TOOL_WIKI.value,
        agent_model="gemini-1.5-pro",
    )

    response = MasterAgent.invoke(query_role=state["role"], query=state["message"])

    print(response.text)
    response = parse_json_string(response.text)
    print(response)

    if response["next"] == "tooling":
        return {
            "next": response["next"],
            "message": response["message"],
            "action_steps": response["action_steps"],
        }

    return {
        "next": response["next"],
        "message": response["message"],
        "role": "master_agent",
    }


def reviewer(state):
    """
    Invokes the Reviewer agent to generate a response.

    Args:
        state (dict): The state containing the role, message, and optionally a PDF.

    Returns:
        dict: A dictionary containing the next action and message.
    """
    print("Reviewer invoked")
    Reviewer = Agent(
        agent_name="Reviewer",
        agent_prompt=Prompt.REVIEWER.value,
        agent_model="gemini-1.5-pro",
    )

    query = state["message"]
    if state["pdf"] != None:
        pdf_text = extract_pdf_text(state["pdf"])
        query = "DOCUMENT HAS BEEN UPLOADED. PLEASE REVIEW THE DOCUMENT." + pdf_text

    response = Reviewer.invoke(query_role=state["role"], query=query)

    response = parse_json_string(response.text)
    return {
        "next": response["next"],
        "message": response["message"],
        "pdf": state["pdf"],
        "role": "reviewer",
    }


def tooling(state):
    """
    Placeholder function for the Tooling agent.

    Args:
        state (dict): The state containing the role and message.
    """
    print("Tooling invoked")
    # Tooling = Agent(
    #     agent_name="Tooling",
    #     agent_prompt=Prompt.TOOLING.value,
    #     agent_model="gemini-flash-8b",
    # )

    # response = Tooling.invoke(query_role=state["role"], query=state["action_steps"])

    # print(response.text)
    # response = parse_json_string(response.text)

    tool_node_list = []
    for tool_node in state["action_steps"]:
        tool_node_list.append(tool_node["tool_node"])
    print(tool_node_list)
    print("LET'S EXECUTE THE TOOLING NODES")
    return {
        "next": tool_node_list,
        "tooling_parameters": state["action_steps"],
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


def update_knowledge_graph(state):
    """
    Placeholder function for updating the knowledge graph.

    Args:
        state (dict): The state containing the role and message.
    """

    print("Updating knowledge graph...")
