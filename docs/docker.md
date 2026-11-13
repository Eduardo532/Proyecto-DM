# Ejecutar con Docker

Docker arranca tres piezas: **ollama** (el modelo de IA), **ollama-init** (descarga los modelos la primera vez y termina) y **app** (backend + interfaz en <http://localhost:8000>).

## Linux

1. Instala Docker Engine y el plugin Compose: <https://docs.docker.com/engine/install/>.
2. Permite usar Docker sin `sudo` (cierra sesión y vuelve a entrar después):

   ```bash
   sudo usermod -aG docker $USER
   ```

3. **GPU NVIDIA (recomendado).** Comprueba el driver con `nvidia-smi`. Después instala el NVIDIA Container Toolkit siguiendo la guía oficial: <https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html>. En Ubuntu/Debian se resume en:

   ```bash
   curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
   curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
     | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
     | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
   sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
   sudo nvidia-ctk runtime configure --runtime=docker
   sudo systemctl restart docker
   ```

4. Arranca:

   ```bash
   ./iniciar.sh
   ```

   El script detecta la GPU y la usa automáticamente. Sin GPU, la IA funciona en la CPU (más lenta).

## Windows

1. Instala Docker Desktop (con WSL 2): <https://www.docker.com/products/docker-desktop/>.
2. Para la GPU NVIDIA basta con el driver normal de NVIDIA actualizado; Docker Desktop la expone a los contenedores.
3. Haz doble clic en `iniciar.bat`.

## Comandos útiles

```bash
docker compose ps                     # estado
docker compose logs -f ollama-init    # progreso de la descarga de modelos
docker compose logs -f app            # registros de la aplicación
./detener.sh                          # parar (las partidas se conservan)
git pull && ./iniciar.sh              # actualizar a la última versión
```

## Cambiar de modelo

Copia `.env.example` como `.env` y cambia `VDM_LLM_MODEL` (ver [guía de Ollama](guia-ollama.md)). Después ejecuta `./iniciar.sh` de nuevo: el nuevo modelo se descarga solo.

Con tu equipo de referencia (NVIDIA de 4 GB y 24 GB de RAM):

| Modelo | Cuándo usarlo |
|---|---|
| `qwen3.5:2b` (por defecto) | Cabe entero en la GPU: respuestas rápidas |
| `qwen3.5:4b` | Mejor narración; parte del modelo va a la RAM y responde más lento |

## Voz del DM

El servicio `voz` ejecuta [Kokoro](https://github.com/remsky/Kokoro-FastAPI), una voz neuronal local y gratuita, en la CPU (así no compite con el modelo de lenguaje por la memoria de la tarjeta gráfica). La primera vez se descarga su imagen.

- Voces en español: `em_alex` (por defecto), `em_santa` (hombre) y `ef_dora` (mujer). Se eligen en la Mesa (botón 🔊) o con `VDM_TTS_VOICE` en `.env`.
- Sin el servicio, o mientras arranca, la Mesa usa la voz del navegador (en Windows, Edge tiene voces «Natural» en español muy buenas).
- Desactivarlo: `VDM_TTS_URL=` en `.env` y `docker compose stop voz`.
- Otro servidor compatible con la API de OpenAI (`/v1/audio/speech`): pon su dirección en `VDM_TTS_URL`.

## Copias de seguridad

Todo está en la carpeta `data/`: la base de datos `vdm.sqlite3`, los PDF y las imágenes. Para hacer una copia, detén la aplicación y copia la carpeta entera. Los modelos de Ollama están en el volumen `virtual-dm_ollama` y se pueden volver a descargar.
