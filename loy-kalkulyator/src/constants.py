"""Doimiy kattaliklar. Foydalanuvchi o'zgartira olmaydi."""

from __future__ import annotations

DENSITY_KG_PER_L: float = 1.95
PART_LENGTH_M: float = 2.0
WASTE_FACTOR: float = 1.05
ALLOWED_THICKNESS_MM: tuple[float, ...] = (3.0, 3.5, 4.0)

# Yopiq konturda pastki tekis qirra shu aniqlikda qidiriladi.
# Mutlaq pol 0.05 mm: millimetrli chizmadagi suzuvchi nuqta shovqini
# yutiladi, lekin bir necha millimetr ko'tarilgan qiya yuz "pastki" deb
# yutilmaydi. Baland konturda bbox balandligining 0.01% i qo'shilishi
# mumkin, lekin 0.25 mm dan oshmaydi.
Y_TOLERANCE_FLOOR_MM: float = 0.05
Y_TOLERANCE_CAP_MM: float = 0.25
Y_TOLERANCE_HEIGHT_FRACTION: float = 1e-4
