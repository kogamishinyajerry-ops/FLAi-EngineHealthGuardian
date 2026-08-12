"""Ingestion adapters.

The ``IngestionAdapter`` protocol is the seam between real data sources and the
platform. v0 ships:

- ``SyntheticAdapter``  — offline demo / tests (in-memory)
- ``QarCsvAdapter``     — decoded QAR CSV export (one engine, one flight)
- ``AcarsJsonAdapter``  — ACARS engine-report JSONL (real-time-style messages)

New sources are a new adapter + a ``ParameterMap``; every brain depends on
``EngineSnapshot`` objects, not on any specific source.
"""

from ehm.data_brain.ingestion.acars_json import AcarsJsonAdapter
from ehm.data_brain.ingestion.base import IngestionAdapter
from ehm.data_brain.ingestion.mapping import (
    EXAMPLE_ACARS_MAP,
    EXAMPLE_QAR_MAP,
    ParameterMap,
    ParamSpec,
)
from ehm.data_brain.ingestion.qar_csv import QarCsvAdapter
from ehm.data_brain.ingestion.synthetic import SyntheticAdapter

__all__ = [
    "AcarsJsonAdapter",
    "EXAMPLE_ACARS_MAP",
    "EXAMPLE_QAR_MAP",
    "IngestionAdapter",
    "ParamSpec",
    "ParameterMap",
    "QarCsvAdapter",
    "SyntheticAdapter",
]
