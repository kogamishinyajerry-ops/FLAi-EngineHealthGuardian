"""Synthetic-data factory — physics-driven, config-driven, reproducible.

Produces canonical ``EngineSnapshot`` data by driving the gas-path / vibration /
oil physics models with explicit degradation injection, sensor reality, and
confounders. Outputs QAR-CSV (real format), canonical snapshots, and an honest
ground-truth manifest. See ``docs/synthetic-data-plan.md`` (ADR-0014).

Honesty: coefficients are generic placeholders (NOT LEAP-1C OEM); the monitoring
residual is calibration-invariant. Labels come only from the manifest (what was
injected), tagged ``source=synthetic``; never mix with real data.
"""

from ehm.data_brain.synth.config import (
    SynthConfig,
    TruthLabel,
)
from ehm.data_brain.synth.factory import default_config, run_factory

__all__ = ["SynthConfig", "TruthLabel", "default_config", "run_factory"]
