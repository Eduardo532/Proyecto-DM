"""Extracción segura de archivos ZIP (también ZIP dentro de ZIP), con límites contra archivos maliciosos."""

from __future__ import annotations

import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

MAX_FILES = 3000
MAX_TOTAL_BYTES = 4 * 1024**3
MAX_FILE_BYTES = 1024**3
MAX_RATIO = 250
MAX_DEPTH = 3
IGNORED_PARTS = ("__MACOSX", ".DS_Store", "Thumbs.db", "desktop.ini")


class ArchiveError(ValueError):
    pass


class BadArchive(ArchiveError):
    pass


@dataclass
class ExtractedFile:
    path: Path
    relative: str  # ruta dentro del archivo, con «/» (los ZIP anidados aparecen como carpeta)


@dataclass
class _Budget:
    files: int = 0
    total: int = 0


def _safe_relative(name: str) -> PurePosixPath | None:
    path = PurePosixPath(name.replace("\\", "/"))
    parts = [p for p in path.parts if p not in ("", ".")]
    if not parts or any(p == ".." for p in parts) or path.is_absolute() or ":" in parts[0]:
        return None
    if any(p in IGNORED_PARTS or p.startswith("._") for p in parts):
        return None
    return PurePosixPath(*parts)


def extract_archive(archive: Path, destination: Path, prefix: str = "", depth: int = 0,
                    budget: _Budget | None = None) -> list[ExtractedFile]:
    """Extrae ``archive`` dentro de ``destination`` y devuelve los archivos (no los ZIP intermedios)."""
    budget = budget or _Budget()
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    result: list[ExtractedFile] = []
    try:
        bundle = zipfile.ZipFile(archive)
    except zipfile.BadZipFile as exc:
        raise BadArchive(f"{archive.name}: no es un ZIP válido.") from exc
    with bundle:
        for info in bundle.infolist():
            if info.is_dir() or (info.external_attr >> 16) & 0o170000 == 0o120000:  # carpetas y enlaces
                continue
            relative = _safe_relative(info.filename)
            if relative is None:
                continue
            budget.files += 1
            budget.total += info.file_size
            if budget.files > MAX_FILES or budget.total > MAX_TOTAL_BYTES:
                raise ArchiveError("El archivo es demasiado grande o tiene demasiados ficheros.")
            if info.file_size > MAX_FILE_BYTES or (
                info.compress_size and info.file_size / info.compress_size > MAX_RATIO and info.file_size > 50 * 1024**2
            ):
                continue
            target = (root / relative).resolve()
            if not target.is_relative_to(root):
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with bundle.open(info) as source, target.open("wb") as sink:
                shutil.copyfileobj(source, sink, length=1024 * 1024)
            label = f"{prefix}{relative.as_posix()}"
            if target.suffix.lower() == ".zip" and depth < MAX_DEPTH:
                inner = target.with_name(target.stem + "_zip")
                try:
                    result.extend(extract_archive(target, inner, f"{label}/", depth + 1, budget))
                    target.unlink()
                    continue
                except BadArchive:
                    pass
            result.append(ExtractedFile(target, label))
    return result
