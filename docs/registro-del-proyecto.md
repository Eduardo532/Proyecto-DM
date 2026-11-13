# Registro del proyecto

Registro vivo pedido en la sección 21 del prompt maestro. Se actualiza en cada PR.

## Estado actual (2026-11-13)

- **MVP completo y ejecutable con un solo comando** (`./iniciar.sh` o `iniciar.bat`).
- **Importación universal** (PR #24): aventuras, packs ZIP, mapas con variantes, fichas de D&D Beyond / Nivel20 / hoja oficial / impresas, ilustraciones, tokens y marcadores de estado.
- **Verificado automáticamente** en cada PR: 81 pruebas de backend (Ubuntu y Windows), 5 de frontend, compilación de la interfaz y construcción y arranque de la imagen Docker.
- **Pendiente de verificar en tu equipo:** el arranque con Docker y GPU en tu Linux, y la calidad real de la IA con `qwen3.5:2b`. Las pruebas de la IA usan un modelo simulado; no he podido ejecutar un modelo real en mi entorno.

## Funcionalidades terminadas

| Área | Detalle | Verificación |
|---|---|---|
| Diseño | Análisis completo en 24 puntos (`docs/diseno/`) | Revisión |
| Motor de reglas 5e 2014 | Dados (expresiones, físicos y digitales, ventaja), características, 18 habilidades, competencia y pericia, pruebas, salvaciones, ataques con crítico, daño con resistencias/inmunidades/vulnerabilidades, PG temporales, 0 PG, muerte instantánea, salvaciones contra muerte, estabilización, 14 condiciones y agotamiento, tabla de PX | 42 pruebas unitarias |
| Combate | Iniciativa con desempate, economía de acción, Correr, Retirarse, movimiento con presupuesto, enemigos automáticos (acercarse, atacar, huir malheridos) | Pruebas de motor y API |
| Mapas | Cuadrícula, distancias 5e y 5-10-5, Dijkstra con terreno difícil y ocupación, puertas, línea de visión, iluminación, visión en la oscuridad, niebla de grupo, editor de capa lógica, calibración de imágenes | Pruebas de motor y API |
| Datos | 19 tablas, migraciones Alembic, eventos inmutables por disparador, FTS5 | Prueba modelos = migraciones |
| API | REST + WebSocket, modo DM con PIN y token temporal, proyecciones que no envían secretos a la mesa | Pruebas de extremo a extremo de la API |
| Importación | Un punto de subida para PDF, imágenes y ZIP anidados (límites contra rutas peligrosas y archivos desmesurados); reconocimiento por contenido; manifiesto por archivo con tipo, motivo y estado; fichas como borrador hasta confirmar; mapas agrupados por variante con cuadrícula detectada (también rectangular) e imagen del DM aparte; marcadores de estado sobre los tokens | Pruebas con PDF e imágenes sintéticos; reconocimiento, lectura de fichas y cuadrícula comprobados con packs reales de DMsGuild y fichas de Nivel20 (no incluidos en el repositorio) |
| PDF | Extracción con PyMuPDF, OCR con Tesseract, orden de lectura a dos columnas, títulos con letras duplicadas, encabezados y áreas numeradas → escenas, lugares sin numerar con texto en voz alta → escenas, texto en voz alta → público, bloques de estadísticas → DM, frases con CD → hechos con habilidad y CD, tablas, imágenes y detección de mapas, revisión manual | PDF de prueba propio |
| Búsqueda (RAG) | Híbrida palabras + embeddings (`qwen3-embedding`) con filtro de nivel dentro de la consulta | Pruebas: la mesa no encuentra secretos |
| IA | Ollama o API compatible con OpenAI; canal fijo (clasificar → motor → narrar), CD del PDF por encima de la del modelo, revelación solo con éxito, filtro de fugas con reescritura, diálogo con PNJ y memoria, narración de escenas y "Anteriormente…", resumen de sesión con modelo y respaldo determinista | Pruebas con modelo simulado |
| Interfaz | Biblioteca, mesa (narración, selector de jugador, acciones, tiradas), mapa con niebla, fichas y editor, diario, combate, panel DM completo | `tsc`, `vitest`, `vite build` |
| Distribución | Imagen Docker (interfaz + backend + Tesseract), Compose con Ollama y descarga de modelos, GPU NVIDIA automática, scripts para Linux y Windows | Construcción y prueba de humo en CI |

## Funcionalidades pendientes

| Prioridad | Pendiente |
|---|---|
| Alta | Probar la calidad real de `qwen3.5:2b` y `qwen3.5:4b` con una aventura y ajustar las instrucciones del modelo |
| Alta | Ataques de los personajes asistidos por el motor (hoy: tirada libre + daño manual en la ficha) |
| Media | Descansos corto y largo, espacios de conjuro y dados de golpe desde la interfaz (los datos existen en la ficha) |
| Media | Concentración, ataques de oportunidad y cobertura conectados al combate en la interfaz (existen en el motor) |
| Media | Enlazar puertas secretas del mapa con su hecho desde el editor (hoy se descubren por el hecho, no se dibujan solas) |
| Media | Creación guiada de personajes con datos del SRD 5.1 (razas, clases, conjuros) |
| Baja | Generación de mapas por IA (fase 8): especificación → capa lógica → dibujo |
| Baja | Narración en streaming (hoy llega completa) |
| Baja | Visión individual por personaje (hoy visión de grupo) |

## Errores y limitaciones conocidos

- **Imagen completa del mapa:** la niebla se dibuja en la interfaz sobre la imagen del PDF; la imagen original sí se envía al navegador. Con pantalla compartida no es un problema práctico, pero un jugador que abra la URL de la imagen vería el mapa entero.
- **PDF con maquetación compleja:** el orden a dos columnas se resuelve, pero recuadros laterales o tres columnas pueden mezclarse. Revisa la clasificación en *Importar*.
- **Fichas por posición (Nivel20, hojas impresas):** se leen por etiquetas y posiciones; si una plataforma cambia su diseño puede faltar algún dato. El borrador avisa de lo que no encontró (p. ej. espacios de conjuro estimados) y se puede corregir antes de crear el personaje. Las fichas de Nivel20 no incluyen inventario si el personaje no lo tiene.
- **Cuadrícula automática:** funciona con cuadrículas visibles; en mapas sin cuadrícula se usa un tamaño aproximado (≈30 casillas en el lado largo) que hay que ajustar. Si el pack trae versión *con cuadrícula*, se mide en ella y a la mesa se le muestra la versión limpia.
- **Modelos pequeños:** con 2–4 B parámetros la clasificación de acciones puede fallar; el sistema pide aclaración o trata la acción como automática, y el motor impone siempre la CD y las reglas.
- **Primer arranque:** la descarga de modelos (~3 GB) puede tardar; hasta entonces la IA avisa de que no está disponible.
- **Datos en `./data` con Docker en Linux:** los archivos quedan como propiedad de `root`.

## Decisiones arquitectónicas

| # | Decisión | Estado | Documento |
|---|---|---|---|
| D-01 | Monolito modular FastAPI + SPA React; la IA solo actúa mediante el motor | Aplicada | [02](./diseno/02-arquitectura.md) |
| D-02 | Event log inmutable (disparadores SQLite) + estado actual en tablas | Aplicada | [03](./diseno/03-modelo-de-datos.md) |
| D-03 | Tres niveles de conocimiento, cerrado por defecto (`dm`) | Aplicada | [03](./diseno/03-modelo-de-datos.md), [05](./diseno/05-ia-narrativa-rag-y-secretos.md) |
| D-04 | RAG propio con FTS5, filtro de nivel dentro de la consulta | Aplicada | [05](./diseno/05-ia-narrativa-rag-y-secretos.md) |
| D-05 | Adaptador de proveedor propio (Ollama y compatible con OpenAI) | Aplicada | [02](./diseno/02-arquitectura.md) |
| D-06 | Mapas: la capa lógica manda; la imagen es decoración | Aplicada | [07](./diseno/07-mapas.md) |
| D-07 | Solo reglas del SRD 5.1 en el repositorio | Aplicada | [08](./diseno/08-reglas-y-combate.md) |
| D-08 | Núcleo de reglas antes del motor narrativo | Aplicada | [10](./diseno/10-pruebas-fases-riesgos-mvp.md) |
| D-09 | Visión de grupo en pantalla compartida | Aplicada | [07](./diseno/07-mapas.md) |
| D-10 | Ollama local; equipo de referencia Linux + NVIDIA 4 GB → `qwen3.5:2b` | Aplicada | [guía de Ollama](./guia-ollama.md) |
| D-11 | Embeddings con `qwen3-embedding` vía Ollama | Aplicada | [02](./diseno/02-arquitectura.md) |
| D-12 | Windows y Linux; CI en ambos | Aplicada | [desarrollo](./desarrollo.md) |
| D-13 | Turno de IA en canal fijo con formularios JSON cerrados | Aplicada | [05](./diseno/05-ia-narrativa-rag-y-secretos.md) |
| D-14 | Búsqueda semántica por fuerza bruta con NumPy en lugar de `sqlite-vec` (sin extensiones nativas; suficiente para miles de fragmentos) | Aplicada | — |
| D-15 | Capa lógica del mapa como JSON en la tabla `map` en lugar de una tabla `map_tile` (el mapa se edita y se carga entero) | Aplicada | — |
| D-16 | Inventario, conjuros y rasgos dentro de la ficha (JSON validado) en lugar de tablas aparte en el MVP | Aplicada | — |
| D-17 | Distribución con Docker Compose y un solo comando; la interfaz la sirve el backend | Aplicada | [docker](./docker.md) |
| D-18 | Enemigos con táctica determinista; el modelo solo narra su turno (no depende de la velocidad del modelo) | Aplicada | — |
| D-19 | Fusión de PR por Claude cuando la CI está en verde (por indicación del propietario) | Aplicada | — |
| D-20 | Importación universal: cada archivo subido es un `Document` con `kind` y `manifest`; los PDF de un ZIP son documentos hijos (`parent_id`) | Aplicada | — |
| D-21 | Migraciones que solo añaden columnas (sin recrear tablas, para no disparar claves foráneas en SQLite); referencias nuevas sin clave foránea (`dm_background_asset_id`) | Aplicada | — |
| D-22 | Las fichas importadas no crean personajes hasta que el DM confirma (borrador en el manifiesto) | Aplicada | — |
| D-23 | El material de terceros usado para ajustar el importador no se sube al repositorio; las pruebas usan documentos sintéticos | Aplicada | — |

## Próxima tarea

1. **Tú:** ejecutar `./iniciar.sh`, crear una campaña de prueba y contar qué tal narra `qwen3.5:2b` (y, si quieres, probar `qwen3.5:4b`).
2. Con esa información: ajustar las instrucciones del modelo y abordar los pendientes de prioridad alta.
