"""Publica un archivo comprimido como anotaciones (uso temporal durante el desarrollo)."""

import base64
import glob
import sys
import zlib

for path in glob.glob(sys.argv[1]):
    data = base64.b64encode(zlib.compress(open(path, "rb").read(), 9)).decode()
    size = 2500
    for index in range(0, len(data), size):
        print(f"::warning title=B64 {index // size}::{data[index : index + size]}")
