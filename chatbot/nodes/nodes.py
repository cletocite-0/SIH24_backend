from models import route_query, model_generation, human_in_the_loop


def route(state):
    """
    Route question to to retrieve information from the user or common node in neo4j.

    Args:
        state (dict): The current graph state

    Returns:
        str: Next node to call
    """

    print("---ROUTE QUESTION---")
    question = state["question"]
    question_router = route_query.obtain_question_router()

    source = question_router.invoke({"question": question})
    if source.datasource == "user_node":
        print("---ROUTE QUERY TO USER NODE IN NEO4J---")
        return "user_node"
    elif source.datasource == "common_node":
        print("---ROUTE QUERY TO COMMON NODE IN NEO4J---")
        return "common_node"


def neo4j_user_node(state):
    pass


def neo4j_common_node(state):
    pass


def generation(state):
    """
    Generate answer from retrieved documentation.

    Args:
        state (dict): The current graph state

    Returns:
        state (dict): New key added to state, generation, that contains LLM generation
    """
    print("---GENERATE---")
    question = state["question"]
    documents = state["documents"]

    rag_chain = model_generation.obtain_rag_chain()
    # RAG generation
    generation = rag_chain.invoke({"context": documents, "question": question})
    return {"documents": documents, "question": question, "generation": generation}


def human_in_the_loop(state):
    """
    Check if human intervention is required.

    Args:
        state (dict): The current graph state

    Returns:
        state (dict): Updated state with human_in_the_loop key

    """
    print("---HUMAN IN THE LOOP---")
    generation = state["generation"]
    documents = state["documents"]
    question = state["question"]

    check_human_interaction = human_in_the_loop.check_human_interaction()
    human_in_the_loop = human_in_the_loop.invoke(
        {"generation": generation, "documents": documents, "question": question}
    )
    return human_in_the_loop.binary_score


def review_generation(state):
    pass


def regenerate():
    pass
