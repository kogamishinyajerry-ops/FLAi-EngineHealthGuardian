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
        ),
        ScenarioData(
            name="振动",
            key="vibration",
            gold=build_gold_labels(vib_ev, store),
            metrics=compute(build_gold_labels(vib_ev, store)),
        ),
    ]


def test_render_produces_valid_self_contained_html(tmp_path):
    html_out = render_dashboard(_scenarios(tmp_path))
    assert html_out.startswith("<!doctype html>")
    assert "<html" in html_out and "</html>" in html_out
    assert "<style>" in html_out and "<script>" in html_out
    # fully offline: no external http(s) references
    assert "http://" not in html_out
    assert "https://" not in html_out


def test_dashboard_contains_engines_status_and_metrics(tmp_path):
    html_out = render_dashboard(_scenarios(tmp_path))
    # scenario tabs + both scenario sections
    assert "EGT 裕度" in html_out
    assert "振动" in html_out
    assert 'data-name="egt"' in html_out
    assert 'data-name="vibration"' in html_out
    # all three statuses rendered as badges
    for status in ("nominal", "advisory", "abstain"):
        assert f'class="status {status}"' in html_out
    # engines from both scenarios appear
    for esn in ("ESN_DEGRADE_02", "ESN_VIB_DEGRADE"):
        assert esn in html_out
    # provenance fields rendered
    assert "rule" in html_out.lower() or "feature" in html_out.lower()
    # confusion matrix present
    assert "matrix" in html_out
    # advisory-only footer
    assert "advisory-only" in html_out


def test_build_dashboard_cli_writes_file(tmp_path):
    import importlib

    import scripts.build_dashboard as cli

    # write demo audits + labels into tmp and point the CLI there
    egt_audit = tmp_path / "egt.jsonl"
    vib_audit = tmp_path / "vib.jsonl"
    egt_run(egt_generate(seed=1), str(egt_audit))
    vib_run(vib_generate(seed=1), str(vib_audit))
    out = tmp_path / "dash.html"
    labels = tmp_path / "labels.jsonl"

    # monkeypatch the module-level DEFAULT_SCENARIOS / paths for this test
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
