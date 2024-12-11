from langgraph.graph import END, StateGraph, START
from langgraph.checkpoint.memory import MemorySaver

from state.state import AgenticGraphState
from nodes.nodes_v2 import (
    axel,
    master_agent,
    reviewer,
    tooling,
    response_generator,
    metadata_index,
)
from nodes.nodes import (
    meeting_shu,
    generate_image_graph,
    send_email,
    update_knowledge_graph,
)

from tools.tools import gmeet, fetch_from_confluence, fetch_from_gdrive, send_mail


def graph():
    workflow = StateGraph(AgenticGraphState)

    tools = [
        "fetch_from_confluence",
        "fetch_from_gdrive",
        "send_mail",
        "gmeet",
    ]

    # Deine the nodes
    workflow.add_node("response_generator", response_generator)
    workflow.add_node("axel", axel)
    workflow.add_node("master_agent", master_agent)
    workflow.add_node("reviewer", reviewer)
    workflow.add_node("tooling", tooling)
    workflow.add_node("metadata_index", metadata_index)

    # tool nodes
    workflow.add_node("gmeet", gmeet)
    workflow.add_node("fetch_from_confluence", fetch_from_confluence)
    workflow.add_node("fetch_from_gdrive", fetch_from_gdrive)
    workflow.add_node("send_mail", send_mail)

    # Build the graph and add the edges
    workflow.add_edge(START, "axel")

    workflow.add_conditional_edges(
        "axel",
        lambda x: x["next"],
        {
            "response_generator": "response_generator",
            "master_agent": "master_agent",
            "reviewer": "reviewer",
        },
    )

    workflow.add_conditional_edges(
        "master_agent",
        lambda x: x["next"],
        {
            "axel": "axel",
            "tooling": "tooling",
            "metadata_index": "metadata_index",
        },
    )

    workflow.add_conditional_edges("tooling", lambda x: x["next"])

    workflow.add_edge(tools, "reviewer")

    workflow.add_conditional_edges(
        "reviewer",
        lambda x: x["next"],
        {
            "response_generator": "response_generator",
            "master_agent": "master_agent",
            "axel": "axel",
        },
    )

    workflow.add_edge("response_generator", END)

    graph = workflow.compile()

    return graph
