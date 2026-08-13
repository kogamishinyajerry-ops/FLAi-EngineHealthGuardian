"""C-MAPSS-style method validation (P4).

NASA C-MAPSS (FD001) is the public benchmark for turbofan degradation/RUL: HPC
efficiency decays (roughly linearly) over cycles, at varied onset per engine, with
operating-condition noise. We do NOT ingest real C-MAPSS here (different format,
large domain gap). Instead we reproduce its *degradation model* in our factory and
assert our physics-driven method reproduces its qualitative signature: degraded
engines show a detectable, upward EGT-residual trend that cleanly separates from
healthy engines (whose trend is flat). This validates the METHOD, not any claim of
LEAP-1C equivalence (ADR-0014 / strategy-report P1).
"""

from __future__ import annotations

from pathlib import Path

from scenarios.egt_margin.features import residual

from ehm.core.schemas import EngineSnapshot
from ehm.data_brain.synth import SynthConfig, run_factory
from ehm.data_brain.synth.config import (
    DegradationKind,
    DegradationSpec,
    EngineSpec,
)


def _cmapss_config(out_dir: Path, seed: int = 11) -> SynthConfig:
    """C-MAPSS FD001-like: healthy peers + engines with HPC decay at varied onsets."""
    fleet = (
        EngineSpec(esn="C_H1", config="CMAPSS", route_family="short_haul", n_flights=40),
        EngineSpec(esn="C_H2", config="CMAPSS", route_family="short_haul", n_flights=40),
        EngineSpec(
            esn="C_D1",
            config="CMAPSS",
            route_family="short_haul",
            n_flights=40,
            degradation=DegradationSpec(
                DegradationKind.HPC_EFFICIENCY_DECAY, onset_cycle=2, rate_per_cycle=0.002,
                max_magnitude=0.10,
            ),
        ),
        EngineSpec(
            esn="C_D2",
            config="CMAPSS",
            route_family="short_haul",
            n_flights=40,
            degradation=DegradationSpec(
                DegradationKind.HPC_EFFICIENCY_DECAY, onset_cycle=10, rate_per_cycle=0.002,
                max_magnitude=0.10,
            ),
        ),
        EngineSpec(
            esn="C_D3",
            config="CMAPSS",
            route_family="short_haul",
            n_flights=40,
            degradation=DegradationSpec(
                DegradationKind.HPC_EFFICIENCY_DECAY, onset_cycle=5, rate_per_cycle=0.003,
                max_magnitude=0.12,
            ),
        ),
    )
    return SynthConfig(
        dataset_id="cmapss-method",
        seed=seed,
        factory_version="0.1.0",
        fleet=fleet,
        out_dir=str(out_dir),
    )


def _ols_slope(values: list[float]) -> float:
    """Ordinary least-squares slope of ``values`` vs index 0..n-1 (no numpy)."""
    n = len(values)
    if n < 2:
        return 0.0
    xs = list(range(n))
    mx = sum(xs) / n
    my = sum(values) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, values, strict=True))
    den = sum((x - mx) ** 2 for x in xs)
    return num / den if den != 0 else 0.0


def _residual_series(snaps: list[EngineSnapshot], esn: str) -> list[float]:
    series = [
        residual(s)
        for s in sorted(snaps, key=lambda s: s.timestamp)
        if s.esn == esn and residual(s) is not None
    ]
    return [v for v in series if v is not None]  # narrow for mypy (residual may be None)


_DEGRADED = ("C_D1", "C_D2", "C_D3")
_HEALTHY = ("C_H1", "C_H2")


def test_hpc_decay_produces_upward_egt_residual_trend(tmp_path):
    """The method's qualitative C-MAPSS signature: degraded trends up, healthy flat."""
    out = run_factory(_cmapss_config(tmp_path))
    snaps = [
        EngineSnapshot.model_validate_json(line)
        for line in (out / "snapshots.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    slopes = {esn: _ols_slope(_residual_series(snaps, esn)) for esn in _DEGRADED + _HEALTHY}

    # every degraded engine has a clearly positive EGT-residual slope
    assert all(slopes[e] > 0.0 for e in _DEGRADED)
    # the method SEPARATES fault from no-fault: min degraded slope > max healthy slope
    assert min(slopes[e] for e in _DEGRADED) > max(slopes[e] for e in _HEALTHY)
    # healthy engines have no meaningful trend
    assert all(abs(slopes[e]) < 0.1 for e in _HEALTHY)


def test_degraded_residuals_end_higher_than_start(tmp_path):
    """C-MAPSS trajectories worsen over time: residual at end > residual at onset."""
    out = run_factory(_cmapss_config(tmp_path))
    snaps = [
        EngineSnapshot.model_validate_json(line)
        for line in (out / "snapshots.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    for esn in _DEGRADED:
        series = _residual_series(snaps, esn)
        assert len(series) >= 10
        assert series[-1] > series[0]  # worse at the end than at the start
