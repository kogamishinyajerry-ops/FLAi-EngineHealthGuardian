"""Agent orchestration — LangGraph 2-node state machine (assess → respond).

The agent NEVER computes engine state. It reads ``Evidence`` objects produced by
the data + knowledge + safety brains, and calls allow-listed tools
(``agent.tools.ALLOWED_TOOLS``) to ground/format the message. It only emits
advisory text; it never changes a maintenance program or dispatch state.

**LLM plug-in point**: the ``respond`` node is deterministic by default so the
demo runs offline with no API key. A ``respond_with_llm`` variant can be wired
in here later — it must still only consume Evidence and only call tools in the
allow-list. The LLM is an interpreter, never a source of engineering truth.
"""

from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from ehm.agent.tools import format_advisory
from ehm.core.evidence import Evidence


class AgentState(TypedDict):
    """Inputs/outputs of the graph: evidence to surface, messages to emit."""

    evidence: list[Evidence]
    messages: list[str]


def assess(state: AgentState) -> dict[str, list[Evidence]]:
    """Select evidence worth surfacing. v0 surfaces everything passed in."""
    return {"evidence": state["evidence"]}


def respond(state: AgentState) -> dict[str, list[str]]:
    """Format one status-aware message per Evidence using allow-listed tools."""
    messages: list[str] = []
    for ev in state["evidence"]:
        # FIM grounding comes from the evidence's own provenance (set by the scenario
        # from authorized docs), not a hardcoded agent table (ADR-0012).
        fim = "; ".join(ev.provenance.manual_citations) or "FIM TBD"
        messages.append(
            format_advisory(
                subject=ev.subject,
                observation=ev.observation,
                status=ev.status.value,
                recommendation=ev.recommendation,
                fim=fim,
            )
        )
    return {"messages": messages}


def build_agent() -> Any:
    """Compile the 2-node graph."""
    graph = StateGraph(AgentState)
    graph.add_node("assess", assess)
    graph.add_node("respond", respond)
    graph.add_edge(START, "assess")
    graph.add_edge("assess", "respond")
    graph.add_edge("respond", END)
    return graph.compile()


def run_agent(evidence: list[Evidence]) -> list[str]:
    """Convenience entrypoint: run the graph and return the emitted messages."""
    app = build_agent()
    result = app.invoke({"evidence": evidence, "messages": []})
    if isinstance(result, dict):
        return list(result.get("messages", []))
    # Defensive: future langgraph variants returning a typed object.
    return list(getattr(result, "messages", []))
