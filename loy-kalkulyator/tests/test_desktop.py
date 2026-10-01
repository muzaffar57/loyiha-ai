from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("ezdxf")

import desktop
from src.samples import dxf_bytes, sloped_bottom

ROOT = Path(__file__).resolve().parents[1]
RECTANGLE = ROOT / "tests" / "fixtures" / "yopiq_tortburchak.dxf"


def test_desktop_module_has_no_web_stack():
    source = (ROOT / "desktop.py").read_text(encoding="utf-8")
    lowered = source.lower()
    assert "streamlit" not in lowered
    assert "fastapi" not in lowered
    assert "flask" not in lowered
    assert not (ROOT / "app.py").exists()
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
    assert "streamlit" not in requirements


def test_rectangle_summary_matches_worked_example():
    loaded = desktop.load_dxf(RECTANGLE)
    assert loaded.error is None
    row = desktop.make_report_row(loaded, 3.0, 1)
    text = desktop.part_summary_text(loaded, row)
    assert row.contour_type == "yopiq"
    assert row.p_jami_mm == pytest.approx(300)
    assert row.l_pastki_mm == pytest.approx(100)
    assert row.p_faol_mm == pytest.approx(200)
    assert row.m_1_kg == pytest.approx(2.34, abs=1e-9)
    assert row.m_without_waste_kg == pytest.approx(2.34, abs=1e-9)
    assert row.m_jami_kg == pytest.approx(2.457, abs=1e-9)
    assert "P_jami" in text and "300.000" in text
    assert "L_pastki" in text and "100.000" in text
    assert "P_faol" in text and "200.000" in text
    assert "M_1 × N" in text
    assert "+5%" in text
    assert "2.457" in text
    assert "(200 * 3.0 * 2 / 1000) * 1.95 = 2.340 kg" in text
    assert loaded.geometry is not None
    assert "millimetr" in loaded.geometry.unit_note.lower() or "Millimetr" in loaded.geometry.unit_note


def test_sloped_part_keeps_the_warning():
    folder = ROOT / "tests" / "fixtures"
    path = folder / "qiyalik_pastki.dxf"
    loaded = desktop.load_dxf(path)
    assert loaded.geometry is not None
    text = desktop.part_summary_text(loaded, desktop.make_report_row(loaded, 3.0, 1))
    assert "pastki gorizontal chiziq topilmadi" in text
    assert loaded.geometry.l_pastki_mm == pytest.approx(0)


def test_bad_dxf_is_an_uzbek_message(tmp_path: Path):
    path = tmp_path / "buzilgan.dxf"
    path.write_bytes(b"this is not a dxf")
    loaded = desktop.load_dxf(path)
    assert loaded.geometry is None
    assert loaded.error is not None
    assert "DXF" in loaded.error
    assert "Traceback" not in loaded.error


def test_quantity_parser():
    assert desktop.parse_quantity("1") == 1
    assert desktop.parse_quantity(" 4 ") == 4
    assert desktop.parse_quantity("0") is None
    assert desktop.parse_quantity("1.5") is None
    assert desktop.parse_quantity("") is None


def test_window_builds_offscreen_and_shows_rectangle():
    tk = pytest.importorskip("tkinter")
    try:
        app = desktop.LoyApp()
    except tk.TclError as exc:
        pytest.skip(f"ekran yo'q: {exc}")
    try:
        app.withdraw()
        app.add_paths([RECTANGLE])
        app.update_idletasks()
        assert app.title().startswith("Penoplast")
        assert len(app.cards) == 1
        card = app.cards[0]
        body = card.body.get("1.0", "end")
        assert "2.457" in body
        assert "200.000" in body
        assert card.tree.get_children()
        values = card.tree.item(card.tree.get_children()[0], "values")
        assert "yopiq" in values
        assert "200.000" in values
        batch = app.batch_label.cget("text")
        assert "2.457" in batch
        assert "+5%" in batch
        app.d_var.set("3.5")
        app.refresh_all()
        app.update_idletasks()
        assert "2.730" in card.body.get("1.0", "end")
    finally:
        app.destroy()


def test_samples_builder_still_importable():
    # Geometry fixtures remain usable without a window.
    blob = dxf_bytes(sloped_bottom)
    assert blob.startswith(b"0") or b"SECTION" in blob
