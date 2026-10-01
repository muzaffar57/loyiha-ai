"""DXF $INSUNITS ni millimetrga o'tkazish."""

from __future__ import annotations

# AutoCAD INSUNITS kodlari. Qiymat — shu birlikdagi 1 ning millimetrdagi uzunligi.
INSUNITS_TO_MM: dict[int, float] = {
    0: 1.0,  # birliksiz — millimetr deb olamiz
    1: 25.4,  # dyuym
    2: 304.8,  # fut
    3: 1_609_344.0,  # milya
    4: 1.0,  # millimetr
    5: 10.0,  # santimetr
    6: 1000.0,  # metr
    7: 1_000_000.0,  # kilometr
    8: 2.54e-5,  # mikrodyuym
    9: 0.0254,  # mil (0.001 dyuym)
    10: 914.4,  # yard
    11: 1e-7,  # angstrem
    12: 1e-6,  # nanometr
    13: 1e-3,  # mikrometr
    14: 100.0,  # detsimetr
    15: 10_000.0,  # dekametr
    16: 100_000.0,  # gektometr
    17: 1e12,  # gigametr
    18: 1.495978707e14,  # astronomik birlik
    19: 9.4607304725808e18,  # yorug'lik yili
    20: 3.0856775814913673e19,  # parsek
}

INSUNIT_NAMES_UZ: dict[int, str] = {
    0: "birliksiz",
    1: "dyuym",
    2: "fut",
    3: "milya",
    4: "millimetr",
    5: "santimetr",
    6: "metr",
    7: "kilometr",
    8: "mikrodyuym",
    9: "mil",
    10: "yard",
    11: "angstrem",
    12: "nanometr",
    13: "mikrometr",
    14: "detsimetr",
    15: "dekametr",
    16: "gektometr",
    17: "gigametr",
    18: "astronomik birlik",
    19: "yorug'lik yili",
    20: "parsek",
}


def scale_and_note(insunits: int) -> tuple[float, str]:
    """$INSUNITS kodidan mm ko'paytmasi va UI uchun izoh qaytaradi."""
    if insunits not in INSUNITS_TO_MM:
        return (
            1.0,
            f"Noma'lum $INSUNITS={insunits}. Millimetr deb qabul qilindi.",
        )
    if insunits == 0:
        return (
            1.0,
            "Chizmada birlik ko'rsatilmagan ($INSUNITS=0). Millimetr deb qabul qilindi.",
        )
    if insunits == 4:
        return (1.0, "O'lchov birligi: millimetr ($INSUNITS=4).")
    name = INSUNIT_NAMES_UZ.get(insunits, str(insunits))
    return (
        INSUNITS_TO_MM[insunits],
        f"O'lchov birligi millimetrga o'tkazildi ($INSUNITS={insunits}, {name}).",
    )
