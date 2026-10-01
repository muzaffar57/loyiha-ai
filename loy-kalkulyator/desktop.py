"""Penoplast profili uchun loy sarfi — desktop oyna.

Ishga tushirish (shu papkadan): python desktop.py
Brauzer va veb-server yo'q. Hisoblash moduli src/ da, o'zgarmagan.
"""

from __future__ import annotations

import base64
import sys
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.formulas import ThicknessError, calculate_mass
from src.geometry import DxfAnalysisError, PartGeometry, analyze_dxf
from src.preview import render_preview_png
from src.reports import ReportRow, build_excel, build_pdf

THICKNESS_OPTIONS: tuple[str, ...] = ("3.0", "3.5", "4.0")

_INTRO = (
    "Qoplama faqat uchta yuzga surtiladi: tepa va ikki yon. "
    "Devorga yopishadigan pastki tekis yuz qoplanmaydi. "
    "Yopiq konturda shu pastki gorizontal chiziq perimetrdan ayiriladi. "
    "Ochiq chiziqda chizuvchi faqat qoplanadigan yo'lni chizgan deb olinadi."
)
_CONSTANTS = (
    "Doimiy qiymatlar: zichlik ρ = 1.95 kg/l, detal uzunligi L = 2 m, "
    "texnik chiqindi = 5% (× 1.05)."
)
_EMPTY = "Hisoblash uchun kamida bitta DXF fayl tanlang. Har bir detal uchun dona sonini kiriting."
_PREVIEW_CAPTION = "Yashil — qoplanadigan qirra. Qizil uzuk chiziq — devorga yopishadigan pastki qirra."


@dataclass
class LoadedPart:
    name: str
    path: Path
    geometry: PartGeometry | None
    error: str | None


def load_dxf(path: Path) -> LoadedPart:
    """DXF faylni o'qiydi. Xato bo'lsa o'zbekcha matn qaytadi, istisno tashlamaydi."""
    name = path.stem or path.name
    try:
        geometry = analyze_dxf(path.read_bytes())
    except DxfAnalysisError as exc:
        return LoadedPart(name=name, path=path, geometry=None, error=exc.message)
    except Exception:
        return LoadedPart(
            name=name,
            path=path,
            geometry=None,
            error="DXF faylni tahlil qilib bo'lmadi. Faylni tekshiring.",
        )
    return LoadedPart(name=name, path=path, geometry=geometry, error=None)


def parse_quantity(raw: str) -> int | None:
    """Musbat butun N. Bo'sh yoki kasr bo'lsa None."""
    text = raw.strip().replace(",", ".")
    if not text:
        return None
    try:
        value = float(text)
    except ValueError:
        return None
    if value < 1 or not value.is_integer():
        return None
    return int(value)


def make_report_row(loaded: LoadedPart, d_mm: float, n: int) -> ReportRow:
    """Geometriya va massa formulasidan hisobot qatori yig'adi."""
    if loaded.geometry is None:
        raise ValueError(loaded.error or "Detal hisoblanmadi.")
    mass = calculate_mass(loaded.geometry.p_faol_mm, d_mm, n)
    return ReportRow(
        name=loaded.name,
        contour_type=loaded.geometry.contour_type,
        p_jami_mm=loaded.geometry.p_jami_mm,
        l_pastki_mm=loaded.geometry.l_pastki_mm,
        p_faol_mm=loaded.geometry.p_faol_mm,
        d_mm=mass.d_mm,
        n=mass.n,
        m_1_kg=mass.m_1_kg,
        waste_kg=mass.waste_kg,
        m_jami_kg=mass.m_jami_kg,
        formula=mass.formula,
        unit_note=loaded.geometry.unit_note,
        warnings=tuple(loaded.geometry.warnings),
        m_without_waste_kg=mass.m_without_waste_kg,
    )


def part_summary_text(loaded: LoadedPart, row: ReportRow) -> str:
    """Oynada ko'rinadigan shaffof hisob matni."""
    assert loaded.geometry is not None
    lines = [loaded.geometry.unit_note]
    if loaded.geometry.warnings:
        lines.append("Ogohlantirish: " + " | ".join(loaded.geometry.warnings))
    lines.extend(
        [
            f"Kontur turi: {row.contour_type}",
            f"Umumiy perimetr P_jami: {row.p_jami_mm:.3f} mm",
            f"Pastki chiziq L_pastki: {row.l_pastki_mm:.3f} mm",
            f"Qoplanadigan faol perimetr P_faol: {row.p_faol_mm:.3f} mm",
            f"Qalinlik d: {row.d_mm:.1f} mm",
            f"Dona soni N: {row.n}",
            f"1 dona uchun loy M_1: {row.m_1_kg:.3f} kg",
            f"M_1 × N: {row.m_without_waste_kg:.3f} kg",
            f"+5% chiqindi: {row.waste_kg:.3f} kg",
            f"Jami loy M_jami: {row.m_jami_kg:.3f} kg",
            "",
            "Formula:",
            row.formula,
            "",
            "2 — detal uzunligi (metr). 1.95 — zichlik (kg/l). 1.05 — 5% texnik chiqindi.",
        ]
    )
    return "\n".join(lines)


def batch_summary_text(rows: list[ReportRow], error_count: int) -> str:
    if not rows and error_count:
        return "Hisoblanadigan detal yo'q. DXF fayllarni tekshiring."
    if not rows:
        return "Partiya jami: hali detal yo'q."
    base = sum(row.m_without_waste_kg for row in rows)
    jami = sum(row.m_jami_kg for row in rows)
    note = ""
    if error_count:
        note = f" {error_count} ta faylda xato bor. Ular jami hisobga kirmaydi."
    return (
        f"Partiya jami: {len(rows)} ta detal. "
        f"M_1 × N = {base:.3f} kg. "
        f"+5% chiqindi: M_jami = {base:.3f} × 1.05 = {jami:.3f} kg."
        + note
    )


class LoyApp(tk.Tk):
    """Desktop oyna. mainloop chaqirilmaguncha o'zi ko'rinmay turishi mumkin."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Penoplast profili — loy sarfi")
        self.geometry("980x740")
        self.minsize(760, 520)
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")

        self.d_var = tk.StringVar(value="3.0")
        self.cards: list[PartCard] = []

        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        header = ttk.Frame(self, padding=(12, 10, 12, 4))
        header.grid(row=0, column=0, sticky="ew")
        ttk.Label(header, text="Penoplast profili — loy sarfi", font=("TkDefaultFont", 16, "bold")).pack(anchor="w")
        intro = ttk.Label(header, text=_INTRO, wraplength=920, justify="left")
        intro.pack(anchor="w", pady=(6, 2))
        ttk.Label(header, text=_CONSTANTS, wraplength=920, justify="left").pack(anchor="w")

        controls = ttk.Frame(self, padding=(12, 4, 12, 4))
        controls.grid(row=1, column=0, sticky="ew")
        ttk.Button(controls, text="DXF fayl tanlash", command=self.choose_files).pack(side="left")
        ttk.Button(controls, text="Ro'yxatni tozalash", command=self.clear_parts).pack(side="left", padx=(8, 16))
        ttk.Label(controls, text="Qalinlik d:").pack(side="left")
        for value in THICKNESS_OPTIONS:
            ttk.Radiobutton(
                controls,
                text=f"{value} mm",
                value=value,
                variable=self.d_var,
                command=self.refresh_all,
            ).pack(side="left", padx=(6, 0))
        ttk.Button(controls, text="Excel saqlash", command=self.save_excel).pack(side="right")
        ttk.Button(controls, text="PDF saqlash", command=self.save_pdf).pack(side="right", padx=(0, 8))

        self.scroller = ScrolledFrame(self)
        self.scroller.grid(row=2, column=0, sticky="nsew", padx=8, pady=4)
        self.empty_label = ttk.Label(self.scroller.inner, text=_EMPTY, wraplength=860, justify="left")
        self.empty_label.pack(anchor="w", padx=8, pady=12)

        self.batch_label = ttk.Label(self, text=batch_summary_text([], 0), padding=(12, 8), wraplength=940, justify="left")
        self.batch_label.grid(row=3, column=0, sticky="ew")

    def thickness(self) -> float:
        return float(self.d_var.get())

    def choose_files(self) -> None:
        selected = filedialog.askopenfilenames(
            title="DXF fayllarni tanlang",
            filetypes=[("DXF chizma", "*.dxf"), ("Barcha fayllar", "*.*")],
        )
        if selected:
            self.add_paths(list(selected))

    def add_paths(self, paths: list[str | Path]) -> None:
        for raw in paths:
            loaded = load_dxf(Path(raw))
            card = PartCard(self.scroller.inner, loaded, self)
            card.pack(fill="x", padx=8, pady=6)
            self.cards.append(card)
        self._sync_empty()
        self.update_batch()

    def clear_parts(self) -> None:
        for card in self.cards:
            card.destroy()
        self.cards.clear()
        self._sync_empty()
        self.update_batch()

    def refresh_all(self) -> None:
        for card in self.cards:
            card.refresh()
        self.update_batch()

    def report_rows(self) -> list[ReportRow]:
        rows: list[ReportRow] = []
        for card in self.cards:
            row = card.report_row()
            if row is not None:
                rows.append(row)
        return rows

    def update_batch(self) -> None:
        failed = sum(1 for card in self.cards if card.loaded.error)
        invalid = sum(1 for card in self.cards if card.loaded.geometry is not None and card.report_row() is None)
        self.batch_label.configure(text=batch_summary_text(self.report_rows(), failed + invalid))

    def _sync_empty(self) -> None:
        if self.cards:
            self.empty_label.pack_forget()
        elif not self.empty_label.winfo_manager():
            self.empty_label.pack(anchor="w", padx=8, pady=12)

    def save_excel(self) -> None:
        self._save("Excel saqlash", "loy-sarfi.xlsx", ".xlsx", [("Excel", "*.xlsx")], build_excel)

    def save_pdf(self) -> None:
        self._save("PDF saqlash", "loy-sarfi.pdf", ".pdf", [("PDF", "*.pdf")], build_pdf)

    def _save(self, title: str, initial: str, extension: str, filetypes: list[tuple[str, str]], builder) -> None:
        rows = self.report_rows()
        if not rows:
            messagebox.showwarning("Loy sarfi", "Saqlash uchun hisoblangan detal yo'q.")
            return
        path = filedialog.asksaveasfilename(
            title=title,
            defaultextension=extension,
            initialfile=initial,
            filetypes=filetypes,
        )
        if not path:
            return
        try:
            Path(path).write_bytes(builder(rows))
        except Exception:
            messagebox.showerror("Loy sarfi", "Faylni saqlab bo'lmadi.")
            return
        messagebox.showinfo("Loy sarfi", f"Saqlandi:\n{path}")


class PartCard(ttk.LabelFrame):
    def __init__(self, master: tk.Misc, loaded: LoadedPart, app: LoyApp) -> None:
        super().__init__(master, text=loaded.name, padding=8)
        self.loaded = loaded
        self.app = app
        self._photo: tk.PhotoImage | None = None
        self.n_var = tk.StringVar(value="1")

        if loaded.error:
            ttk.Label(self, text=loaded.error, foreground="#9B2C2C", wraplength=860, justify="left").pack(anchor="w")
            return

        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Label(top, text="Dona soni N:").pack(side="left")
        spin = ttk.Spinbox(top, from_=1, to=1_000_000, textvariable=self.n_var, width=8, command=self._on_quantity)
        spin.pack(side="left", padx=(6, 0))

        self.body = tk.Text(self, height=14, wrap="word", relief="flat", font=("TkFixedFont", 10))
        self.body.pack(fill="x", pady=(8, 4))

        ttk.Label(self, text="Konturlar bo'yicha").pack(anchor="w")
        columns = ("manba", "holat", "pjami", "lpastki", "pfaol", "izoh")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=min(6, max(2, len(loaded.geometry.contours))))
        headings = {
            "manba": "Manba",
            "holat": "Holat",
            "pjami": "P_jami (mm)",
            "lpastki": "L_pastki (mm)",
            "pfaol": "P_faol (mm)",
            "izoh": "Izoh",
        }
        widths = {"manba": 120, "holat": 70, "pjami": 110, "lpastki": 120, "pfaol": 110, "izoh": 280}
        for key, title in headings.items():
            self.tree.heading(key, text=title)
            self.tree.column(key, width=widths[key], anchor="w")
        for contour in loaded.geometry.contours:
            self.tree.insert(
                "",
                "end",
                values=(
                    contour.source,
                    contour.state_label,
                    f"{contour.p_jami_mm:.3f}",
                    f"{contour.l_pastki_mm:.3f}",
                    f"{contour.p_faol_mm:.3f}",
                    contour.warning or "",
                ),
            )
        self.tree.pack(fill="x", pady=(2, 6))

        self.preview = ttk.Label(self)
        self.preview.pack(anchor="w")
        self._show_preview()
        ttk.Label(self, text=_PREVIEW_CAPTION, wraplength=860).pack(anchor="w", pady=(2, 0))
        self.n_var.trace_add("write", lambda *_name: self._on_quantity())
        self.refresh()

    def _on_quantity(self) -> None:
        self.refresh()
        self.app.update_batch()

    def report_row(self) -> ReportRow | None:
        if self.loaded.geometry is None:
            return None
        quantity = parse_quantity(self.n_var.get())
        if quantity is None:
            return None
        try:
            return make_report_row(self.loaded, self.app.thickness(), quantity)
        except (ThicknessError, ValueError):
            return None

    def refresh(self) -> None:
        if self.loaded.geometry is None:
            return
        row = self.report_row()
        if row is None:
            text = "Dona soni N kamida 1 bo'lgan butun son bo'lishi kerak."
        else:
            text = part_summary_text(self.loaded, row)
        self.body.configure(state="normal")
        self.body.delete("1.0", "end")
        self.body.insert("1.0", text)
        line_count = int(self.body.index("end-1c").split(".")[0])
        self.body.configure(height=min(max(line_count, 8), 24), state="disabled")

    def _show_preview(self) -> None:
        if self.loaded.geometry is None:
            return
        try:
            png = render_preview_png(self.loaded.geometry)
            image = tk.PhotoImage(data=base64.b64encode(png).decode("ascii"))
            while image.width() > 680 and image.width() > 2:
                image = image.subsample(2, 2)
            self._photo = image
            self.preview.configure(image=self._photo)
        except Exception:
            self.preview.configure(text="Kesim eskizini chizib bo'lmadi. Raqamlar shu holicha ishonchli.")


class ScrolledFrame(ttk.Frame):
    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master)
        self.canvas = tk.Canvas(self, highlightthickness=0)
        scroll = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas)
        self.inner.bind("<Configure>", self._on_inner_configure)
        self._window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=scroll.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind("<Enter>", self._bind_wheel)
        self.canvas.bind("<Leave>", self._unbind_wheel)

    def _on_inner_configure(self, _event: tk.Event) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event: tk.Event) -> None:
        self.canvas.itemconfigure(self._window, width=event.width)

    def _bind_wheel(self, _event: tk.Event) -> None:
        self.canvas.bind_all("<MouseWheel>", self._on_wheel)
        self.canvas.bind_all("<Button-4>", self._on_wheel)
        self.canvas.bind_all("<Button-5>", self._on_wheel)

    def _unbind_wheel(self, _event: tk.Event) -> None:
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")

    def _on_wheel(self, event: tk.Event) -> None:
        if getattr(event, "num", None) == 4:
            self.canvas.yview_scroll(-1, "units")
        elif getattr(event, "num", None) == 5:
            self.canvas.yview_scroll(1, "units")
        else:
            delta = int(getattr(event, "delta", 0))
            if delta:
                self.canvas.yview_scroll(int(-delta / 120) or (-1 if delta > 0 else 1), "units")


def main() -> None:
    app = LoyApp()
    app.mainloop()


if __name__ == "__main__":
    main()
