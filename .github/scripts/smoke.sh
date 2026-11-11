#!/usr/bin/env bash
# Prueba de humo de la imagen Docker: arranca, responde la API y sirve la interfaz.
set -euo pipefail
docker run -d --name vdm-smoke -p 8000:8000 -e VDM_LLM_PROVIDER=none virtual-dm:ci >/dev/null
trap 'docker logs vdm-smoke | tail -40; docker rm -f vdm-smoke >/dev/null' EXIT
for _ in $(seq 1 30); do
  curl -fsS http://localhost:8000/api/health >/dev/null 2>&1 && break
  sleep 2
done
curl -fsS http://localhost:8000/api/health
curl -fsS http://localhost:8000/ | grep -q "Virtual Dungeon Master"
curl -fsS http://localhost:8000/c/ruta-de-la-interfaz | grep -q '<div id="root">'
curl -fsS -X POST http://localhost:8000/api/campaigns -H 'Content-Type: application/json' -d '{"name":"Humo"}' | grep -q '"name":"Humo"'
curl -fsS http://localhost:8000/api/ai/status | grep -q '"provider":"none"'
echo "Prueba de humo superada."
