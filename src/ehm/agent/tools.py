"""Tool allow-list for the agent.

Per the cardinal rule "the LLM never computes engine state", every tool the
agent may call is enumerated here (**allow-list, not open function-calling**).
v0 tools are deterministic, side-effect-free lookups; LLM-grounded tools (RAG
over authorized AMM/FIM/TSM with version control) plug in at the marked points.
"""

from __future__ import annotations

# v0 allow-list: only deterministic, side-effect-free tools.
ALLOWED_TOOLS: tuple[str, ...] = ("lookup_fim_task", "format_advisory")

# Mock FIM mapping. Real impl: RAG over authorized AMM/FIM/TSM with version control.
_FIM_TABLE: dict[str, str] = {
    "CompressorEfficiencyDegradation": "FIM 72-00-00 (compressor efficiency / gas-path)",
    "BleedAirLeak": "FIM 36-11-00 (pneumatic / bleed)",
    "FuelNozzleDegradation": "FIM 73-21-00 (fuel distribution)",
    "SensorDegradation": "FIM 77-20-00 (engine indicating)",
}


def lookup_fim_task(failure_mode: str) -> str:
    """Ground a failure mode in an authorized maintenance reference (mock in v0)."""
    return _FIM_TABLE.get(failure_mode, "FIM TBD — no mapping in v0")


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
