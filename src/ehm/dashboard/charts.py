"""Inline SVG chart generators (no dependencies).

Both return self-contained ``<svg>`` strings sized by viewBox so they scale.
Used by the dashboard to render residual waveforms and 4-dim confidence radars.
"""

from __future__ import annotations

import math

from ehm.core.evidence import Confidence


def sparkline(
    points: list[float],
    *,
    width: int = 150,
    height: int = 44,
    threshold: float | None = None,
    baseline: float | None = None,
    color: str = "#22d3ee",
    fill: str = "rgba(34,211,238,0.12)",
) -> str:
    """A residual waveform: area fill + line, with optional threshold/baseline guides."""
    n = len(points)
    if n == 0:
        return f'<svg class="spark" viewBox="0 0 {width} {height}"><text x="4" y="{height // 2}" fill="#64748b" font-size="10">无数据</text></svg>'

    refs = list(points)
    if baseline is not None:
        refs.append(baseline)
    if threshold is not None:
        refs.append(threshold)
    lo = min(refs)
    hi = max(refs)
    if hi == lo:
        hi = lo + 1.0
    span = hi - lo
    pad = 3

    def fx(i: int) -> float:
        return (i / (n - 1)) * (width - 2 * pad) + pad if n > 1 else width / 2

    def fy(v: float) -> float:
        return (height - pad) - ((v - lo) / span) * (height - 2 * pad)

    coords = " ".join(f"{fx(i):.1f},{fy(v):.1f}" for i, v in enumerate(points))
    area = f"M{fx(0):.1f},{height - pad} L{coords} L{fx(n - 1):.1f},{height - pad} Z"

    guides = ""
    if threshold is not None:
        ty = fy(threshold)
        guides += f'<line class="thr" x1="{pad}" y1="{ty:.1f}" x2="{width - pad}" y2="{ty:.1f}"/>'
    if baseline is not None:
        by = fy(baseline)
        guides += f'<line class="base" x1="{pad}" y1="{by:.1f}" x2="{width - pad}" y2="{by:.1f}"/>'

    return (
        f'<svg class="spark" viewBox="0 0 {width} {height}" preserveAspectRatio="none">'
        f'<path class="spark-area" d="{area}" fill="{fill}"/>'
        f'<polyline class="spark-line" points="{coords}" fill="none" stroke="{color}"/>'
        f"{guides}</svg>"
    )


_RADAR_DIMS = ("data", "model", "knowledge", "applicability")
_RADAR_ANGLES = (-90.0, 0.0, 90.0, 180.0)  # top, right, bottom, left


def radar(confidence: Confidence, *, size: int = 96) -> str:
    """A 4-axis confidence radar (data/model/knowledge/applicability)."""
    cx = cy = size / 2
    r = size / 2 - 14
    values = [getattr(confidence, d) for d in _RADAR_DIMS]

    def point(angle_deg: float, frac: float) -> tuple[float, float]:
        a = math.radians(angle_deg)
        return cx + math.cos(a) * r * frac, cy + math.sin(a) * r * frac

    rings = ""
    for frac in (0.33, 0.66, 1.0):
        pts = " ".join(f"{point(a, frac)[0]:.1f},{point(a, frac)[1]:.1f}" for a in _RADAR_ANGLES)
        rings += f'<polygon class="rgrid" points="{pts}"/>'

    axes = ""
    labels = ""
    for angle, dim in zip(_RADAR_ANGLES, _RADAR_DIMS, strict=True):
        ex, ey = point(angle, 1.0)
        axes += f'<line class="raxis" x1="{cx:.1f}" y1="{cy:.1f}" x2="{ex:.1f}" y2="{ey:.1f}"/>'
        lx, ly = point(angle, 1.28)
        anchor = "middle"
        labels += f'<text class="rlabel" x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}">{dim[0:2]}</text>'

    poly_pts = []
    for angle, value in zip(_RADAR_ANGLES, values, strict=True):
        frac = value if value is not None else 0.0
        px, py = point(angle, frac)
        poly_pts.append(f"{px:.1f},{py:.1f}")

    return (
        f'<svg class="radar" viewBox="0 0 {size} {size}">'
        f"{rings}{axes}"
        f'<polygon class="rpoly" points="{" ".join(poly_pts)}"/>'
        f"{labels}</svg>"
    )


__all__ = ["radar", "sparkline"]
