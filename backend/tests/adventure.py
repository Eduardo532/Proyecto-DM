"""Aventura de prueba propia (sin material con derechos de autor), generada como PDF."""

from pathlib import Path

import pymupdf


def make_adventure_pdf(path: Path) -> Path:
    doc = pymupdf.open()
    page = doc.new_page()
    y = 72.0

    def write(text: str, size: float = 10, font: str = "helv", gap: float = 14) -> None:
        nonlocal y
        page.insert_text((72, y), text, fontsize=size, fontname=font)
        y += size * 1.4 + gap

    write("La Cripta del Rey Ceniza", 24, "hebo")
    write("Resumen de la aventura", 16, "hebo")
    write("El sacerdote Varis es el verdadero villano y planea despertar al rey.")
    write("1. Entrada de la cripta", 14, "hebo")
    write("Una escalera de piedra desciende hacia la oscuridad. Huele a humedad y a cera.", font="heit")
    write("La pared norte oculta una puerta secreta. Una prueba de Sabiduria (Percepcion) CD 15 la revela.")
    write("Ghoul", 12, "hebo")
    write("Clase de Armadura 12", gap=2)
    write("Puntos de golpe 22 (5d8)", gap=2)
    write("Velocidad 30 pies")
    doc.save(path)
    doc.close()
    return path
