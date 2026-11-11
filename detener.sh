#!/usr/bin/env bash
# Detiene Virtual Dungeon Master. Las partidas se conservan en ./data y los modelos en el volumen de Ollama.
set -euo pipefail
cd "$(dirname "$0")"
docker compose -f docker-compose.yml -f docker-compose.gpu.yml down
