#!/usr/bin/env bash
# Arranca Virtual Dungeon Master con Docker: aplicación + Ollama + modelos.
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v docker >/dev/null 2>&1; then
  echo "❌ No se encontró Docker. Instálalo: https://docs.docker.com/engine/install/" >&2
  exit 1
fi
if ! docker compose version >/dev/null 2>&1; then
  echo "❌ Falta el plugin 'docker compose'. Instala Docker Compose v2." >&2
  exit 1
fi
if ! docker info >/dev/null 2>&1; then
  echo "❌ Docker no responde. ¿Está en marcha el servicio? (sudo systemctl start docker)" >&2
  echo "   Si es un problema de permisos: sudo usermod -aG docker \$USER y vuelve a iniciar sesión." >&2
  exit 1
fi

FILES=(-f docker-compose.yml)
if command -v nvidia-smi >/dev/null 2>&1 && docker info 2>/dev/null | grep -qi nvidia; then
  echo "✅ GPU NVIDIA detectada: Ollama usará la tarjeta gráfica."
  FILES+=(-f docker-compose.gpu.yml)
elif command -v nvidia-smi >/dev/null 2>&1; then
  echo "⚠️  Hay una GPU NVIDIA pero Docker no puede usarla: falta el NVIDIA Container Toolkit."
  echo "   Instrucciones: docs/docker.md. Mientras tanto, la IA funcionará en la CPU (más lenta)."
else
  echo "ℹ️  Sin GPU NVIDIA: la IA funcionará en la CPU (más lenta)."
fi

mkdir -p data
echo "🔨 Construyendo y arrancando (la primera vez tarda varios minutos)…"
docker compose "${FILES[@]}" up -d --build

echo "⏳ Esperando a la aplicación…"
for _ in $(seq 1 60); do
  if curl -fsS "http://localhost:${VDM_PORT:-8000}/api/health" >/dev/null 2>&1; then
    URL="http://localhost:${VDM_PORT:-8000}"
    echo "🐉 Listo: $URL"
    echo "   Los modelos de IA se descargan en segundo plano la primera vez:"
    echo "   docker compose logs -f ollama-init"
    (xdg-open "$URL" >/dev/null 2>&1 || true) &
    exit 0
  fi
  sleep 2
done
echo "⚠️  La aplicación no respondió a tiempo. Revisa: docker compose logs app" >&2
exit 1
