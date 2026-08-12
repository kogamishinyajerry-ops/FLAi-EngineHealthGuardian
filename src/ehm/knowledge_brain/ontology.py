"""Engine ontology v0 (single-layer RDF/OWL via rdflib).

Defines the namespace, core classes and relations from the strategy report's
7-layer model (structure / function / behavior / monitoring / maintenance /
lifecycle / environment) plus the Evidence & Regulatory layer this project adds.
v0 binds only the classes/relations the EGT slice exercises; the rest are
placeholders filled as scenarios expand.

On the report's "dual-layer graph (OWL/RDF authoritative + property-graph view)":
**deferred**. v0 is single-layer rdflib. A property-graph view can be added later
as a materialized projection — but not before a scenario proves we need it (the
report's own warning about "perfect ontology" / "pretty dashboard" applies).
"""

from __future__ import annotations

from rdflib import Graph, Namespace
from rdflib.namespace import OWL, RDF
from rdflib.term import Node

EHM = Namespace("https://comac.cn/ehm/ontology/0.1/#")

# --- Core classes -----------------------------------------------------------
ENGINE = EHM.Engine
MODULE = EHM.Module
COMPONENT = EHM.Component
PARAMETER = EHM.Parameter
OBSERVATION = EHM.Observation
ANOMALY = EHM.Anomaly
FAILURE_MODE = EHM.FailureMode
MAINTENANCE_TASK = EHM.MaintenanceTask
EVIDENCE = EHM.Evidence
CONFIGURATION = EHM.Configuration

CLASSES: tuple[Node, ...] = (
    ENGINE,
    MODULE,
    COMPONENT,
    PARAMETER,
    OBSERVATION,
    ANOMALY,
    FAILURE_MODE,
    MAINTENANCE_TASK,
    EVIDENCE,
    CONFIGURATION,
)

# --- Core relations (subset of the report's relation list) ------------------
PART_OF = EHM.partOf
INSTALLED_ON = EHM.installedOn
HAS_CONFIGURATION = EHM.hasConfiguration
PERFORMS_FUNCTION = EHM.performsFunction
OBSERVED_BY = EHM.observedBy
OBSERVES_PROPERTY = EHM.observesProperty
INDICATES = EHM.indicates
CAUSED_BY = EHM.causedBy
MAY_CAUSE = EHM.mayCause
HAS_FAILURE_MODE = EHM.hasFailureMode
REQUIRES_MAINTENANCE = EHM.requiresMaintenance
RESOLVED_BY = EHM.resolvedBy
SUPPORTED_BY_EVIDENCE = EHM.supportedByEvidence
DERIVED_BY_MODEL = EHM.derivedByModel
GOVERNED_BY_MANUAL = EHM.governedByManual
SUPERSEDES = EHM.supersedes
VALID_FOR_CONFIGURATION = EHM.validForConfiguration
HAS_CONFIDENCE = EHM.hasConfidence


def build_graph() -> Graph:
    """Return a Graph with the v0 class hierarchy declared and namespaces bound."""
    graph = Graph()
    graph.bind("ehm", EHM)
    graph.bind("owl", OWL)
    for cls in CLASSES:
        graph.add((cls, RDF.type, OWL.Class))
    return graph


__all__ = [
    "EHM",
    "ENGINE",
    "MODULE",
    "COMPONENT",
    "PARAMETER",
    "OBSERVATION",
    "ANOMALY",
    "FAILURE_MODE",
    "MAINTENANCE_TASK",
    "EVIDENCE",
    "CONFIGURATION",
    "CLASSES",
    "PART_OF",
    "INSTALLED_ON",
    "HAS_CONFIGURATION",
    "PERFORMS_FUNCTION",
    "OBSERVED_BY",
    "OBSERVES_PROPERTY",
    "INDICATES",
    "CAUSED_BY",
    "MAY_CAUSE",
    "HAS_FAILURE_MODE",
    "REQUIRES_MAINTENANCE",
    "RESOLVED_BY",
    "SUPPORTED_BY_EVIDENCE",
    "DERIVED_BY_MODEL",
    "GOVERNED_BY_MANUAL",
    "SUPERSEDES",
    "VALID_FOR_CONFIGURATION",
    "HAS_CONFIDENCE",
    "build_graph",
]
