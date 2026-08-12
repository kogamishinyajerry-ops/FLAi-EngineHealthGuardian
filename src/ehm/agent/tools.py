"""Tool allow-list for the agent.

Per the cardinal rule "the LLM never computes engine state", every tool the agent
may call is enumerated here (**allow-list, not open function-calling**).

The maintenance-reference grounding (FIM task) used to live in a hardcoded
``_FIM_TABLE`` here, which was EGT-specific and wrong for other scenarios
(vibration/oil returned "FIM TBD"). It is now read from
``Evidence.provenance.manual_citations`` — each scenario already sets it from the
authorized docs it knows. So the agent no longer re-derives FIM; it just renders
what the evidence already carries (ADR-0012).
"""

from __future__ import annotations

# v0 allow-list: only deterministic, side-effect-free tools.
ALLOWED_TOOLS: tuple[str, ...] = ("format_advisory",)


def format_advisory(
    *,
    subject: str,
    observation: str,
    status: str,
    recommendation: str | None,
    fim: str,
) -> str:
    """Render a human-readable, status-aware message for the engineer workbench."""
    if status == "abstain":
        return (
            f"[ABSTAIN] {subject}: {observation}. "
            f"Unable to recommend automatically — route to engineering. Reference: {fim}."
        )
    if status == "advisory":
        return (
            f"[ADVISORY] {subject}: {observation}. "
            f"Recommendation (advisory-only; requires engineer approval): {recommendation}. "
            f"Reference: {fim}."
        )
    return f"[NOMINAL] {subject}: {observation}. No action."


__all__ = ["ALLOWED_TOOLS", "format_advisory"]
