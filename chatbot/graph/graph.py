from langgraph.graph import END, StateGraph, START

from state.state import GraphState
from nodes.nodes import (
    route,
    neo4j_user_node,
    neo4j_common_node,
    generate,
    summarize,
    update_knowledge_graph,
    tech_support,
    route_summarization_usernode,
    bad_language,
    video_processing,
    send_email,
)


def graph():
    workflow = StateGraph(GraphState)

    # Define the nodes

    workflow.add_node("update_knowledge_graph", update_knowledge_graph)  # pdf-email
    workflow.add_node("neo4j_user_node", neo4j_user_node)  # neo4j_user_node
    workflow.add_node("neo4j_common_node", neo4j_common_node)  # neo4j_common_node
    workflow.add_node("generate", generate)
    workflow.add_node("bad_language", bad_language)
    workflow.add_node("video_processing", video_processing)
    workflow.add_node("summarize", summarize)
    workflow.add_node("tech_support", tech_support)
    workflow.add_node("send_mail", send_email)
    workflow.add_node("route_summarization_usernode", route_summarization_usernode)

    # Build graph
    workflow.add_conditional_edges(
        START,
        route,
        {
            "common_node": "neo4j_common_node",
            "user_node": "neo4j_user_node",
            "update_knowledge_graph": "update_knowledge_graph",
            "video_processing": "video_processing",
            "tech_support": "tech_support",
            "bad_language": "bad_language",
        },
    )
    workflow.add_edge("neo4j_common_node", "generate")
    workflow.add_edge("neo4j_user_node", "generate")
    workflow.add_edge("video_processing", "update_knowledge_graph")
    workflow.add_edge("update_knowledge_graph", "route_summarization_usernode")
    workflow.add_edge("tech_support", "send_mail")
    workflow.add_edge("send_mail", END)
    workflow.add_edge("bad_language", END)

    workflow.add_conditional_edges(
        "route_summarization_usernode",
        lambda x: x["next"],
        {"neo4j_user_node": "neo4j_user_node", "summarize": "summarize"},
    )

    workflow.add_edge("summarize", "generate")

    workflow.set_finish_point("generate")
    # workflow.set_finish_point("send_mail")

    # Compile
    graph = workflow.compile()

    return graph