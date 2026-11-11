"""Ejecuta un comando y, si falla, publica su salida como anotación de GitHub Actions.

Uso: python .github/scripts/run.py "Título" comando arg1 arg2 ...
Así los errores son visibles en la API de check-runs sin descargar los registros.
"""

import subprocess
import sys

title, *command = sys.argv[1:]
result = subprocess.run(command, capture_output=True, text=True)
output = (result.stdout + result.stderr).strip()
print(output)
if result.returncode != 0:
    tail = "\n".join(output.splitlines()[-80:])
    encoded = tail.replace("%", "%25").replace("\r", "").replace("\n", "%0A")
    print(f"::error title={title}::{encoded}")
sys.exit(result.returncode)
