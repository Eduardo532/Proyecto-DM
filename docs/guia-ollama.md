# Guía de Ollama para Virtual Dungeon Master

La aplicación usa [Ollama](https://ollama.com) para ejecutar el modelo de lenguaje en tu propio equipo, sin claves de API ni costes por uso (decisión D-10).

## 1. Elegir el modelo según tu tarjeta gráfica

El modelo "más potente" que puedes usar depende de la memoria de vídeo (VRAM). Recomendaciones a noviembre de 2026 (se revisarán al llegar a la fase 3):

| Memoria disponible | Modelo de narración | Descarga aprox. | Comentario |
|---|---|---|---|
| GPU de 24 GB (o más) | `qwen3.8:27b` | 18 GB | Opción recomendada. Admite herramientas, razonamiento ("thinking") e imágenes; licencia Apache 2.0 |
| GPU de 16 GB | `gemma4:12b` | — | Alternativa: `qwen3.8:27b` funciona pero pasa parte del modelo a la RAM y va más lento |
| GPU de 8 GB | `qwen3.5:4b` | — | Narración aceptable; menos fiable con reglas y secretos |
| Sin GPU dedicada | `gemma4:e2b` | — | Solo para probar; lento y de calidad limitada |

Existen modelos abiertos más grandes, pero necesitan varias GPU profesionales o cientos de GB de memoria. Los modelos con etiqueta `:cloud` en Ollama **no** se ejecutan en tu equipo: envían el texto a servidores externos, así que no se usan por defecto.

Embeddings (búsqueda en los PDF): `qwen3-embedding:0.6b` (pequeño, multilingüe). Con memoria de sobra, `qwen3-embedding:4b`.

## 2. Instalación

### Windows

1. Descarga el instalador desde <https://ollama.com/download> y ejecútalo. Ollama queda como servicio en segundo plano (icono en la bandeja del sistema).
2. Abre **PowerShell** y comprueba:

   ```powershell
   ollama --version
   ollama pull qwen3.8:27b
   ollama pull qwen3-embedding:0.6b
   ollama run qwen3.8:27b "Describe en dos frases la entrada de una cripta."
   ```

### Linux

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama --version
ollama pull qwen3.8:27b
ollama pull qwen3-embedding:0.6b
ollama run qwen3.8:27b "Describe en dos frases la entrada de una cripta."
```

En ambos sistemas Ollama escucha en `http://localhost:11434`.

## 3. Configuración en la aplicación

Se hará en `backend/.env` (a partir de la fase 3):

```dotenv
VDM_LLM_PROVIDER=ollama
VDM_LLM_BASE_URL=http://localhost:11434
VDM_LLM_MODEL=qwen3.8:27b
VDM_LLM_AUX_MODEL=qwen3.8:27b        # clasificación y resúmenes; puede ser uno más pequeño
VDM_EMBEDDING_MODEL=qwen3-embedding:0.6b
```

Cambiar de modelo es cambiar estas líneas; no hace falta tocar el código.
