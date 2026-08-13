"""Physics — a simplified turbofan gas-path model (the EGT baseline).

A principled, thermodynamically-structured baseline replacing the earlier linear
placeholder. Honest scope (see ADR-0010): the functional form is real cycle physics
(ram-heated total temp -> polytropic compression -> combustor TIT -> turbine
expansion -> EGT), but the design coefficients are GENERIC public turbofan-class
values, NOT LEAP-1C OEM data (assumption A3 not granted). Absolute EGT is therefore
illustrative; the RESIDUAL used for monitoring is calibration-invariant (a constant
offset cancels), so functional correctness is what matters.

Tests assert directional physics, not absolute magnitudes.
"""

from ehm.data_brain.physics.cycle import (
    Degradation,
    EngineDesign,
    GasPathPoint,
    OperatingPoint,
    default_design,
    egt_degraded,
    egt_healthy,
    gas_path,
    operating_point_from,
    phase_environment,
)
from ehm.data_brain.physics.oil import (
    OilState,
    consumption_rate_l_per_h,
    oil_pressure,
    oil_temperature,
)
from ehm.data_brain.physics.vibration import (
    VibrationState,
    vibration_at,
    vibration_healthy,
)

__all__ = [
    "Degradation",
    "EngineDesign",
    "GasPathPoint",
    "OilState",
    "OperatingPoint",
    "VibrationState",
    "consumption_rate_l_per_h",
    "default_design",
    "egt_degraded",
    "egt_healthy",
    "gas_path",
    "oil_pressure",
    "oil_temperature",
    "operating_point_from",
    "phase_environment",
    "vibration_at",
    "vibration_healthy",
]
