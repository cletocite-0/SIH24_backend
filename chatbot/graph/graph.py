from langgraph.graph import END, StateGraph, START
from langgraph.checkpoint.memory import MemorySaver

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
    meeting_shu,
    chatbot,
    chatbot_rag_router,
    check_uploads,
    generate_image_graph,
)


def graph():
    workflow = StateGraph(GraphState)

    # config = {"thread_id": "abc1"}
    memory = MemorySaver()

    # Define the nodes

    workflow.add_node("update_knowledge_graph", update_knowledge_graph)  # pdf-email
    workflow.add_node("route", route)  # route
    workflow.add_node("neo4j_user_node", neo4j_user_node)  # neo4j_user_node
    workflow.add_node("neo4j_common_node", neo4j_common_node)  # neo4j_common_node
    workflow.add_node("generate", generate)
    workflow.add_node("chatbot", chatbot)
    workflow.add_node("video_processing", video_processing)
    workflow.add_node("summarize", summarize)
    workflow.add_node("tech_support", tech_support)
    workflow.add_node("schedule_meeting", meeting_shu)
    workflow.add_node("send_mail", send_email)
    workflow.add_node("route_summarization_usernode", route_summarization_usernode)
    workflow.add_node("chatbot_rag_router", chatbot_rag_router)
    workflow.add_node("generate_image_graph", generate_image_graph)

    # Build graph
    workflow.add_conditional_edges(
        START,
        check_uploads,
        {
            "update_knowledge_graph": "update_knowledge_graph",
            "video_processing": "video_processing",
            "chatbot_rag_router": "chatbot_rag_router",
        },
    )
    workflow.add_conditional_edges(
        "chatbot_rag_router",
        lambda x: x["next"],
        {"route": "route", "chatbot": "chatbot"},
    )
    workflow.add_conditional_edges(
        "route",
        lambda x: x["next"],
        {
            "common_node": "neo4j_common_node",
            "user_node": "neo4j_user_node",
            "tech_support": "tech_support",
            "schedule_meeting": "schedule_meeting",
        },
    )
    workflow.add_edge("neo4j_common_node", "generate")
    workflow.add_edge("neo4j_user_node", "generate")
    workflow.add_edge("video_processing", "update_knowledge_graph")
    workflow.add_edge("update_knowledge_graph", "route_summarization_usernode")
    workflow.add_edge("tech_support", "send_mail")
    workflow.add_edge("send_mail", END)
    workflow.add_edge("generate_image_graph", END)
    workflow.add_edge("schedule_meeting", END)
    workflow.add_edge("chatbot", END)

    workflow.add_conditional_edges(
        "route_summarization_usernode",
        lambda x: x["next"],
        {
            "neo4j_user_node": "neo4j_user_node",
            "summarize": "summarize",
            "generate_image_graph": "generate_image_graph",
        },
    )

    workflow.add_edge("summarize", "generate")

    workflow.set_finish_point("generate")
    # workflow.set_finish_point("send_mail")

    # Compile
    graph = workflow.compile(checkpointer=memory)

    return graph
