"""Dashboard — static, self-contained HTML rendering of Evidence + metrics.

A read-only consumer of ``ehm.core`` + ``ehm.feedback``. Emits one offline HTML
file; see ADR-0008.
"""

from ehm.dashboard.render import ScenarioData, render_dashboard

__all__ = ["ScenarioData", "render_dashboard"]
