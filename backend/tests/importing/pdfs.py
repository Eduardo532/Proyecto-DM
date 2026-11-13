"""PDF sintéticos para las pruebas del importador (sin material con derechos de autor).

Se generan con PyMuPDF; si no está instalado (entorno de desarrollo), con reportlab.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

PAGE_W, PAGE_H = 612.0, 792.0


@dataclass
class Text:
    x: float
    y: float  # desde arriba, línea base
    text: str
    size: float = 10
    bold: bool = False
    italic: bool = False
    page: int = 0


@dataclass
class FormField:
    name: str
    value: str
    rect: tuple[float, float, float, float]  # x0, y0, x1, y1 desde arriba
    page: int = 0


@dataclass
class PdfSpec:
    texts: list[Text] = field(default_factory=list)
    fields: list[FormField] = field(default_factory=list)
    pages: int = 1
    image: Path | None = None  # imagen a página completa en la primera página


def write_pdf(path: Path, spec: PdfSpec) -> Path:
    try:
        import pymupdf
    except ImportError:  # pragma: no cover - solo en desarrollo
        return _write_reportlab(path, spec)
    doc = pymupdf.open()
    for _ in range(spec.pages):
        doc.new_page(width=PAGE_W, height=PAGE_H)
    if spec.image is not None:
        doc[0].insert_image(doc[0].rect, filename=str(spec.image))
    for item in spec.texts:
        font = "hebo" if item.bold else "heit" if item.italic else "helv"
        doc[item.page].insert_text((item.x, item.y), item.text, fontsize=item.size, fontname=font)
    for form in spec.fields:
        widget = pymupdf.Widget()
        widget.field_type = pymupdf.PDF_WIDGET_TYPE_TEXT
        widget.field_name = form.name
        widget.field_value = form.value
        widget.rect = pymupdf.Rect(*form.rect)
        page = doc[form.page]
        page.add_widget(widget)
    doc.save(path)
    doc.close()
    return path


def _write_reportlab(path: Path, spec: PdfSpec) -> Path:  # pragma: no cover
    from reportlab.pdfgen import canvas

    pdf = canvas.Canvas(str(path), pagesize=(PAGE_W, PAGE_H))
    for page in range(spec.pages):
        if page == 0 and spec.image is not None:
            pdf.drawImage(str(spec.image), 0, 0, PAGE_W, PAGE_H)
        for item in (t for t in spec.texts if t.page == page):
            font = "Helvetica-Bold" if item.bold else "Helvetica-Oblique" if item.italic else "Helvetica"
            pdf.setFont(font, item.size)
            pdf.drawString(item.x, PAGE_H - item.y, item.text)
        for form in (f for f in spec.fields if f.page == page):
            x0, y0, x1, y1 = form.rect
            value = form.value.replace("\u2022", "-").encode("latin-1", "replace").decode("latin-1")
            pdf.acroForm.textfield(name=form.name, value=value, x=x0, y=PAGE_H - y1, width=x1 - x0,
                                   height=y1 - y0, borderWidth=0, fontSize=8)
        pdf.showPage()
    pdf.save()
    return path


# ------------------------------------------------------------------ fichas ---
def ddb_sheet(path: Path) -> Path:
    """Exportación tipo D&D Beyond: todo va en campos de formulario."""
    values = {
        "CharacterName": "Kira Vientoalto", "CLASS  LEVEL": "Rogue 3", "RACE": "Lightfoot Halfling",
        "BACKGROUND": "Urchin", "ALIGNMENT": "Chaotic Good", "PLAYER NAME": "Ana",
        "STR": "8", "STRmod": "-1", "DEX": "17", "DEXmod": "+3", "CON": "14", "CONmod": "+2",
        "INT": "12", "INTmod": "+1", "WIS": "13", "WISmod": "+1", "CHA": "10", "CHamod": "+0",
        "ProfBonus": "+2", "MaxHP": "20", "CurrentHP": "20", "AC": "15", "Speed": "25 ft. (Walking)",
        "Total": "3d8", "AdditionalSenses": "Darkvision 60 ft.", "Defenses": "Poison",
        "ST Dexterity": "+5", "ST Intelligence": "+3", "DexProf": "P", "IntProf": "P",
        "Stealth": "+7", "StealthProf": "E", "Acrobatics": "+5", "AcrobaticsProf": "P",
        "Perception": "+3", "PerceptionProf": "P", "Athletics": "-1",
        "Wpn Name": "Shortsword", "Wpn1 AtkBonus": "+5", "Wpn1 Damage": "1d6+3 Piercing",
        "Wpn Name 2": "Shortbow", "Wpn2 AtkBonus": "+5", "Wpn2 Damage": "1d6+3 Piercing",
        "FeaturesTraits1": "* Sneak Attack • PHB\nOnce per turn, extra 2d6 damage.\n\n* Cunning Action • PHB\nDash, Disengage or Hide as a bonus action.",
        "ProficienciesLang": "=== LANGUAGES ===\nCommon, Halfling",
    }
    fields = [FormField(name, value, (40, 40 + 16 * i % 700, 300, 54 + 16 * i % 700), page=(16 * i) // 700)
              for i, (name, value) in enumerate(values.items())]
    return write_pdf(path, PdfSpec(fields=fields, pages=2))


def spanish_text_sheet(path: Path) -> Path:
    """Hoja impresa «plana» en español: etiquetas con su valor al lado."""
    texts = [
        Text(40, 40, "HOJA DE PERSONAJE", 16, bold=True),
        Text(40, 70, "Nombre del personaje: Lía Brasa"),
        Text(320, 70, "Clase y nivel: Mago 2"),
        Text(40, 88, "Raza: Elfa"),
        Text(320, 88, "Trasfondo: Sabia"),
        Text(40, 106, "Velocidad: 30 pies"),
        Text(320, 106, "Idiomas: Común, Élfico, Dracónico"),
    ]
    abilities = [("FUERZA", 8, "-1"), ("DESTREZA", 14, "+2"), ("CONSTITUCIÓN", 13, "+1"),
                 ("INTELIGENCIA", 16, "+3"), ("SABIDURÍA", 12, "+1"), ("CARISMA", 10, "+0")]
    for i, (label, score, mod) in enumerate(abilities):
        y = 150 + i * 50
        texts += [Text(40, y, label, 9, bold=True), Text(48, y + 20, str(score), 14), Text(80, y + 20, mod, 9)]
    texts += [
        Text(320, 150, "Puntos de golpe máximos: 14"),
        Text(320, 168, "Clase de armadura: 12"),
        Text(320, 186, "Bonificador por competencia: +2"),
        Text(320, 204, "Dados de golpe: 2d6"),
        Text(320, 240, "Arcanos +5"),
        Text(320, 258, "Historia +5"),
        Text(320, 276, "Percepción +1"),
        Text(320, 312, "Visión en la oscuridad 60 pies."),
    ]
    return write_pdf(path, PdfSpec(texts=texts))
