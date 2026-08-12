"""Inspect a real-format fixture through the ingestion adapters.

  uv run python -m scripts.inspect_ingestion qar
  uv run python -m scripts.inspect_ingestion acars

Shows that a realistic file format decodes deterministically into EngineSnapshots
(unit conversion + phase detection + identity), proving the platform is no longer
synthetic-only.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ehm.data_brain.ingestion import (
    EXAMPLE_ACARS_MAP,
    EXAMPLE_QAR_MAP,
    AcarsJsonAdapter,
    QarCsvAdapter,
)

FIXTURES = Path("tests/fixtures")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="inspect_ingestion")
    parser.add_argument("format", choices=("qar", "acars"))
    args = parser.parse_args(argv)

    if args.format == "qar":
        adapter: QarCsvAdapter | AcarsJsonAdapter = QarCsvAdapter(
            FIXTURES / "qar_sample.csv", EXAMPLE_QAR_MAP, esn="ESN_QAR_01", flight_id="QAR-DEMO"
        )
    else:
        adapter = AcarsJsonAdapter(FIXTURES / "acars_sample.jsonl", EXAMPLE_ACARS_MAP)

    snapshots = list(adapter.iter_snapshots())
    print(f"[{adapter.name}] decoded {len(snapshots)} EngineSnapshot(s):")
    for snap in snapshots[:8]:
        print(
            f"  [{snap.phase.value:<8}] {snap.timestamp.isoformat()}  "
            f"esn={snap.esn}  egt_c={snap.egt_c}  ff_kg_h={snap.fuel_flow_kg_h}"
        )
    if len(snapshots) > 8:
        print(f"  ... ({len(snapshots) - 8} more)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
