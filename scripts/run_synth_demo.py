"""`make synth` entrypoint — generate a physics-driven synthetic fleet on disk.

Invoke with ``uv run python -m scripts.run_synth_demo`` from the repo root.
Produces QAR-CSV (one file per flight) + snapshots.jsonl + manifest.jsonl +
config/hash/README under ``data/synth/<dataset_id>/``, all reproducible from the
seed. This is SYNTHETIC data — not real flight data, not LEAP-1C OEM truth.
"""

from __future__ import annotations

import json
from collections import Counter

from ehm.data_brain.synth import default_config, run_factory


def main() -> None:
    config = default_config(dataset_id="synth-fleet-v1", seed=42)
    out = run_factory(config)

    manifest = [
        json.loads(line)
        for line in (out / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    qar_files = list((out / "qar_csv").glob("*.csv"))
    truth_counts = Counter(r["truth_label"] for r in manifest)
    esns = sorted({r["esn"] for r in manifest})

    width = 72
    print("=" * width)
    print("Synthetic-data factory — physics-driven fleet (P2-P3)")
    print("=" * width)
    print(f"dataset_id   : {config.dataset_id}")
    print(f"factory      : {config.factory_version}")
    print(f"seed         : {config.seed}")
    print(f"config_hash  : {config.config_hash()}")
    print(f"out_dir      : {out}")
    print("-" * width)
    print(f"engines      : {len(esns)}  ({', '.join(esns)})")
    print(f"flights      : {len(manifest)}   (QAR files: {len(qar_files)})")
    print("truth labels : " + ", ".join(f"{k}={v}" for k, v in sorted(truth_counts.items())))
    print("-" * width)
    print("Artifacts:")
    for name in (
        "manifest.jsonl",
        "snapshots.jsonl",
        "config.json",
        "config_hash.txt",
        "README.txt",
    ):
        path = out / name
        print(f"  - {name:<22} {'(missing)' if not path.exists() else path}")
    print(f"  - qar_csv/                 {len(qar_files)} flight CSVs")
    print(f"  - acars_json/reports.jsonl {len(manifest)} cruise reports")
    print(f"  - mro_json/findings.jsonl  {len(esns)} shop-visit findings (-> gold-label loop)")
    print("-" * width)
    print("Round-trip: QAR-CSV -> QarCsvAdapter -> PhaseTracker -> EngineSnapshots")
    print("(synthetic data walks the same path real data will). See README.txt for honesty notes.")
    print("-" * width)
    print("source=SYNTHETIC. Labels come only from manifest.jsonl (what was injected).")
    print("Advisory-only; nothing here changes dispatch, MEL, or maintenance program.")


if __name__ == "__main__":
    main()
