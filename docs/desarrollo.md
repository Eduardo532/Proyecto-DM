# Guía de desarrollo

Cómo instalar, ejecutar y probar el proyecto en **Windows** y **Linux**.

## Requisitos

| Herramienta | Versión | Comprobar |
|---|---|---|
| Git | cualquiera reciente | `git --version` |
| Python | 3.12 o superior | Windows: `py -3.12 --version` · Linux: `python3.12 --version` |
| Node.js | 20 LTS o superior (a partir del frontend) | `node --version` |
| Ollama | a partir de la fase 2 | ver [guía de Ollama](./guia-ollama.md) |

En Windows, instala Python desde <https://www.python.org/downloads/> marcando **"Add python.exe to PATH"**.

## 1. Clonar el repositorio

```bash
git clone https://github.com/Eduardo532/Proyecto-DM.git
cd Proyecto-DM
```

## 2. Backend

Todo se ejecuta dentro de la carpeta `backend/`, en un entorno virtual (`.venv`) para no mezclar paquetes con el resto del sistema.

### Windows (PowerShell)

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Si PowerShell bloquea `Activate.ps1` por la política de ejecución, ejecuta una vez:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### Linux (bash)

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

`-e` instala el proyecto en modo editable (los cambios en el código se aplican sin reinstalar) y `[dev]` añade las herramientas de pruebas y calidad.

### Arrancar el servidor

Con el entorno virtual activado, desde `backend/`:

```bash
uvicorn app.main:create_app --factory --reload
```

- `--factory`: uvicorn llama a `create_app()` para construir la aplicación.
- `--reload`: reinicia el servidor al guardar cambios.

Al arrancar, el servidor crea la carpeta `data/` en la raíz del repositorio, crea `data/vdm.sqlite3` y aplica las migraciones pendientes.

### Comprobar que funciona

1. Abre <http://127.0.0.1:8000/api/health>. Debes ver:

   ```json
   {"status":"ok","version":"0.1.0","database":{"journal_mode":"wal","foreign_keys":true,"schema_revision":"0001"}}
   ```

2. Abre <http://127.0.0.1:8000/docs> para ver la documentación interactiva de la API.

### Pruebas y calidad

Desde `backend/` con el entorno activado:

```bash
pytest          # pruebas automatizadas
ruff check .    # errores y estilo
ruff format .   # formatea el código
mypy app        # comprobación de tipos
```

### Migraciones de base de datos

Las migraciones (cambios de estructura de la base de datos) están en `backend/alembic/versions/`.

```bash
alembic upgrade head        # aplicar todas
alembic downgrade -1        # deshacer la última
alembic revision --autogenerate -m "descripcion"   # crear una nueva tras cambiar un modelo
```

Revisa siempre el archivo generado antes de confirmarlo: en SQLite algunas operaciones necesitan ajustes.

## 3. Integración continua

Cada PR ejecuta en GitHub Actions, en **Ubuntu y Windows**: `ruff`, `mypy` y `pytest`. Un PR no se fusiona si alguno falla.
