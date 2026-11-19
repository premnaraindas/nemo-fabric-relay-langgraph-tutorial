"""A small support agent: plain LangChain and LangGraph, nothing NVIDIA-specific."""
import json

from langchain.agents import create_agent
from langchain_core.tools import tool

DELETED = []


@tool
def lookup_customer(email: str) -> str:
    """Look up a customer record by email address."""
    return json.dumps({"email": email, "plan": "Enterprise", "seats": 40, "contact": "billing.owner@example.com"})


@tool
def delete_customer(email: str) -> str:
    """Permanently delete a customer record by email address."""
    DELETED.append(email)
    return "deleted"


def build_agent(model, middleware=()):
    return create_agent(model=model, tools=[lookup_customer, delete_customer], middleware=list(middleware),
                        system_prompt="You are a support assistant. Use the tools. Be brief.")
