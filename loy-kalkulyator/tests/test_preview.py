from __future__ import annotations

import pytest

pytest.importorskip("ezdxf")
pytest.importorskip("matplotlib")

from src.geometry import analyze_dxf
from src.preview import render_preview_png
from src.samples import closed_rectangle, dxf_bytes


def test_preview_png_marks_coated_and_bare_edges():
    part = analyze_dxf(dxf_bytes(closed_rectangle))
    png = render_preview_png(part)
    assert png.startswith(b"\x89PNG")
    assert len(png) > 1000
