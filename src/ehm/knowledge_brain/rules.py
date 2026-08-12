"""Rule layer (placeholder).

Real rules — FMEA/FMECA, fault trees, FIM/TSM-derived expert rules — are loaded
and versioned here. v0 exposes only the failure-mode vocabulary the EGT slice
uses, so Evidence can cite ontology entities (``provenance.ontology_entities``)
and the agent can ground a recommendation in a named failure mode.
"""

from __future__ import annotations

from enum import StrEnum

from ehm.knowledge_brain.ontology import FAILURE_MODE

# Version pinned to every rule-derived Evidence (config control is mandatory).
RULES_VERSION = "rules:v0"


class EgtFailureMode(StrEnum):
    """Failure modes exercised by the EGT slice, named as ontology URIs."""

    COMPRESSOR_EFFICIENCY_DEGRADATION = "CompressorEfficiencyDegradation"
    BLEED_AIR_LEAK = "BleedAirLeak"
    FUEL_NOZZLE_DEGRADATION = "FuelNozzleDegradation"
    SENSOR_DEGRADATION = "SensorDegradation"

    def uri(self) -> str:
        """Full ontology URI for this failure mode."""
        return f"{FAILURE_MODE}{self.value}"
