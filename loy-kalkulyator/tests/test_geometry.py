from __future__ import annotations

import math

import pytest

ezdxf = pytest.importorskip("ezdxf")

from src.geometry import WARNING_NO_BOTTOM, analyze_dxf, y_tolerance_mm
from src.samples import (
    arc_bulge_profile,
    closed_rectangle,
    dxf_bytes,
    open_polyline_250,
    sloped_bottom,
)


def test_y_tolerance_stays_tight():
    assert y_tolerance_mm(50) == pytest.approx(0.05)
    assert y_tolerance_mm(0) == pytest.approx(0.05)
    # 10 m balandlikda ulush 1 mm bo'lardi, lekin qopqoq 0.25 mm.
    assert y_tolerance_mm(10_000) == pytest.approx(0.25)


def test_closed_rectangle_subtracts_only_the_bottom():
    part = analyze_dxf(dxf_bytes(lambda: closed_rectangle(100, 50, insunits=4)))
    assert part.insunits == 4
    assert len(part.contours) == 1
    contour = part.contours[0]
    assert contour.closed is True
    assert contour.state_label == "yopiq"
    assert part.p_jami_mm == pytest.approx(300)
    assert part.l_pastki_mm == pytest.approx(100)
    assert part.p_faol_mm == pytest.approx(200)
    assert contour.warning is None
    bare = [segment for segment in contour.segments if not segment.coated]
    coated = [segment for segment in contour.segments if segment.coated]
    assert sum(segment.length_mm for segment in bare) == pytest.approx(100)
    assert sum(segment.length_mm for segment in coated) == pytest.approx(200)


def test_split_bottom_segments_are_summed():
    def build():
        doc = ezdxf.new("R2010")
        doc.header["$INSUNITS"] = 4
        doc.modelspace().add_lwpolyline(
            [(0, 0), (40, 0), (100, 0), (100, 50), (0, 50)],
            close=True,
        )
        return doc

    part = analyze_dxf(dxf_bytes(build))
    assert part.p_jami_mm == pytest.approx(300)
    assert part.l_pastki_mm == pytest.approx(100)
    assert part.p_faol_mm == pytest.approx(200)


def test_inner_horizontal_ledge_is_not_the_back_face():
    def build():
        doc = ezdxf.new("R2010")
        doc.header["$INSUNITS"] = 4
        # Pastki tashqi qirra y=0. Ichki tokcha y=20 — ayirilmaydi.
        doc.modelspace().add_lwpolyline(
            [(0, 0), (100, 0), (100, 50), (80, 50), (80, 20), (20, 20), (20, 50), (0, 50)],
            close=True,
        )
        return doc

    part = analyze_dxf(dxf_bytes(build))
    assert part.p_jami_mm == pytest.approx(360)
    assert part.l_pastki_mm == pytest.approx(100)
    assert part.p_faol_mm == pytest.approx(260)


def test_open_polyline_does_not_subtract_bottom():
    part = analyze_dxf(dxf_bytes(open_polyline_250))
    assert len(part.contours) == 1
    contour = part.contours[0]
    assert contour.closed is False
    assert part.p_jami_mm == pytest.approx(250)
    assert part.l_pastki_mm == pytest.approx(0)
    assert part.p_faol_mm == pytest.approx(250)
    assert contour.warning is None
    assert all(segment.coated for segment in contour.segments)


def test_bulge_arc_length_is_not_the_chord():
    part = analyze_dxf(dxf_bytes(arc_bulge_profile))
    true_arc = 50 * math.pi
    true_total = 200 + true_arc
    # Vatar bo'lsa perimetr 300 mm, faol perimetr 200 mm bo'lardi.
    assert part.p_jami_mm == pytest.approx(true_total, abs=0.15)
    assert abs(part.p_jami_mm - 300) > 40
    assert part.l_pastki_mm == pytest.approx(100, abs=0.05)
    assert part.p_faol_mm == pytest.approx(true_total - 100, abs=0.15)
    assert any(segment.kind == "curve" for segment in part.contours[0].segments)
    assert part.contours[0].warning is None


def test_bottom_arc_is_coated_and_warns():
    def build():
        doc = ezdxf.new("R2010")
        doc.header["$INSUNITS"] = 4
        # Manfiy bulge — pastga qaragan yarim aylana. Tekis pastki chiziq yo'q.
        doc.modelspace().add_lwpolyline(
            [(0, 10, -1), (100, 10, 0), (100, 60, 0), (0, 60, 0)],
            format="xyb",
            close=True,
        )
        return doc

    part = analyze_dxf(dxf_bytes(build))
    true_total = 200 + 50 * math.pi
    assert part.l_pastki_mm == pytest.approx(0)
    assert part.p_jami_mm == pytest.approx(true_total, abs=0.2)
    assert part.p_faol_mm == pytest.approx(part.p_jami_mm)
    assert abs(part.p_jami_mm - 300) > 40
    assert part.contours[0].warning == WARNING_NO_BOTTOM
    assert WARNING_NO_BOTTOM in part.warnings[0]


def test_sloped_closed_shape_does_not_guess_a_bottom():
    part = analyze_dxf(dxf_bytes(sloped_bottom))
    assert part.contours[0].closed is True
    assert part.l_pastki_mm == pytest.approx(0)
    assert part.p_faol_mm == pytest.approx(part.p_jami_mm)
    assert part.p_jami_mm > 100
    assert part.contours[0].warning == WARNING_NO_BOTTOM


def test_slight_slope_is_not_treated_as_flat():
    def build():
        doc = ezdxf.new("R2010")
        doc.header["$INSUNITS"] = 4
        # 100 mm da 0.2 mm ko'tarilish — 0.05 mm toleransdan katta.
        doc.modelspace().add_lwpolyline(
            [(0, 0), (100, 0.2), (100, 50), (0, 50)],
            close=True,
        )
        return doc

    part = analyze_dxf(dxf_bytes(build))
    assert part.l_pastki_mm == pytest.approx(0)
    assert part.contours[0].warning == WARNING_NO_BOTTOM


def test_unitless_assumes_millimetres():
    def build():
        doc = ezdxf.new("R2010")
        doc.header["$INSUNITS"] = 0
        doc.modelspace().add_lwpolyline([(0, 0), (100, 0), (100, 50), (0, 50)], close=True)
        return doc

    part = analyze_dxf(dxf_bytes(build))
    assert part.insunits == 0
    assert part.p_faol_mm == pytest.approx(200)
    assert "Millimetr deb qabul qilindi" in part.unit_note


def test_metres_and_inches_convert_to_millimetres():
    metres = analyze_dxf(dxf_bytes(lambda: closed_rectangle(insunits=6)))
    inches = analyze_dxf(dxf_bytes(lambda: closed_rectangle(insunits=1)))
    assert metres.insunits == 6
    assert inches.insunits == 1
    assert metres.p_jami_mm == pytest.approx(300, abs=1e-4)
    assert metres.l_pastki_mm == pytest.approx(100, abs=1e-4)
    assert metres.p_faol_mm == pytest.approx(200, abs=1e-4)
    assert inches.p_faol_mm == pytest.approx(200, abs=1e-4)
    assert "metr" in metres.unit_note
    assert "dyuym" in inches.unit_note


def test_multiple_contours_are_summed():
    def build():
        doc = ezdxf.new("R2010")
        doc.header["$INSUNITS"] = 4
        msp = doc.modelspace()
        msp.add_lwpolyline([(0, 0), (100, 0), (100, 50), (0, 50)], close=True)
        msp.add_lwpolyline([(0, 0), (80, 0)], close=False)
        return doc

    part = analyze_dxf(dxf_bytes(build))
    assert len(part.contours) == 2
    assert part.contour_type.startswith("aralash")
    assert part.p_jami_mm == pytest.approx(300 + 80)
    assert part.l_pastki_mm == pytest.approx(100)
    assert part.p_faol_mm == pytest.approx(200 + 80)


def test_rectangle_drawn_as_four_lines_is_a_closed_loop():
    def build():
        doc = ezdxf.new("R2010")
        doc.header["$INSUNITS"] = 4
        msp = doc.modelspace()
        msp.add_line((0, 0), (100, 0))
        msp.add_line((100, 0), (100, 50))
        msp.add_line((100, 50), (0, 50))
        msp.add_line((0, 50), (0, 0))
        return doc

    part = analyze_dxf(dxf_bytes(build))
    assert len(part.contours) == 1
    assert part.contours[0].closed is True
    assert part.p_jami_mm == pytest.approx(300)
    assert part.l_pastki_mm == pytest.approx(100)
    assert part.p_faol_mm == pytest.approx(200)


def test_line_and_arc_loop_counts_arc_length():
    def build():
        doc = ezdxf.new("R2010")
        doc.header["$INSUNITS"] = 4
        msp = doc.modelspace()
        msp.add_line((0, 0), (100, 0))
        msp.add_line((100, 0), (100, 50))
        msp.add_arc((50, 50), radius=50, start_angle=0, end_angle=180)
        msp.add_line((0, 50), (0, 0))
        return doc

    part = analyze_dxf(dxf_bytes(build))
    assert len(part.contours) == 1
    assert part.contours[0].closed is True
    assert part.l_pastki_mm == pytest.approx(100, abs=0.05)
    assert part.p_faol_mm == pytest.approx(100 + 50 * math.pi, abs=0.2)


def test_classic_polyline_circle_and_spline_are_supported():
    def build():
        doc = ezdxf.new("R2010")
        doc.header["$INSUNITS"] = 4
        msp = doc.modelspace()
        msp.add_polyline2d([(0, 0), (100, 0), (100, 50), (0, 50)], close=True)
        msp.add_circle((200, 25), radius=10)
        msp.add_spline([(0, 80), (20, 100), (40, 80)])
        msp.add_ellipse((300, 25), major_axis=(15, 0), ratio=0.5)
        return doc

    part = analyze_dxf(dxf_bytes(build))
    sources = {contour.source for contour in part.contours}
    assert "POLYLINE" in sources
    assert "CIRCLE" in sources
    assert "SPLINE" in sources
    assert "ELLIPSE" in sources
    polyline = next(c for c in part.contours if c.source == "POLYLINE")
    assert polyline.p_faol_mm == pytest.approx(200)
    circle = next(c for c in part.contours if c.source == "CIRCLE")
    assert circle.closed is True
    assert circle.p_jami_mm == pytest.approx(2 * math.pi * 10, abs=0.05)
    assert circle.l_pastki_mm == pytest.approx(0)
    assert circle.warning == WARNING_NO_BOTTOM
    spline = next(c for c in part.contours if c.source == "SPLINE")
    assert spline.closed is False
    assert spline.p_faol_mm == pytest.approx(spline.p_jami_mm)
    assert spline.p_jami_mm > 40


def test_empty_bad_and_zero_geometry_raise_uzbek_errors():
    with pytest.raises(Exception) as empty:
        analyze_dxf(b"   ")
    assert "bo'sh" in str(empty.value).lower() or "bo'sh" in empty.value.message

    with pytest.raises(Exception) as bad:
        analyze_dxf(b"this is not a dxf file")
    assert "DXF" in bad.value.message

    def zero():
        doc = ezdxf.new("R2010")
        doc.modelspace().add_lwpolyline([(0, 0), (0, 0), (0, 0)], close=True)
        return doc

    with pytest.raises(Exception) as nothing:
        analyze_dxf(dxf_bytes(zero))
    assert "nol" in nothing.value.message

    def blank():
        return ezdxf.new("R2010")

    with pytest.raises(Exception) as missing:
        analyze_dxf(dxf_bytes(blank))
    assert "topilmadi" in missing.value.message


def test_fixture_files_match_the_worked_example():
    root = __import__("pathlib").Path(__file__).resolve().parents[1]
    rectangle = analyze_dxf((root / "tests" / "fixtures" / "yopiq_tortburchak.dxf").read_bytes())
    opened = analyze_dxf((root / "tests" / "fixtures" / "ochiq_polyline.dxf").read_bytes())
    arc = analyze_dxf((root / "tests" / "fixtures" / "yoyli_profil.dxf").read_bytes())
    assert rectangle.p_faol_mm == pytest.approx(200)
    assert opened.p_faol_mm == pytest.approx(250)
    assert arc.p_faol_mm == pytest.approx(100 + 50 * math.pi, abs=0.15)
