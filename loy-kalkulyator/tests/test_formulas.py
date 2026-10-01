from __future__ import annotations

import pytest

pytest.importorskip("ezdxf")

from src.formulas import ThicknessError, calculate_mass
from src.geometry import analyze_dxf
from src.samples import closed_rectangle, dxf_bytes, open_polyline_250


def test_rectangle_worked_example():
    part = analyze_dxf(dxf_bytes(lambda: closed_rectangle()))
    mass = calculate_mass(part.p_faol_mm, 3.0, 1)
    assert part.p_faol_mm == pytest.approx(200)
    assert mass.m_1_kg == pytest.approx(2.34, abs=1e-9)
    assert mass.m_without_waste_kg == pytest.approx(2.34, abs=1e-9)
    assert mass.waste_kg == pytest.approx(0.117, abs=1e-9)
    assert mass.m_jami_kg == pytest.approx(2.457, abs=1e-9)
    assert "200" in mass.formula
    assert "3.0" in mass.formula
    assert "2.340" in mass.formula
    assert "1.05" in mass.formula
    assert "2.457" in mass.formula


def test_open_polyline_mass_uses_full_length():
    part = analyze_dxf(dxf_bytes(open_polyline_250))
    mass = calculate_mass(part.p_faol_mm, 4.0, 2)
    # M_1 = (250 * 4 * 2 / 1000) * 1.95 = 3.9
    assert mass.m_1_kg == pytest.approx(3.9, abs=1e-9)
    assert mass.m_without_waste_kg == pytest.approx(7.8, abs=1e-9)
    assert mass.m_jami_kg == pytest.approx(8.19, abs=1e-9)


def test_thickness_is_limited_to_three_values():
    calculate_mass(200, 3.5, 1)
    with pytest.raises(ThicknessError):
        calculate_mass(200, 5.0, 1)


def test_quantity_must_be_positive_int():
    with pytest.raises(ValueError):
        calculate_mass(200, 3.0, 0)
