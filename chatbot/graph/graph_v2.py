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


def graph():
    workflow = StateGraph(AgenticGraphState)

    # Deine the nodes
    workflow.add_node("response_generator", response_generator)
    workflow.add_node("axel", axel)
    workflow.add_node("master_agent", master_agent)
    workflow.add_node("reviewer", reviewer)
    workflow.add_node("tooling", tooling)
    workflow.add_node("metadata_index", metadata_index)

    # tool nodes
    workflow.add_node("meeting_shu", meeting_shu)
    workflow.add_node("generate_image_graph", generate_image_graph)
    workflow.add_node("send_email", send_email)
    workflow.add_node("update_knowledge_graph", update_knowledge_graph)

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
            "tooling": "tooling",
            "metadata_index": "metadata_index",
        },
    )

    workflow.add_conditional_edges("tooling", lambda x: x["next"])

    workflow.add_edge("response_generator", END)

    graph = workflow.compile()

    return graph
