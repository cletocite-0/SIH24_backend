from langgraph.graph import END, StateGraph, START

from state import GraphState
from nodes import (
    route,
    neo4j_user_node,
    neo4j_common_node,
    generation,
    review_generation,
    regenerate,
)


def graph():
    workflow = StateGraph(GraphState)

    # Define the nodes
    workflow.add_node("neo4j_user_node", neo4j_user_node)  # neo4j_user_node
    workflow.add_node("neo4j_common_node", neo4j_common_node)  # neo4j_common_node
    workflow.add_node("generation", generation)  # generation
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
    workflow.add_edge("retrieve", "grade_documents")
    workflow.add_conditional_edges(
        "review_generation",
        review_generation,
        {
            "transform_query": "transform_query",
            "generate": "generate",
        },
    )
    workflow.add_edge("transform_query", "retrieve")
    workflow.add_conditional_edges(
        "generate",
        generation,
        {
            "not supported": "generate",
            "useful": END,
            "not useful": "transform_query",
        },
    )

    # Compile
    graph = workflow.compile()

    return graph
