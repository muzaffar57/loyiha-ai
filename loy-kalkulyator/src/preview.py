"""Kesim eskizi. Streamlit siz, PNG bayt qaytaradi."""

from __future__ import annotations

import io

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from src.geometry import PartGeometry

_COATED = "#1F7A4D"
_BARE = "#C0392B"


def render_preview_png(part: PartGeometry) -> bytes:
    """Qoplanadigan qirralarni yashil, pastki yuzni qizil uzuk chiziq qilib chizadi."""
    fig, ax = plt.subplots(figsize=(6.4, 4.4), dpi=120)
    for contour in part.contours:
        for segment in contour.segments:
            if len(segment.points) < 2:
                continue
            xs = [point[0] for point in segment.points]
            ys = [point[1] for point in segment.points]
            if segment.coated:
                ax.plot(xs, ys, color=_COATED, linewidth=2.4, solid_capstyle="round")
            else:
                ax.plot(
                    xs,
                    ys,
                    color=_BARE,
                    linewidth=2.8,
                    linestyle="--",
                    solid_capstyle="round",
                )
    ax.set_aspect("equal", adjustable="datalim")
    ax.grid(True, linewidth=0.4, alpha=0.4)
    ax.set_xlabel("X, mm")
    ax.set_ylabel("Y, mm")
    ax.set_title("Kesim")
    ax.legend(
        handles=[
            Line2D([0], [0], color=_COATED, lw=2.4, label="Qoplanadigan qirra"),
            Line2D(
                [0],
                [0],
                color=_BARE,
                lw=2.4,
                ls="--",
                label="Pastki qirra (qoplanmaydi)",
            ),
        ],
        loc="best",
        fontsize=8,
    )
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    return buf.getvalue()
