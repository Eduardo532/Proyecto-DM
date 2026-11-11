"""Publica el contenido de un archivo como anotación (uso temporal durante el desarrollo)."""

import glob
import sys

for path in glob.glob(sys.argv[1]):
    text = open(path, encoding="utf-8").read()
    for index in range(0, len(text), 30000):
        chunk = text[index : index + 30000].replace("%", "%25").replace("\r", "").replace("\n", "%0A")
        print(f"::warning title=FILE {path} part {index // 30000}::{chunk}")
