"""Loy massasi formulalari.

M_1 = (P_faol_mm * d_mm * L_m / 1000) * rho

P_faol va d millimetrda, L = 2 m. Bo'linma 1000 litr beradi
(mm * mm * m / 1000 = litr), rho = 1.95 kg/l esa kilogramm beradi.
M_jami = M_1 * N * 1.05 — 5% texnik chiqindi shu yerda.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from src.constants import (
    ALLOWED_THICKNESS_MM,
    DENSITY_KG_PER_L,
    PART_LENGTH_M,
    WASTE_FACTOR,
)


class ThicknessError(ValueError):
    """Qalinlik ruxsat etilgan qiymatlardan boshqa."""


def normalize_thickness_mm(d_mm: float) -> float:
    """Faqat 3.0, 3.5 yoki 4.0 mm ni qabul qiladi."""
    for allowed in ALLOWED_THICKNESS_MM:
        if abs(float(d_mm) - allowed) <= 1e-6:
            return allowed
    raise ThicknessError(
        "Qalinlik faqat 3.0, 3.5 yoki 4.0 mm bo'lishi mumkin."
    )


@dataclass(frozen=True)
class MassResult:
    d_mm: float
    n: int
    m_1_kg: float
    m_without_waste_kg: float
    waste_kg: float
    m_jami_kg: float
    formula: str


def _dec_mm(value: float) -> Decimal:
    return Decimal(f"{float(value):.10f}")


def calculate_mass(p_faol_mm: float, d_mm: float, n: int) -> MassResult:
    """Bitta detal va partiya uchun loy massasini hisoblaydi."""
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        raise ValueError("Dona soni N kamida 1 bo'lishi kerak.")
    if p_faol_mm < 0:
        raise ValueError("Faol perimetr manfiy bo'lishi mumkin emas.")

    thickness = normalize_thickness_mm(d_mm)
    perimeter = _dec_mm(p_faol_mm)
    depth = Decimal(f"{thickness:.1f}")
    length_m = Decimal(str(PART_LENGTH_M))
    density = Decimal(str(DENSITY_KG_PER_L))
    waste = Decimal(str(WASTE_FACTOR))

    m_1 = (perimeter * depth * length_m / Decimal(1000)) * density
    without_waste = m_1 * n
    m_jami = without_waste * waste
    waste_kg = m_jami - without_waste

    m_1_f = float(m_1)
    without_f = float(without_waste)
    waste_f = float(waste_kg)
    jami_f = float(m_jami)
    formula = substituted_formula(
        p_faol_mm=float(perimeter),
        d_mm=thickness,
        n=n,
        m_1_kg=m_1_f,
        m_without_waste_kg=without_f,
        m_jami_kg=jami_f,
    )
    return MassResult(
        d_mm=thickness,
        n=n,
        m_1_kg=m_1_f,
        m_without_waste_kg=without_f,
        waste_kg=waste_f,
        m_jami_kg=jami_f,
        formula=formula,
    )


def substituted_formula(
    p_faol_mm: float,
    d_mm: float,
    n: int,
    m_1_kg: float,
    m_without_waste_kg: float,
    m_jami_kg: float,
) -> str:
    """Formulani haqiqiy sonlar qo'yilgan holda qaytaradi."""
    return (
        "M_1 = (P_faol * d * 2 / 1000) * 1.95\n"
        f"M_1 = ({_fmt(p_faol_mm)} * {d_mm:.1f} * 2 / 1000) * 1.95 "
        f"= {_fmt_kg(m_1_kg)} kg\n"
        f"M_1 * N = {_fmt_kg(m_1_kg)} * {n} = {_fmt_kg(m_without_waste_kg)} kg\n"
        f"+5% chiqindi: M_jami = M_1 * N * 1.05 = "
        f"{_fmt_kg(m_without_waste_kg)} * 1.05 = {_fmt_kg(m_jami_kg)} kg"
    )


def _fmt(value: float) -> str:
    if abs(value - round(value)) < 1e-6:
        return str(int(round(value)))
    return f"{value:.3f}"


def _fmt_kg(value: float) -> str:
    return f"{value:.3f}"
