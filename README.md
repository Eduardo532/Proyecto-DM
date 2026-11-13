# Virtual Dungeon Master

Aplicación web local que usa inteligencia artificial para dirigir partidas de **Dungeons & Dragons 5e (2014)** a partir de aventuras en PDF, con un motor de reglas determinista, mapas con niebla de guerra, combate por turnos y memoria de campaña.

**La IA proporciona la inteligencia narrativa. El motor de reglas garantiza la coherencia mecánica.**

## Inicio rápido (un solo comando)

Requisito: [Docker](https://docs.docker.com/engine/install/) (en Windows, Docker Desktop). Para usar la tarjeta gráfica NVIDIA en Linux, instala también el NVIDIA Container Toolkit ([docs/docker.md](docs/docker.md)).

```bash
git clone https://github.com/Eduardo532/Proyecto-DM.git
cd Proyecto-DM
./iniciar.sh          # Linux
iniciar.bat           # Windows (doble clic)
```

Abre <http://localhost:8000>. La primera vez se descargan los modelos de IA (unos 3 GB) en segundo plano; mientras tanto ya puedes crear la campaña e importar la aventura, los mapas y las fichas.

Para detenerlo: `./detener.sh` o `detener.bat`. Las partidas se guardan en la carpeta `data/`.

## Qué incluye

| Área | Funciona |
|---|---|
| Campañas | Biblioteca, PIN del modo DM, dados digitales o físicos |
| Importación | PDF, imágenes y ZIP (también ZIP dentro de ZIP). Reconoce aventuras (también a dos columnas), fichas de personaje (D&D Beyond, Nivel20, hoja oficial rellenable o impresa), mapas con sus versiones DM / jugadores / con y sin cuadrícula, ilustraciones, tokens y marcadores de estado |
| Aventuras | OCR de páginas escaneadas, detección de escenas, texto para leer en voz alta, bloques de estadísticas, CD y habilidades; revisión de qué puede saber la mesa |
| IA (Ollama local) | Narración de escenas, interpretación de acciones libres, petición de tiradas con CD oculta, revelación de secretos solo con éxito, diálogo con PNJ, resúmenes de sesión, filtro de fugas de secretos |
| Reglas 5e 2014 | Características, habilidades, salvaciones, ventaja/desventaja, daño con resistencias, PG temporales, 0 PG y salvaciones contra muerte, condiciones y agotamiento |
| Personajes | Fichas completas con valores calculados, historial de cambios, varios jugadores en una pantalla con selector de jugador activo |
| Mapas | Imágenes importadas con cuadrícula detectada automáticamente (también casillas rectangulares), versión del DM aparte, editor de paredes/puertas/terreno/luces, fichas, movimiento validado, línea de visión, visión en la oscuridad y niebla de guerra |
| Combate | Iniciativa, turnos, acción/adicional/movimiento, Correr, Retirarse, enemigos que se mueven y atacan solos |
| Memoria | Registro inmutable de eventos, hechos conocidos, memoria de PNJ, resúmenes, "Anteriormente…" al reanudar |

Lo que falta o tiene límites conocidos está en el [registro del proyecto](docs/registro-del-proyecto.md).

## Documentación

- [Guía de juego](docs/guia-de-juego.md): cómo preparar y jugar una partida.
- [Docker](docs/docker.md): instalación, GPU, cambio de modelo, copias de seguridad.
- [Guía de Ollama](docs/guia-ollama.md): qué modelo usar según tu tarjeta gráfica.
- [Guía de desarrollo](docs/desarrollo.md): ejecutar sin Docker, pruebas y estructura.
- [Registro del proyecto](docs/registro-del-proyecto.md): hecho, pendiente, errores conocidos y decisiones.
- Diseño: [prompt maestro](docs/prompt-maestro.md) y [análisis y diseño](docs/diseno/01-producto-y-requisitos.md) (11 documentos en `docs/diseno/`).

## Licencias y contenido

- Las aventuras, mapas y fichas que importes se quedan en tu equipo (`data/`, excluido de Git) y no se redistribuyen.
- Las reglas proceden del System Reference Document 5.1 de Wizards of the Coast, bajo licencia [Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/legalcode). Este proyecto no está afiliado a Wizards of the Coast.
