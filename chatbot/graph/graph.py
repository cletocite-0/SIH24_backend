from langgraph.graph import END, StateGraph, START

from state import GraphState
from nodes import (
    route,
    neo4j_user_node,
    neo4j_common_node,
    generation,
    review_generation,
    regenerate,
    human_in_the_loop,
)

from tools import send_email


def graph():
    workflow = StateGraph(GraphState)

    # Define the nodes
    workflow.add_node("neo4j_user_node", neo4j_user_node)  # neo4j_user_node
    workflow.add_node("neo4j_common_node", neo4j_common_node)  # neo4j_common_node
    workflow.add_node("generation", generation)
    workflow.add_node("human_in_the_loop", human_in_the_loop)
    workflow.add_node("send_email", send_email)  # send_email
    workflow.add_node("review_generation", review_generation)  # review_generation
    workflow.add_node("regenerate", regenerate)  # regenerate

    # Build graph
    workflow.add_conditional_edges(
        START,
        route,
        {
            "common_node": "neo4j_common_node",
            "user_node": "neo4j_user_node",
        },
    )
    workflow.add_edge("neo4j_common_node", "generate")
    workflow.add_edge("neo4j_user_node", "generate")
    workflow.add_edge("generate", "review_generation")

    workflow.add_conditional_edges(
        "review_generation",
        review_generation,
        {
            "transform_query": "transform_query",
            "proceed": human_in_the_loop,
        },
    )

    workflow.add_conditional_edges(
        "humain_in_the_loop",
        human_in_the_loop,
        {
            "email": "send_email",
            "ticket": "send_ticket",
            "respond": END,
        },
    )

    workflow.add_edge("send_email", END)

    # Compile
    graph = workflow.compile()

    return graph
