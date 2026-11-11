# 6. Procesamiento de PDF

> Cubre el punto 13 y la sección 4 del prompt maestro.

## 6.1 Expectativas realistas

Las aventuras de rol tienen maquetación compleja: dos columnas, recuadros, texto para leer en voz alta, bloques de estadísticas, mapas a página completa. Ninguna herramienta lo interpreta perfectamente. El diseño asume que **la extracción automática da un borrador que el usuario revisa**, y que la revisión debe ser rápida.

## 6.2 Canal de procesamiento

El procesamiento corre en segundo plano (tarea asíncrona dentro del mismo proceso, con progreso por WebSocket) y es **reanudable**: cada etapa guarda su resultado, así que un fallo no obliga a empezar de cero.

| Etapa | Qué hace | Herramienta | Salida |
|---|---|---|---|
| 1. Registro | Copia el PDF a `data/campaigns/<id>/documents/`, calcula SHA-256, cuenta páginas | PyMuPDF | `document` |
| 2. Detección de tipo de página | Texto seleccionable vs escaneado (poco texto + imagen a página completa) | PyMuPDF | marca por página |
| 3. OCR (si hace falta) | Reconocimiento en español | Tesseract (`spa`) | texto con posiciones |
| 4. Extracción de bloques | Texto con fuente, tamaño, color y posición; orden de lectura por columnas | PyMuPDF `get_text("dict")` | bloques |
| 5. Estructura | Jerarquía de títulos por tamaño/peso de fuente; detección de áreas numeradas ("7. Osario") | Heurísticas propias | árbol de secciones |
| 6. Tipos de bloque | Texto para leer en voz alta (recuadro/cursiva/fondo de color), bloque de estadísticas (patrón "Clase de Armadura… Puntos de golpe…"), tabla, recuadro lateral | Heurísticas + LLM para casos dudosos | `document_chunk.kind` |
| 7. Tablas | Detección y extracción a filas/columnas | PyMuPDF `find_tables` | JSON |
| 8. Imágenes | Extracción, tamaño, página, texto cercano | PyMuPDF | `document_asset` |
| 9. Candidatos a mapa | Imagen grande + texto cercano "mapa" / numeración de áreas / cuadrícula detectable | Heurísticas + (opcional) modelo con visión | `kind='map'` |
| 10. Entidades | NPC, criaturas, objetos, trampas, misiones, encuentros, escenas, con referencia a su fragmento | LLM con salida estructurada, por capítulo | `npc`, `stat_block`, `scene`, `quest`, `fact`… en estado *borrador* |
| 11. Clasificación de conocimiento | `public`/`conditional`/`dm` por fragmento y por hecho | LLM + reglas | `knowledge_level` |
| 12. Relaciones | "Ver área 12", "el NPC del capítulo 2" → enlaces entre escenas, NPC y encuentros | LLM + coincidencia de nombres | referencias |
| 13. Indexación | FTS5 + embeddings | sqlite-vec | índices |
| 14. Revisión | Pantalla de revisión en modo DM | UI | correcciones `classification_source='manual'` |

## 6.3 Bloques de estadísticas

Los bloques de criatura de 5e tienen un formato muy regular. Se parsean con un analizador determinista (expresiones regulares tolerantes a español e inglés) a `stat_block`. Solo si falla se recurre al LLM, y el resultado se valida con el esquema de `stat_block` (rangos de CA, características 1–30, VD válido). Los que no validan quedan marcados para revisión.

## 6.4 Clasificación de conocimiento

Reglas iniciales (el LLM aplica estas pautas y explica su decisión en una línea, que el DM ve en la revisión):

| Señal en el documento | Nivel por defecto |
|---|---|
| Texto para leer en voz alta | `public` (se revela al entrar en la escena) |
| Descripción de sala sin recuadro | `dm`, con hechos `public` extraídos de lo que es visible |
| Trampas, puertas secretas, objetos escondidos, pistas | `conditional` con `discovery_conditions` (habilidad y CD si el texto las indica) |
| Estadísticas, tácticas, motivaciones, desenlaces, notas del autor | `dm` |
| Introducción "para el DM", resumen de la aventura | `dm` |
| Material para entregar a los jugadores (handouts) | `public` al entregarse |

Principio: **ante la duda, `dm`**. Es preferible que el DM tenga que revelar algo manualmente a que se filtre.

## 6.5 Revisión

La pantalla de revisión (modo DM) muestra el PDF original a la izquierda y lo extraído a la derecha, con filtros "pendiente de revisar" y "baja confianza". Permite cambiar el nivel de un fragmento, fusionar o dividir fragmentos, corregir un bloque de estadísticas y asociar un mapa a una escena.

## 6.6 Copyright y almacenamiento

- Los PDF y sus derivados se guardan solo en `data/`, que está en `.gitignore`.
- Las pruebas usan una **aventura de prueba propia** escrita para el proyecto (con reglas del SRD 5.1), nunca material comercial.
- Los fragmentos se envían al proveedor de LLM durante el procesamiento y el juego; esto se indica claramente en la configuración. Con Ollama no sale nada del equipo.
