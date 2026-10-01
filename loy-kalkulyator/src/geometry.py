"""DXF profil konturini o'qiydi va qoplanadigan faol perimetrni topadi.

Qoplama faqat uch yuzga surtiladi: tepa va ikki yon. Devorga yopishadigan
pastki tekis yuz qoplanmaydi.

- Yopiq kontur: P_faol = P_jami - L_pastki. L_pastki — Y_min dagi gorizontal
  to'g'ri kesmalar yig'indisi. Yoy va qiya qirra ayirilmaydi.
- Ochiq kontur: chizuvchi faqat qoplanadigan yo'lni chizgan. P_faol = shu
  yo'l uzunligi, pastki qirra ayirilmaydi.

Yoy uzunligi vatar (chord) emas. LWPOLYLINE bulge ezdxf.path orqali egri
chiziqqa aylanadi va uzunlik shu egri chiziq bo'yicha olinadi.
"""

from __future__ import annotations

import io
import math
import tempfile
from dataclasses import dataclass, field
from typing import Iterable, Sequence

import ezdxf
from ezdxf.math import Matrix44, Vec3
from ezdxf.path import Curve3To, Curve4To, LineTo, MoveTo, Path, make_path

from src.constants import (
    Y_TOLERANCE_CAP_MM,
    Y_TOLERANCE_FLOOR_MM,
    Y_TOLERANCE_HEIGHT_FRACTION,
)
from src.units import scale_and_note

WARNING_NO_BOTTOM = "pastki gorizontal chiziq topilmadi"
WARNING_BRANCH = "Shoxlangan chiziqlar alohida ochiq kontur sifatida olindi."

_STANDALONE = {"LWPOLYLINE", "POLYLINE", "CIRCLE", "ELLIPSE", "SPLINE"}
_FRAGMENTS = {"LINE", "ARC"}
_SUPPORTED = _STANDALONE | _FRAGMENTS

# Egri chiziqni tekislashdagi maksimal sagitta, mm. Yoy vatar emas,
# uzunlik shu zichlikdagi ezdxf.path namunalaridan yig'iladi.
_CURVE_SAGITTA_MM = 0.01


class DxfAnalysisError(Exception):
    """Foydalanuvchiga ko'rsatiladigan o'zbekcha xato."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


@dataclass
class DrawSegment:
    """Kesim chizig'i. Nuqtalar millimetrda."""

    kind: str  # "line" yoki "curve"
    points: list[tuple[float, float]]
    length_mm: float
    coated: bool = True


@dataclass
class ContourGeometry:
    index: int
    closed: bool
    source: str
    p_jami_mm: float
    l_pastki_mm: float
    p_faol_mm: float
    warning: str | None
    segments: list[DrawSegment] = field(default_factory=list)

    @property
    def state_label(self) -> str:
        return "yopiq" if self.closed else "ochiq"


@dataclass
class PartGeometry:
    contours: list[ContourGeometry]
    p_jami_mm: float
    l_pastki_mm: float
    p_faol_mm: float
    unit_note: str
    insunits: int
    warnings: list[str]

    @property
    def contour_type(self) -> str:
        if not self.contours:
            return ""
        flags = {contour.closed for contour in self.contours}
        if flags == {True}:
            base = "yopiq"
        elif flags == {False}:
            base = "ochiq"
        else:
            base = "aralash"
        if len(self.contours) == 1:
            return base
        return f"{base} ({len(self.contours)} ta kontur)"


@dataclass
class _Fragment:
    segments: list[DrawSegment]
    start: tuple[float, float]
    end: tuple[float, float]
    entity_type: str


def y_tolerance_mm(bbox_height_mm: float) -> float:
    """Pastki gorizontal qirra uchun Y bo'yicha tolerans, mm.

    Mutlaq pol — 0.05 mm. Dag'al (juda baland) chizmada bbox balandligining
    kichik ulushi qo'shiladi, lekin 0.25 mm dan oshmaydi. Chegara ataylab
    tor: ozgina qiyalagan yuz jimgina pastki devor yuzi deb olinmaydi.
    """
    height = max(0.0, float(bbox_height_mm))
    fractional = Y_TOLERANCE_HEIGHT_FRACTION * height
    return min(Y_TOLERANCE_CAP_MM, max(Y_TOLERANCE_FLOOR_MM, fractional))


def analyze_dxf(data: bytes) -> PartGeometry:
    """DXF baytlaridan detal geometriyasini (mm) qaytaradi."""
    if data is None or not bytes(data).strip():
        raise DxfAnalysisError("Fayl bo'sh. DXF chizma yuklang.")
    try:
        doc = _read_document(bytes(data))
    except Exception as exc:
        raise DxfAnalysisError(
            "DXF faylni o'qib bo'lmadi. Fayl buzilgan yoki DXF formatida emas."
        ) from exc

    try:
        raw_units = doc.header.get("$INSUNITS", 0)
        insunits = int(raw_units)
    except (TypeError, ValueError):
        insunits = 0
    scale, unit_note = scale_and_note(insunits)

    standalone: list[tuple[list[DrawSegment], bool, str]] = []
    fragments: list[_Fragment] = []
    saw_supported = False
    saw_insert = False
    try:
        for entity in doc.modelspace():
            kind = entity.dxftype()
            if kind == "INSERT":
                saw_insert = True
                continue
            if kind not in _SUPPORTED:
                continue
            segments = _segments_from_entity(entity, scale)
            length = sum(segment.length_mm for segment in segments)
            if length <= 1e-9:
                saw_supported = True
                continue
            saw_supported = True
            if kind in _FRAGMENTS:
                start = segments[0].points[0]
                end = segments[-1].points[-1]
                fragments.append(
                    _Fragment(segments=segments, start=start, end=end, entity_type=kind)
                )
            else:
                standalone.append((segments, _entity_is_closed(entity), kind))
    except DxfAnalysisError:
        raise
    except Exception as exc:
        raise DxfAnalysisError(
            "DXF geometriyasini o'qishda xatolik. Chizma formati qo'llab-quvvatlanmaydi."
        ) from exc

    if not saw_supported and not fragments and not standalone:
        if saw_insert:
            raise DxfAnalysisError(
                "DXF faylda profil konturi topilmadi. Blok (INSERT) ichidagi "
                "chiziqlar hisobga olinmaydi — kontur modelspace da bo'lishi kerak."
            )
        raise DxfAnalysisError(
            "DXF faylda profil konturi topilmadi. Modelspace da LWPOLYLINE, "
            "POLYLINE, LINE, ARC, CIRCLE, SPLINE yoki ELLIPSE bo'lishi kerak."
        )
    if not fragments and not standalone:
        raise DxfAnalysisError(
            "Geometriya uzunligi nolga teng. Profil perimetri hisoblanmadi."
        )

    tol = y_tolerance_mm(_bbox_height([seg for frag in fragments for seg in frag.segments]))
    chained = _chain_fragments(fragments, tol)

    raw: list[tuple[list[DrawSegment], bool, str, str | None]] = [
        (segments, closed, source, None) for segments, closed, source in standalone
    ]
    raw.extend(chained)

    contours: list[ContourGeometry] = []
    for segments, closed, source, extra_warning in raw:
        contour = _finish_contour(len(contours) + 1, segments, closed, source, extra_warning)
        contours.append(contour)

    warnings: list[str] = []
    for contour in contours:
        if contour.warning:
            warnings.append(f"Kontur {contour.index}: {contour.warning}")

    return PartGeometry(
        contours=contours,
        p_jami_mm=sum(c.p_jami_mm for c in contours),
        l_pastki_mm=sum(c.l_pastki_mm for c in contours),
        p_faol_mm=sum(c.p_faol_mm for c in contours),
        unit_note=unit_note,
        insunits=insunits,
        warnings=warnings,
    )


def _read_document(data: bytes):
    """ASCII va binary DXF ni baytdan o'qiydi. Tarmoq chaqiruvi yo'q."""
    if data.startswith(b"AutoCAD Binary DXF"):
        with tempfile.NamedTemporaryFile(suffix=".dxf") as handle:
            handle.write(data)
            handle.flush()
            return ezdxf.readfile(handle.name)
    text = data.decode("utf-8", errors="surrogateescape")
    return ezdxf.read(io.StringIO(text))


def _segments_from_entity(entity: object, scale: float) -> list[DrawSegment]:
    path = make_path(entity)
    if scale != 1.0:
        path = path.transform(Matrix44.scale(scale, scale, scale))
    return _segments_from_path(path)


def _segments_from_path(path: Path) -> list[DrawSegment]:
    segments: list[DrawSegment] = []
    current = Vec3(path.start)
    for command in path:
        if isinstance(command, MoveTo):
            current = Vec3(command.end)
            continue
        if isinstance(command, LineTo):
            end = Vec3(command.end)
            points = [_xy(current), _xy(end)]
            segments.append(
                DrawSegment(kind="line", points=points, length_mm=_polyline_length(points))
            )
            current = end
            continue
        points_vec = _flatten_curve(current, command)
        points = [_xy(point) for point in points_vec]
        if len(points) < 2:
            points = [_xy(current), _xy(command.end)]
        segments.append(
            DrawSegment(kind="curve", points=points, length_mm=_polyline_length(points))
        )
        current = Vec3(command.end)
    return [segment for segment in segments if segment.length_mm > 1e-9 or len(segment.points) >= 2]


def _flatten_curve(start: Vec3, command: Curve3To | Curve4To) -> list[Vec3]:
    mini = Path(start)
    if isinstance(command, Curve4To):
        mini.curve4_to(command.end, command.ctrl1, command.ctrl2)
    elif isinstance(command, Curve3To):
        mini.curve3_to(command.end, command.ctrl)
    else:
        return [start, Vec3(command.end)]
    points = list(mini.flattening(_CURVE_SAGITTA_MM, segments=8))
    if len(points) < 2:
        return [start, Vec3(command.end)]
    return points


def _entity_is_closed(entity: object) -> bool:
    kind = entity.dxftype()
    if kind == "LWPOLYLINE":
        return bool(entity.closed)
    if kind == "POLYLINE":
        return bool(entity.is_closed)
    if kind == "CIRCLE":
        return True
    if kind == "ELLIPSE":
        span = abs(float(entity.dxf.end_param) - float(entity.dxf.start_param))
        return span >= (math.tau - 1e-4)
    if kind == "SPLINE":
        return bool(entity.closed)
    return False


def _finish_contour(
    index: int,
    segments: list[DrawSegment],
    closed: bool,
    source: str,
    extra_warning: str | None,
) -> ContourGeometry:
    p_jami = sum(segment.length_mm for segment in segments)
    warning = extra_warning
    l_pastki = 0.0
    if closed:
        l_pastki, bottom_warning = _subtract_bottom(segments)
        if bottom_warning and not warning:
            warning = bottom_warning
    else:
        for segment in segments:
            segment.coated = True
    p_faol = p_jami - l_pastki
    if p_faol < 0:
        p_faol = 0.0
    return ContourGeometry(
        index=index,
        closed=closed,
        source=source,
        p_jami_mm=p_jami,
        l_pastki_mm=l_pastki,
        p_faol_mm=p_faol,
        warning=warning,
        segments=segments,
    )


def _subtract_bottom(segments: Sequence[DrawSegment]) -> tuple[float, str | None]:
    """Yopiq konturdan faqat Y_min dagi gorizontal to'g'ri kesmalarni ayiradi.

    Yoy (curve) hech qachon pastki devor yuzi emas — uning uchi Y_min da
    bo'lsa ham ayirilmaydi. Ikkala uchi ham Y_min da va dy ≈ 0 bo'lmagan
    to'g'ri kesma ham ayirilmaydi. Shunday kesma umuman topilmasa
    L_pastki = 0 va ogohlantirish qaytadi; qiya qirra taxmin qilinmaydi.
    """
    ys = [y for segment in segments for _x, y in segment.points]
    if not ys:
        return 0.0, WARNING_NO_BOTTOM
    y_min = min(ys)
    height = max(ys) - y_min
    tol = y_tolerance_mm(height)
    l_pastki = 0.0
    for segment in segments:
        if _is_bottom_line(segment, y_min, tol):
            segment.coated = False
            l_pastki += segment.length_mm
        else:
            segment.coated = True
    if l_pastki <= 1e-9:
        return 0.0, WARNING_NO_BOTTOM
    return l_pastki, None


def _is_bottom_line(segment: DrawSegment, y_min: float, tol: float) -> bool:
    if segment.kind != "line" or len(segment.points) < 2:
        return False
    y0 = segment.points[0][1]
    y1 = segment.points[-1][1]
    # Ikkala uchi ham eng past gorizontalda va kesma o'zi gorizontal (dy ≈ 0).
    return (
        abs(y0 - y_min) <= tol
        and abs(y1 - y_min) <= tol
        and abs(y1 - y0) <= tol
    )


def _chain_fragments(
    fragments: Sequence[_Fragment], tol: float
) -> list[tuple[list[DrawSegment], bool, str, str | None]]:
    """Uchi-uchiga tegib turgan LINE/ARC larni bitta konturga ulaydi.

    Oddiy zanjir yoki halqa bo'lsa, yopiq halqada pastki qirra qidiriladi.
    Shoxlangan tutashuvda kontur taxmin qilinmaydi: har bir primitiv ochiq
    qoladi va ogohlantirish yoziladi.
    """
    if not fragments:
        return []
    n = len(fragments)
    parent = list(range(n))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    # (frag_a, end_a_is_start, frag_b, end_b_is_start)
    connections: list[tuple[int, bool, int, bool]] = []
    ends: list[tuple[int, bool, tuple[float, float]]] = []
    for index, frag in enumerate(fragments):
        ends.append((index, True, frag.start))
        ends.append((index, False, frag.end))
    for left in range(len(ends)):
        ia, sa, pa = ends[left]
        for right in range(left + 1, len(ends)):
            ib, sb, pb = ends[right]
            if ia == ib:
                continue
            if _dist(pa, pb) <= tol:
                union(ia, ib)
                connections.append((ia, sa, ib, sb))

    groups: dict[int, list[int]] = {}
    for index in range(n):
        groups.setdefault(find(index), []).append(index)

    ordered_groups: list[tuple[list[DrawSegment], bool, str, str | None]] = []
    for indexes in groups.values():
        if len(indexes) == 1:
            frag = fragments[indexes[0]]
            ordered_groups.append((list(frag.segments), False, frag.entity_type, None))
            continue
        ordered = _order_component(fragments, indexes, connections, tol)
        if ordered is None:
            for index in indexes:
                frag = fragments[index]
                ordered_groups.append((list(frag.segments), False, frag.entity_type, WARNING_BRANCH))
            continue
        segments, closed, source = ordered
        ordered_groups.append((segments, closed, source, None))
    return ordered_groups


def _order_component(
    fragments: Sequence[_Fragment],
    indexes: Sequence[int],
    connections: Sequence[tuple[int, bool, int, bool]],
    tol: float,
) -> tuple[list[DrawSegment], bool, str] | None:
    index_set = set(indexes)
    adjacency: dict[int, list[tuple[int, bool, bool]]] = {i: [] for i in indexes}
    for ia, sa, ib, sb in connections:
        if ia in index_set and ib in index_set:
            adjacency[ia].append((ib, sb, sa))
            adjacency[ib].append((ia, sa, sb))

    for links in adjacency.values():
        if len(links) > 2:
            return None
        used_ends = [my_end for _neighbor, _n_end, my_end in links]
        if len(used_ends) != len(set(used_ends)):
            return None

    start = next((i for i in indexes if len(adjacency[i]) <= 1), None)
    closed_shape = start is None
    if start is None:
        start = indexes[0]
        reversed_flag = False
    elif len(adjacency[start]) == 1:
        _neighbor, _n_end, my_end = adjacency[start][0]
        # Ulanish start tomonda bo'lsa, erkin uch — oxir. Zanjir erkin uchdan yuradi.
        reversed_flag = bool(my_end)
    else:
        reversed_flag = False

    ordered: list[tuple[int, bool]] = []
    used: set[int] = set()
    current: int | None = start
    prev: int | None = None
    while current is not None and current not in used:
        used.add(current)
        ordered.append((current, reversed_flag))
        exit_is_start = reversed_flag
        nxt: int | None = None
        nxt_reversed = False
        for neighbor, neighbor_end_is_start, my_end_is_start in adjacency[current]:
            if neighbor == prev or neighbor in used:
                continue
            if my_end_is_start != exit_is_start:
                continue
            nxt = neighbor
            nxt_reversed = not neighbor_end_is_start
            break
        prev = current
        current = nxt
        reversed_flag = nxt_reversed

    if len(used) != len(indexes):
        return None

    segments: list[DrawSegment] = []
    types: list[str] = []
    for index, reversed_seg in ordered:
        frag = fragments[index]
        types.append(frag.entity_type)
        piece = _reverse_segments(frag.segments) if reversed_seg else frag.segments
        segments.extend(_copy_segments(piece))
    if not segments:
        return None
    start_pt = segments[0].points[0]
    end_pt = segments[-1].points[-1]
    closed = closed_shape and _dist(start_pt, end_pt) <= tol
    source = "+".join(dict.fromkeys(types))
    return segments, closed, source


def _copy_segments(segments: Iterable[DrawSegment]) -> list[DrawSegment]:
    return [
        DrawSegment(
            kind=segment.kind,
            points=list(segment.points),
            length_mm=segment.length_mm,
            coated=segment.coated,
        )
        for segment in segments
    ]


def _reverse_segments(segments: Sequence[DrawSegment]) -> list[DrawSegment]:
    reversed_segments: list[DrawSegment] = []
    for segment in reversed(segments):
        reversed_segments.append(
            DrawSegment(
                kind=segment.kind,
                points=list(reversed(segment.points)),
                length_mm=segment.length_mm,
                coated=segment.coated,
            )
        )
    return reversed_segments


def _bbox_height(segments: Sequence[DrawSegment]) -> float:
    ys = [y for segment in segments for _x, y in segment.points]
    if not ys:
        return 0.0
    return max(ys) - min(ys)


def _polyline_length(points: Sequence[tuple[float, float]]) -> float:
    total = 0.0
    for start, end in zip(points, points[1:]):
        total += _dist(start, end)
    return total


def _dist(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _xy(point: Vec3) -> tuple[float, float]:
    return (float(point.x), float(point.y))
