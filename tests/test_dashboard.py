from scenarios.egt_margin.pipeline import run as egt_run
from scenarios.egt_margin.synthetic import generate as egt_generate
from scenarios.vibration.pipeline import run as vib_run
from scenarios.vibration.synthetic import generate as vib_generate

from ehm.dashboard import ScenarioData, render_dashboard
from ehm.feedback import LabelStore, build_gold_labels, compute


def _scenarios(tmp_path) -> list[ScenarioData]:
    egt_ev = egt_run(egt_generate(seed=42), str(tmp_path / "egt.jsonl")).evidence
    vib_ev = vib_run(vib_generate(seed=42), str(tmp_path / "vib.jsonl")).evidence
    store = LabelStore(tmp_path / "labels.jsonl")
    return [
        ScenarioData(
            name="EGT 裕度",
            key="egt",
            gold=build_gold_labels(egt_ev, store),
            metrics=compute(build_gold_labels(egt_ev, store)),
            summary={"snapshots_in": 54, "snapshots_clean": 54, "evidence_out": 3},
        ),
        ScenarioData(
            name="振动",
            key="vibration",
            gold=build_gold_labels(vib_ev, store),
            metrics=compute(build_gold_labels(vib_ev, store)),
            summary={"snapshots_in": 54, "snapshots_clean": 54, "evidence_out": 3},
        ),
    ]


def test_render_produces_valid_self_contained_html(tmp_path):
    out = render_dashboard(_scenarios(tmp_path))
    assert out.startswith("<!doctype html>")
    assert "<html" in out and "</html>" in out
    assert "<style>" in out and "<script>" in out
    assert "http://" not in out
    assert "https://" not in out


def test_dashboard_has_views_charts_drawers_and_pipeline(tmp_path):
    out = render_dashboard(_scenarios(tmp_path))
    # scenario tabs + sections
    assert "EGT 裕度" in out and "振动" in out
    assert 'data-name="egt"' in out and 'data-name="vibration"' in out
    # three views per scenario
    assert 'data-view="fleet"' in out
    assert 'data-view="flow"' in out
    assert 'data-view="model"' in out
    # status badges for all three states (drawers render every status)
    for status in ("nominal", "advisory", "abstain"):
        assert f"badge {status}" in out
    # engines from both scenarios
    for esn in ("ESN_DEGRADE_02", "ESN_VIB_DEGRADE"):
        assert esn in out
    # SVG charts present
    assert "spark-line" in out  # sparkline polylines
    assert "rpoly" in out  # confidence radar
    # engine detail drawers (progressive disclosure)
    assert 'class="drawer"' in out
    # pipeline stages with counts
    assert 'class="stage"' in out and "ACARS/QAR" in out
    # anomaly-first + collapsed normals
    assert "需要关注" in out and "正常 ·" in out
    assert "advisory-only" in out


def test_build_dashboard_cli_writes_file(tmp_path):
    import importlib

    import scripts.build_dashboard as cli

    egt_audit = tmp_path / "egt.jsonl"
    vib_audit = tmp_path / "vib.jsonl"
    egt_run(egt_generate(seed=1), str(egt_audit))
    vib_run(vib_generate(seed=1), str(vib_audit))
    out = tmp_path / "dash.html"
    labels = tmp_path / "labels.jsonl"

    original = cli.DEFAULT_SCENARIOS
    cli.DEFAULT_SCENARIOS = (
        ("EGT 裕度", "egt", str(egt_audit)),
        ("振动", "vibration", str(vib_audit)),
    )
    try:
        rc = cli.main(["--labels", str(labels), "--out", str(out), "--no-open"])
    finally:
        cli.DEFAULT_SCENARIOS = original
        importlib.reload(cli)

    assert rc == 0
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert "ESN_DEGRADE_02" in text and "advisory-only" in text
