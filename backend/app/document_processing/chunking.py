"""Agrupa bloques en secciones y fragmentos sin cortar bloques de estadísticas ni texto leído en voz alta."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.document_processing.classify import STAT_BLOCK
from app.document_processing.extract import Block

MAX_CHARS = 2400
AREA_HEADING = re.compile(
    r"^\s*(?:[ÁA]rea\s+|Sala\s+|Room\s+|Area\s+)?([A-Z]?\d{1,3}[A-Za-z]?)[.:)]\s+\S", re.IGNORECASE
)


@dataclass
class Piece:
    text: str
    page_start: int
    page_end: int
    section: str
    read_aloud: bool
    area: str | None = None


@dataclass
class Section:
    path: list[str] = field(default_factory=list)
    area: str | None = None


def is_heading(block: Block, body_size: float) -> bool:
    text = block.text.strip()
    if len(text) > 120 or len(text.strip().splitlines()) > 2:
        return False
    if block.size >= body_size + 1.5:
        return True
    return block.bold and len(text) < 80 and not text.endswith(".")


def heading_level(block: Block, body_size: float) -> int:
    if block.size >= body_size + 6:
        return 1
    if block.size >= body_size + 3:
        return 2
    return 3


def build_pieces(blocks: list[Block], body_size: float) -> list[Piece]:
    pieces: list[Piece] = []
    path: list[tuple[int, str]] = []
    area: str | None = None
    buffer: list[Block] = []

    def section_name() -> str:
        return " > ".join(title for _, title in path)

    def flush() -> None:
        nonlocal buffer
        if not buffer:
            return
        text = "\n".join(b.text for b in buffer).strip()
        pieces.append(Piece(text, buffer[0].page, buffer[-1].page, section_name(), False, area))
        buffer = []

    for block in blocks:
        if is_heading(block, body_size):
            flush()
            level = heading_level(block, body_size)
            title = " ".join(block.text.split())
            path = [p for p in path if p[0] < level] + [(level, title)]
            match = AREA_HEADING.match(title)
            area = title if match else (area if level >= 3 else None)
            continue
        is_read_aloud = block.italic or block.boxed
        if is_read_aloud or STAT_BLOCK.search(block.text):
            flush()
            pieces.append(Piece(block.text.strip(), block.page, block.page, section_name(), is_read_aloud, area))
            continue
        if buffer and sum(len(b.text) for b in buffer) + len(block.text) > MAX_CHARS:
            flush()
        buffer.append(block)
    flush()
    return _merge_adjacent_read_aloud(pieces)


def _merge_adjacent_read_aloud(pieces: list[Piece]) -> list[Piece]:
    merged: list[Piece] = []
    for piece in pieces:
        last = merged[-1] if merged else None
        if (last and last.read_aloud and piece.read_aloud and last.section == piece.section
                and len(last.text) + len(piece.text) < MAX_CHARS):
            last.text = f"{last.text}\n{piece.text}"
            last.page_end = piece.page_end
        else:
            merged.append(piece)
    return merged
