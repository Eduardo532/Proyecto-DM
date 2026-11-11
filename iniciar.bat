@echo off
rem Arranca Virtual Dungeon Master con Docker Desktop: aplicacion + Ollama + modelos.
setlocal
cd /d "%~dp0"
where docker >nul 2>nul || (echo No se encontro Docker. Instala Docker Desktop: https://www.docker.com/products/docker-desktop/ & pause & exit /b 1)
docker info >nul 2>nul || (echo Docker Desktop no esta en marcha. Abrelo y vuelve a intentarlo. & pause & exit /b 1)
set FILES=-f docker-compose.yml
where nvidia-smi >nul 2>nul && (
  echo GPU NVIDIA detectada: Ollama usara la tarjeta grafica.
  set FILES=-f docker-compose.yml -f docker-compose.gpu.yml
)
if not exist data mkdir data
echo Construyendo y arrancando (la primera vez tarda varios minutos)...
docker compose %FILES% up -d --build || (pause & exit /b 1)
echo Esperando a la aplicacion...
for /l %%i in (1,1,60) do (
  powershell -NoProfile -Command "try { Invoke-WebRequest -UseBasicParsing http://localhost:8000/api/health | Out-Null; exit 0 } catch { exit 1 }" && goto ready
  timeout /t 2 >nul
)
echo La aplicacion no respondio a tiempo. Revisa: docker compose logs app
pause
exit /b 1
:ready
echo Listo: http://localhost:8000
echo Los modelos de IA se descargan la primera vez: docker compose logs -f ollama-init
start "" http://localhost:8000
