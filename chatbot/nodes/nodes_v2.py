from agents.agents import Agent
from prompts.prompts import Enum


def axel(state):
    Axel = Agent(
        agent_name="Axel", agent_prompt=Enum.AXEL.value, agent_model="gemini-pro"
    )


def master_agent(state):
    MasterAgent = Agent(
        agent_name="Master Agent",
        agent_prompt=Enum.MASTER_AGENT.value,
        agent_model="gemini-pro",
    )


def reviewer(state):
    Reviewer = Agent(
        agent_name="Reviewer",
        agent_prompt=Enum.REVIEWER.value,
        agent_model="gemini-pro",
    )


def tooling(state):
    Tooling = Agent(
        agent_name="Tooling",
        agent_prompt=Enum.TOOLING.value,
        agent_model="gemini-flash-8b",
    )
