from langgraph.graph import END, StateGraph, START
from langgraph.checkpoint.memory import MemorySaver

from state.state import AgenticGraphState
from nodes.nodes_v2 import axel, master_agent, reviewer, tooling


def graph():
    workflow = StateGraph(AgenticGraphState)

    # Deine the nodes
    workflow.add_node("axel", axel)
    workflow.add_node("master_agent", master_agent)
    workflow.add_node("reviewer", reviewer)
    workflow.add_node("tooling", tooling)

    # Build the graph and add the edges

    graph = workflow.compile()

    return graph
