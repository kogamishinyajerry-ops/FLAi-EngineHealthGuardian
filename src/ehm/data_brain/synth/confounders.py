"""Confounders — operating-condition effects that look like faults but aren't.

A confounder (hot day, high-altitude airport, ...) changes the *environment* the
engine sees, so the physics honestly produces an EGT/oil shift — but no fault is
injected, so the manifest truth stays ``no_fault``. These are the main false-alert
source: a rule that flags "hot-day EGT" as an advisory is wrong, and the synthetic
fleet exists to expose that. Confounders are applied *before* physics (they move
OAT / field elevation inputs), not as a post-hoc offset.
"""

from __future__ import annotations

from dataclasses import dataclass

from ehm.data_brain.synth.config import ConfounderKind, ConfounderSpec


@dataclass(frozen=True)
class ResolvedConfounders:
    """Effective environment offsets active for one engine's flight."""

    oat_delta_c: float = 0.0
    field_elevation_ft: float = 0.0
    active: tuple[str, ...] = ()


def resolve_for_esn(esn: str, confounders: tuple[ConfounderSpec, ...]) -> ResolvedConfounders:
    """Fold all confounders applying to ``esn`` into one effective offset set."""
    oat_delta = 0.0
    field_elev = 0.0
    active: list[str] = []
    for c in confounders:
        if c.applies_to_esns and esn not in c.applies_to_esns:
            continue
        match c.kind:
            case ConfounderKind.HOT_DAY:
                oat_delta += c.oat_delta_c
            case ConfounderKind.COLD_DAY:
                oat_delta += c.oat_delta_c  # negative delta
            case ConfounderKind.HIGH_ALT_AIRPORT:
                field_elev += c.field_elevation_ft
        active.append(c.kind.value)
    return ResolvedConfounders(
        oat_delta_c=oat_delta, field_elevation_ft=field_elev, active=tuple(active)
    )


__all__ = ["ResolvedConfounders", "resolve_for_esn"]
