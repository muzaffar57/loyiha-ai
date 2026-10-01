"""Namuna DXF fayllar. `python -m src.samples` ularni yozadi."""

from __future__ import annotations

import io
from pathlib import Path

import ezdxf

from src.units import INSUNITS_TO_MM

ROOT = Path(__file__).resolve().parents[1]


def dxf_bytes(builder) -> bytes:
    doc = builder()
    buf = io.StringIO()
    doc.write(buf)
    return buf.getvalue().encode("utf-8")


def _new(insunits: int):
    doc = ezdxf.new("R2010")
    doc.header["$INSUNITS"] = insunits
    return doc


def closed_rectangle(width_mm: float = 100.0, height_mm: float = 50.0, insunits: int = 4):
    """Yopiq to'rtburchak. O'lchov `insunits` da, o'lcham esa millimetrda beriladi."""
    scale = INSUNITS_TO_MM[insunits]
    width = width_mm / scale
    height = height_mm / scale
    doc = _new(insunits)
    doc.modelspace().add_lwpolyline(
        [(0, 0), (width, 0), (width, height), (0, height)],
        close=True,
    )
    return doc


def open_polyline_250(insunits: int = 4):
    """Ochiq polyline, uzunligi 250 mm (150 + 100)."""
    scale = INSUNITS_TO_MM[insunits]
    doc = _new(insunits)
    doc.modelspace().add_lwpolyline(
        [(0, 0), (150 / scale, 0), (150 / scale, 100 / scale)],
        close=False,
    )
    return doc


def arc_bulge_profile(insunits: int = 4):
    """Yopiq profil: pastki qirra tekis, tepa qirra yarim aylana (bulge=1)."""
    scale = INSUNITS_TO_MM[insunits]
    def xy(x: float, y: float, bulge: float = 0.0) -> tuple[float, float, float]:
        return (x / scale, y / scale, bulge)

    doc = _new(insunits)
    # (100, 50) dagi bulge keyingi nuqtagacha — tepadagi yarim aylana.
    doc.modelspace().add_lwpolyline(
        [xy(0, 0), xy(100, 0), xy(100, 50, 1), xy(0, 50)],
        format="xyb",
        close=True,
    )
    return doc


def sloped_bottom(insunits: int = 4):
    """Yopiq uchburchak. Eng past nuqta — cho'qqi, gorizontal pastki chiziq yo'q."""
    scale = INSUNITS_TO_MM[insunits]
    doc = _new(insunits)
    doc.modelspace().add_lwpolyline(
        [(0, 0), (100 / scale, 8 / scale), (40 / scale, 70 / scale)],
        close=True,
    )
    return doc


def write_samples(root: Path | None = None) -> list[Path]:
    root = root or ROOT
    targets = {
        root / "samples" / "yopiq_tortburchak.dxf": lambda: closed_rectangle(),
        root / "samples" / "ochiq_polyline.dxf": lambda: open_polyline_250(),
        root / "samples" / "yoyli_profil.dxf": lambda: arc_bulge_profile(),
        root / "samples" / "qiyalik_pastki.dxf": lambda: sloped_bottom(),
        root / "tests" / "fixtures" / "yopiq_tortburchak.dxf": lambda: closed_rectangle(),
        root / "tests" / "fixtures" / "ochiq_polyline.dxf": lambda: open_polyline_250(),
        root / "tests" / "fixtures" / "yoyli_profil.dxf": lambda: arc_bulge_profile(),
        root / "tests" / "fixtures" / "qiyalik_pastki.dxf": lambda: sloped_bottom(),
        root / "tests" / "fixtures" / "tortburchak_metr.dxf": lambda: closed_rectangle(insunits=6),
        root / "tests" / "fixtures" / "tortburchak_dyuym.dxf": lambda: closed_rectangle(insunits=1),
    }
    written: list[Path] = []
    for path, builder in targets.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(dxf_bytes(builder))
        written.append(path)
    return written


if __name__ == "__main__":
    for path in write_samples():
        print(path)
