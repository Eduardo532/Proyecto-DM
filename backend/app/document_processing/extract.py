"""Extracción de bloques de texto, imágenes y tablas con PyMuPDF."""

from __future__ import annotations

import logging
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pymupdf

log = logging.getLogger("vdm.pdf")

ITALIC_FONT = re.compile(r"(italic|oblique|-it\b|it$)", re.IGNORECASE)
BOLD_FONT = re.compile(r"(bold|black|heavy|-bd\b|bd$)", re.IGNORECASE)


@dataclass
class Block:
    page: int
    text: str
    size: float
    bold: bool
    italic: bool
    boxed: bool
    bbox: tuple[float, float, float, float]


@dataclass
class ImageInfo:
    page: int
    path: Path
    width: int
    height: int
    page_coverage: float
    nearby_text: str


@dataclass
class Extraction:
    page_count: int
    blocks: list[Block] = field(default_factory=list)
    images: list[ImageInfo] = field(default_factory=list)
    tables: list[tuple[int, list[list[str]]]] = field(default_factory=list)
    body_size: float = 10.0
    ocr_pages: list[int] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _filled_rects(page: Any) -> list[Any]:
    rects = []
    try:
        for drawing in page.get_drawings():
            if drawing.get("fill") is not None and drawing.get("rect") is not None:
                rect = drawing["rect"]
                if rect.width > 100 and rect.height > 20:
                    rects.append(rect)
    except Exception:  # pragma: no cover - dibujos corruptos
        return []
    return rects


def _page_dict(page: Any, extraction: Extraction, index: int) -> dict[str, Any]:
    data: dict[str, Any] = page.get_text("dict", sort=True)
    chars = sum(len(s.get("text", "")) for b in data["blocks"] if b.get("type") == 0
                for line in b["lines"] for s in line["spans"])
    if chars < 30 and page.get_images():
        try:
            textpage = page.get_textpage_ocr(language="spa+eng", dpi=200, full=True)
            data = page.get_text("dict", sort=True, textpage=textpage)
            extraction.ocr_pages.append(index + 1)
        except Exception as exc:  # Tesseract no instalado
            extraction.warnings.append(f"Página {index + 1}: parece escaneada y no se pudo aplicar OCR ({exc}).")
    return data


def extract(path: Path, assets_dir: Path, min_image_px: int = 200) -> Extraction:
    assets_dir.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open(path)
    extraction = Extraction(page_count=doc.page_count)
    sizes: Counter[float] = Counter()
    seen_xrefs: set[int] = set()
    for index, page in enumerate(doc):
        boxes = _filled_rects(page)
        data = _page_dict(page, extraction, index)
        page_area = page.rect.width * page.rect.height or 1
        for block in data["blocks"]:
            if block.get("type") != 0:
                continue
            spans = [s for line in block["lines"] for s in line["spans"] if s.get("text", "").strip()]
            if not spans:
                continue
            text = "\n".join(
                "".join(s["text"] for s in line["spans"]).strip() for line in block["lines"]
            ).strip()
            if not text:
                continue
            main = max(spans, key=lambda s: len(s["text"]))
            size = round(float(main["size"]), 1)
            font = str(main.get("font", ""))
            flags = int(main.get("flags", 0))
            italic_chars = sum(len(s["text"]) for s in spans if (int(s.get("flags", 0)) & 2)
                               or ITALIC_FONT.search(str(s.get("font", ""))))
            bbox = tuple(float(v) for v in block["bbox"])
            center = pymupdf.Point((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)
            boxed = any(rect.contains(center) for rect in boxes)
            sizes[size] += len(text)
            extraction.blocks.append(
                Block(
                    page=index + 1,
                    text=text,
                    size=size,
                    bold=bool(flags & 16) or bool(BOLD_FONT.search(font)),
                    italic=italic_chars > 0.6 * sum(len(s["text"]) for s in spans),
                    boxed=boxed,
                    bbox=(bbox[0], bbox[1], bbox[2], bbox[3]),
                )
            )
        try:
            for table in page.find_tables().tables:
                rows = [[str(c or "").strip() for c in row] for row in table.extract()]
                if len(rows) >= 2:
                    extraction.tables.append((index + 1, rows))
        except Exception:  # pragma: no cover - versiones antiguas de PyMuPDF
            pass
        page_text = page.get_text("text")[:2000]
        for info in page.get_images(full=True):
            xref = int(info[0])
            if xref in seen_xrefs:
                continue
            seen_xrefs.add(xref)
            try:
                image = doc.extract_image(xref)
            except Exception:
                continue
            width, height = int(image.get("width", 0)), int(image.get("height", 0))
            if width < min_image_px or height < min_image_px:
                continue
            target = assets_dir / f"p{index + 1:04d}_x{xref}.{image.get('ext', 'png')}"
            target.write_bytes(image["image"])
            coverage = 0.0
            try:
                for rect in page.get_image_rects(xref):
                    coverage = max(coverage, (rect.width * rect.height) / page_area)
            except Exception:
                coverage = 0.0
            extraction.images.append(ImageInfo(index + 1, target, width, height, coverage, page_text))
    doc.close()
    if sizes:
        extraction.body_size = sizes.most_common(1)[0][0]
    return extraction
