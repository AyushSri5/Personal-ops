"""Agent state definition."""
from __future__ import annotations

from collections.abc import Sequence
from typing import Annotated

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class AgentState(TypedDict):
    """State flowing through the Personal Ops LangGraph agent."""
    messages: Annotated[Sequence[BaseMessage], add_messages]
