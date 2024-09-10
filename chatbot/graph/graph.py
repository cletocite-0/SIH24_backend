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
    route_after_breakpoint,
    video_processing,
    review_generation,
    regenerate,
)


def graph():
    workflow = StateGraph(GraphState)

    # Define the nodes

    workflow.add_node("update_knowledge_graph", update_knowledge_graph)  # pdf-email
    workflow.add_node("neo4j_user_node", neo4j_user_node)  # neo4j_user_node
    workflow.add_node("neo4j_common_node", neo4j_common_node)  # neo4j_common_node
    workflow.add_node("generate", generate)
    workflow.add_node("bad_language", bad_language)
    workflow.add_node("summarize", summarize)
    workflow.add_node("tech_support", tech_support)
    workflow.add_node("route_summarization_usernode", route_summarization_usernode)

    # Build graph
    workflow.add_conditional_edges(
        START,
        route,
        {
            "common_node": "neo4j_common_node",
            "user_node": "neo4j_user_node",
            "update_knowledge_graph": "update_knowledge_graph",
            "tech_support": "tech_support",
            "bad_language": "bad_language",
        },
    )
    workflow.add_edge("neo4j_common_node", "generate")
    workflow.add_edge("neo4j_user_node", "generate")
    workflow.add_edge("update_knowledge_graph", "route_summarization_usernode")
    workflow.add_edge("tech_support", END)
    workflow.add_edge("bad_language", END)
    # workflow.add_edge("tech_support", "issue_resolved_breakpoint")

    workflow.add_conditional_edges(
        "route_summarization_usernode",
        lambda x: x["next"],
        {"neo4j_user_node": "neo4j_user_node", "summarize": "summarize"},
    )

    workflow.add_edge("summarize", "generate")
    # workflow.add_edge("generate", "review_generation")

    workflow.set_finish_point("generate")
    # workflow.set_finish_point("send_mail")

    # Compile
    graph = workflow.compile()

    return graph
