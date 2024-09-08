from langchain import hub
from langchain_core.output_parsers import StrOutputParser
from langchain_groq import ChatGroq

import os


def obtain_rag_chain():

    prompt = hub.pull("rlm/rag-prompt")

    GROQ_API_KEY = "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"
    os.environ["GROQ_API_KEY"] = GROQ_API_KEY

    llm = ChatGroq(temperature=0, model_name="gemma2-9b-it")

    rag_chain = prompt | llm | StrOutputParser()

    return rag_chain
