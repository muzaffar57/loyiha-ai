"""Penoplast profili uchun loy sarfi. Ishga tushirish: streamlit run app.py"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pandas as pd
import streamlit as st

from src.formulas import ThicknessError, calculate_mass
from src.geometry import DxfAnalysisError, PartGeometry, analyze_dxf
from src.preview import render_preview_png
from src.reports import ReportRow, build_excel, build_pdf

THICKNESS_OPTIONS = (3.0, 3.5, 4.0)


def main() -> None:
    st.set_page_config(page_title="Penoplast loy sarfi", layout="wide")
    st.title("Penoplast profili — loy sarfi")
    st.markdown(
        "Qoplama **faqat uchta yuzga** surtiladi: tepa va ikki yon. "
        "Devorga yopishadigan pastki tekis yuz **qoplanmaydi**. "
        "Yopiq konturda shu pastki gorizontal chiziq perimetrdan ayiriladi. "
        "Ochiq chiziqda chizuvchi faqat qoplanadigan yo'lni chizgan deb olinadi."
    )

    with st.sidebar:
        st.header("Sozlamalar")
        d_global = st.radio(
            "Qoplama qalinligi d",
            options=list(THICKNESS_OPTIONS),
            format_func=lambda value: f"{value:.1f} mm",
            horizontal=True,
        )
        st.markdown(
            "Doimiy qiymatlar (o'zgarmaydi):\n\n"
            "- Zichlik ρ = **1.95 kg/l**\n"
            "- Detal uzunligi L = **2 m**\n"
            "- Texnik chiqindi = **5%** (× 1.05)"
        )
        st.caption(
            "M_1 = (P_faol × d × 2 / 1000) × 1.95\n\n"
            "M_jami = M_1 × N × 1.05"
        )

    uploads = st.file_uploader(
        "DXF fayllarni yuklang",
        type=["dxf"],
        accept_multiple_files=True,
        help="Har bir fayl bitta detal. Fayl ichidagi konturlar yig'ilib, shu detalning perimetri chiqadi.",
    )
    if not uploads:
        st.info("Hisoblash uchun kamida bitta DXF fayl yuklang. Har bir detal uchun dona sonini kiriting.")
        return

    rows: list[ReportRow] = []
    errors = 0
    for index, uploaded in enumerate(uploads):
        name = Path(uploaded.name).stem or f"detal-{index + 1}"
        key = f"{index}-{uploaded.name}"
        st.divider()
        st.subheader(name)
        left, right = st.columns(2)
        with left:
            n = int(
                st.number_input(
                    "Dona soni N",
                    min_value=1,
                    max_value=1_000_000,
                    value=1,
                    step=1,
                    key=f"n-{key}",
                )
            )
        with right:
            override = st.selectbox(
                "Qalinlik d",
                options=["global", *THICKNESS_OPTIONS],
                format_func=lambda value: (
                    f"Umumiy sozlama ({d_global:.1f} mm)" if value == "global" else f"{value:.1f} mm"
                ),
                key=f"d-{key}",
            )
        d_mm = float(d_global if override == "global" else override)
        try:
            part = analyze_dxf(uploaded.getvalue())
            mass = calculate_mass(part.p_faol_mm, d_mm, n)
        except (DxfAnalysisError, ThicknessError) as exc:
            errors += 1
            st.error(str(exc))
            continue
        except Exception:
            errors += 1
            st.error("DXF faylni tahlil qilib bo'lmadi. Faylni tekshiring.")
            continue

        row = ReportRow(
            name=name,
            contour_type=part.contour_type,
            p_jami_mm=part.p_jami_mm,
            l_pastki_mm=part.l_pastki_mm,
            p_faol_mm=part.p_faol_mm,
            d_mm=mass.d_mm,
            n=mass.n,
            m_1_kg=mass.m_1_kg,
            waste_kg=mass.waste_kg,
            m_jami_kg=mass.m_jami_kg,
            formula=mass.formula,
            unit_note=part.unit_note,
            warnings=tuple(part.warnings),
            m_without_waste_kg=mass.m_without_waste_kg,
        )
        rows.append(row)
        _show_part(part, row)

    st.divider()
    if errors and not rows:
        st.error("Hisoblanadigan detal yo'q. DXF fayllarni tekshiring.")
        return
    if errors:
        st.warning(f"{errors} ta faylda xato bor. Ular jami hisobga kirmaydi.")
    if not rows:
        return

    st.header("Partiya jami")
    total_base = sum(row.m_without_waste_kg for row in rows)
    total_jami = sum(row.m_jami_kg for row in rows)
    c1, c2, c3 = st.columns(3)
    c1.metric("Detallar", len(rows))
    c2.metric("M_1 × N, kg", f"{total_base:.3f}")
    c3.metric("M_jami (+5%), kg", f"{total_jami:.3f}")
    st.code(
        "Partiya:\n"
        f"M_1 * N yig'indisi = {total_base:.3f} kg\n"
        f"+5% chiqindi: M_jami = {total_base:.3f} * 1.05 = {total_jami:.3f} kg",
        language=None,
    )
    summary = pd.DataFrame(
        [
            {
                "Detal nomi": row.name,
                "Kontur turi": row.contour_type,
                "P_jami (mm)": row.p_jami_mm,
                "L_pastki (mm)": row.l_pastki_mm,
                "P_faol (mm)": row.p_faol_mm,
                "d (mm)": row.d_mm,
                "N": row.n,
                "M_1 (kg)": row.m_1_kg,
                "M_1 × N (kg)": row.m_without_waste_kg,
                "Chiqindi 5% (kg)": row.waste_kg,
                "M_jami (kg)": row.m_jami_kg,
            }
            for row in rows
        ]
    )
    st.dataframe(summary, hide_index=True, use_container_width=True)

    try:
        excel = build_excel(rows)
        pdf = build_pdf(rows)
    except Exception:
        st.error("Hisobot faylini yaratib bo'lmadi.")
        return
    d1, d2 = st.columns(2)
    with d1:
        st.download_button(
            "Excel (.xlsx) yuklab olish",
            data=excel,
            file_name="loy-sarfi.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    with d2:
        st.download_button(
            "PDF yuklab olish",
            data=pdf,
            file_name="loy-sarfi.pdf",
            mime="application/pdf",
        )


def _show_part(part: PartGeometry, row: ReportRow) -> None:
    st.caption(part.unit_note)
    for warning in part.warnings:
        st.warning(warning)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("P_jami, mm", f"{row.p_jami_mm:.3f}")
    m2.metric("L_pastki, mm", f"{row.l_pastki_mm:.3f}")
    m3.metric("P_faol, mm", f"{row.p_faol_mm:.3f}")
    m4.metric("M_jami, kg", f"{row.m_jami_kg:.3f}")
    st.markdown(
        f"Kontur: **{row.contour_type}**. "
        f"Qalinlik d = **{row.d_mm:.1f} mm**, dona N = **{row.n}**. "
        f"1 dona uchun M_1 = **{row.m_1_kg:.3f} kg**. "
        f"M_1 × N = **{row.m_without_waste_kg:.3f} kg**, "
        f"ustiga 5% chiqindi → M_jami = **{row.m_jami_kg:.3f} kg**."
    )
    breakdown = pd.DataFrame(
        [
            {
                "#": contour.index,
                "Manba": contour.source,
                "Holat": contour.state_label,
                "P_jami (mm)": contour.p_jami_mm,
                "L_pastki (mm)": contour.l_pastki_mm,
                "P_faol (mm)": contour.p_faol_mm,
                "Izoh": contour.warning or "",
            }
            for contour in part.contours
        ]
    )
    st.markdown("**Konturlar bo'yicha**")
    st.dataframe(breakdown, hide_index=True, use_container_width=True)
    st.markdown("**Formula**")
    st.code(row.formula, language=None)
    st.caption("2 — detal uzunligi (metr). 1.95 — zichlik (kg/l). 1.05 — 5% texnik chiqindi.")
    try:
        png = render_preview_png(part)
    except Exception:
        st.warning("Kesim eskizini chizib bo'lmadi. Raqamlar shu holicha ishonchli.")
        return
    st.image(png, use_container_width=True)
    st.caption("Yashil — qoplanadigan qirra. Qizil uzuk chiziq — devorga yopishadigan pastki qirra.")


main()
