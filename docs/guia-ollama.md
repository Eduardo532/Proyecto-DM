# Guía de Ollama para Virtual Dungeon Master

La aplicación usa [Ollama](https://ollama.com) para ejecutar el modelo de lenguaje en tu propio equipo, sin claves de API ni costes por uso (decisión D-10).

## 1. Equipo de referencia del proyecto

| Componente | Valor |
|---|---|
| Sistema | Linux |
| GPU | NVIDIA con 4 GB de VRAM |
| Disco | 700 GB libres (sobra: los modelos ocupan pocos GB) |
| RAM | *pendiente de confirmar* |

Todo el diseño de la IA (fase 3) se prueba con este equipo como mínimo.

## 2. Elegir el modelo

Con 4 GB de VRAM el modelo y su contexto deben caber casi enteros en la tarjeta para que la respuesta sea fluida.

| Modelo | Descarga | Uso en el proyecto |
|---|---|---|
| `qwen3.5:2b` | 2,7 GB | **Por defecto.** Cabe en la GPU dejando ~1 GB para el contexto. Admite herramientas, razonamiento ("thinking") e imágenes |
| `qwen3.5:4b` | ~4 GB | **Calidad.** No cabe entero en 4 GB: Ollama pasa parte a la RAM. Mejor narración, respuestas más lentas. Recomendable si tienes 16 GB de RAM o más |
| `phi4-mini` | ~2,5 GB | Alternativa a probar (solo texto, con herramientas) |
| `llama3.2:3b` | 2,0 GB | Alternativa a probar; más flojo en español |

Se compararán en la fase 3 con pruebas reales de la aventura de prueba (pedir la tirada correcta, no revelar secretos, calidad del español) y se elegirá el definitivo con datos.

**Embeddings** (búsqueda en los PDF): `qwen3-embedding:0.6b` (~0,6 GB, multilingüe). Se ejecuta en la CPU para no competir por la VRAM con el modelo de narración; para indexar unos PDF es suficiente.

**Ollama Cloud no se usa:** los modelos `:cloud` envían el texto a servidores externos y actualmente se pagan por uso.

### Qué esperar de un modelo pequeño

Un modelo de 2–4 B parámetros narra de forma aceptable pero se equivoca más con reglas, herramientas y secretos. Por eso el proyecto lo compensa con diseño (D-13):

- El motor de reglas decide la CD, los modificadores y los resultados; el modelo nunca pone números.
- El turno sigue un canal fijo: el modelo rellena formularios JSON con opciones cerradas y después narra un resultado ya calculado.
- Los secretos no revelados no llegan al modelo salvo los de la escena actual, y su salida pasa por un filtro.
- Si algún día cambias de tarjeta gráfica o quieres usar un servicio externo, basta con cambiar la configuración.

## 3. Instalación en Linux

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama --version
nvidia-smi                      # comprueba que el driver de NVIDIA está activo
ollama pull qwen3.5:2b
ollama pull qwen3-embedding:0.6b
ollama run qwen3.5:2b "Describe en dos frases, en español, la entrada de una cripta."
```

Mientras responde, en otra terminal ejecuta `ollama ps`: la columna **PROCESSOR** debe indicar `100% GPU`. Si indica un reparto CPU/GPU, el modelo no cabe entero en la tarjeta.

Ollama escucha en `http://localhost:11434`.

### Windows

Descarga el instalador desde <https://ollama.com/download>, ejecútalo y usa los mismos comandos `ollama` en PowerShell.

## 4. Configuración en la aplicación

Se hará en `backend/.env` (a partir de la fase 3):

```dotenv
VDM_LLM_PROVIDER=ollama
VDM_LLM_BASE_URL=http://localhost:11434
VDM_LLM_MODEL=qwen3.5:2b
VDM_LLM_TURN_MODE=pipeline           # pipeline (canal fijo) | agent
VDM_LLM_CONTEXT_BUDGET=5000          # tokens de entrada por turno
VDM_EMBEDDING_MODEL=qwen3-embedding:0.6b
```

Cambiar de modelo es cambiar estas líneas; no hace falta tocar el código.
