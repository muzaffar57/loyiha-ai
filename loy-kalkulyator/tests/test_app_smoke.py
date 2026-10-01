from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("streamlit")
pytest.importorskip("ezdxf")

from streamlit.testing.v1 import AppTest


def test_empty_upload_shows_uzbek_hint_without_exception():
    app = Path(__file__).resolve().parents[1] / "app.py"
    at = AppTest.from_file(str(app), default_timeout=30)
    at.run(timeout=30)
    assert not at.exception
    texts = " ".join(item.value for item in at.info)
    assert "DXF" in texts
    assert "yuklang" in texts.lower()
