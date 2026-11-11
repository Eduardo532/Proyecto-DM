# 1. Producto y requisitos

> Cubre los puntos 1, 2 y 3 de la sección 22 del [prompt maestro](../prompt-maestro.md).

## 1.1 Descripción general del producto

**Virtual Dungeon Master (VDM)** es una aplicación web que se ejecuta en `localhost` y dirige partidas de Dungeons & Dragons 5e (2014) usando un modelo de lenguaje como Dungeon Master.

El grupo se sienta frente a **una sola pantalla**. Una persona (o varias, por turnos) escribe lo que hace cada personaje, elegido con un selector de jugador activo. La IA narra, interpreta a los NPC y decide cuándo hace falta una tirada; un **motor de reglas escrito en código** calcula modificadores, daño, distancias y estados, y guarda todo en SQLite.

El contenido de la aventura sale de los **PDF que aporta el usuario**. La aplicación los procesa, los divide en fragmentos clasificados por nivel de secreto y los consulta durante la partida (RAG) sin cargar el documento entero en cada petición.

Qué lo diferencia de un chatbot:

| Chatbot de rol | Virtual Dungeon Master |
|---|---|
| El estado vive en el historial de conversación | El estado vive en la base de datos; el historial es solo una vista |
| El modelo "inventa" las tiradas y los números | El motor tira los dados y calcula; el modelo solo los solicita |
| El modelo ve todo y se le pide discreción | El backend decide qué información puede llegar a cada contexto |
| Mapas descritos en texto | Mapas con capa visual y capa lógica, tokens y niebla de guerra |
| Se olvida entre sesiones | Memoria estructurada, resúmenes y estado del mundo persistentes |

## 1.2 Requisitos funcionales

Numerados para poder referenciarlos desde issues (`RF-xx`). La columna **MVP** indica si entran en la primera versión jugable (sección 19 del prompt maestro).

### Campañas y documentos

| ID | Requisito | MVP |
|---|---|---|
| RF-01 | Crear, listar, editar, archivar y eliminar campañas | Sí |
| RF-02 | Importar uno o varios PDF por campaña (aventura, módulo, suplemento) | Sí |
| RF-03 | Extraer texto conservando página, capítulo y sección de origen | Sí |
| RF-04 | Extraer imágenes y marcar candidatas a mapa | Sí |
| RF-05 | Extraer tablas (incluidos bloques de estadísticas de criaturas) | Parcial |
| RF-06 | OCR para PDF escaneados | No (fase 2+) |
| RF-07 | Clasificar cada fragmento como público, condicionado o exclusivo del DM | Sí |
| RF-08 | Revisar y corregir manualmente la clasificación desde el panel del DM | Sí |
| RF-09 | Identificar escenas, NPC, criaturas, encuentros, objetos, trampas y misiones | Parcial |
| RF-10 | Consultar la campaña por búsqueda semántica y por texto, con cita de página | Sí |
| RF-11 | Añadir notas y modificaciones propias a la campaña | Sí |

### Jugadores y personajes

| ID | Requisito | MVP |
|---|---|---|
| RF-20 | Registrar participantes sin cuentas | Sí |
| RF-21 | Crear personajes de 5e (2014) con ficha completa | Sí |
| RF-22 | Importar fichas (formato JSON propio; otros formatos a definir) | No |
| RF-23 | Asociar uno o más personajes a cada participante | Sí |
| RF-24 | Selector de jugador activo con orden configurable | Sí |
| RF-25 | Cambiar de jugador activo sin perder el contexto | Sí |
| RF-26 | Calcular automáticamente modificadores, competencias, CA, salvaciones, percepción pasiva | Sí |
| RF-27 | Actualizar la ficha mediante operaciones validadas (daño, curación, objetos, espacios de conjuro, condiciones, experiencia) con historial | Sí |

### Dirección de juego (IA)

| ID | Requisito | MVP |
|---|---|---|
| RF-30 | Narrar la escena al entrar usando solo información percibible | Sí |
| RF-31 | Aceptar acciones en texto libre | Sí |
| RF-32 | Clasificar la acción: automática, requiere tirada, imposible, requiere preparación | Sí |
| RF-33 | Determinar característica/habilidad, CD, ventaja/desventaja; mantener la CD oculta salvo justificación | Sí |
| RF-34 | Solicitar la tirada y detenerse hasta recibirla | Sí |
| RF-35 | Narrar las consecuencias del resultado ya calculado por el motor | Sí |
| RF-36 | Interpretar NPC con personalidad, memoria y conocimiento limitado | Sí (básico) |
| RF-37 | Improvisar sin contradecir hechos establecidos | Sí |
| RF-38 | No actuar por los personajes ni adelantar acontecimientos | Sí |

### Dados

| ID | Requisito | MVP |
|---|---|---|
| RF-40 | Dados d4, d6, d8, d10, d12, d20, d100 y expresiones (`2d6+3`) | Sí |
| RF-41 | Modo digital (servidor) y modo manual (dados físicos), configurable por campaña y por tirada | Sí |
| RF-42 | Ventaja y desventaja | Sí |
| RF-43 | Pruebas de característica, habilidad, salvación, ataque, daño, iniciativa, salvación contra muerte | Sí (sin muerte en MVP si no hay combate) |
| RF-44 | Registro inmutable de tiradas con modificadores desglosados | Sí |

### Mapas y exploración

| ID | Requisito | MVP |
|---|---|---|
| RF-50 | Mostrar mapas extraídos del PDF asociados a escenas | Sí |
| RF-51 | Calibrar la cuadrícula manualmente sobre la imagen | Sí |
| RF-52 | Editar la capa lógica (paredes, puertas, terreno difícil, obstáculos, zonas) | Básico |
| RF-53 | Posicionar tokens de personajes, NPC y enemigos en coordenadas | Sí |
| RF-54 | Niebla de guerra con línea de visión e iluminación | No (fase 6) |
| RF-55 | Elementos interactivos seleccionables (puertas, cofres, palancas) | No (fase 6) |
| RF-56 | Generación de mapas por IA | No (fase 8, arquitectura preparada) |

### Combate

| ID | Requisito | MVP |
|---|---|---|
| RF-60 | Vista táctica, iniciativa y orden de turnos | No (fase 7) |
| RF-61 | Economía de acción: acción, adicional, movimiento, reacción | No |
| RF-62 | Ataques, daño con resistencias/vulnerabilidades/inmunidades, cobertura | No |
| RF-63 | Ataques de oportunidad, concentración, condiciones | No |
| RF-64 | 0 PG, salvaciones contra muerte, estabilización, muerte | No |
| RF-65 | Comportamiento táctico de enemigos según inteligencia y objetivos | No |

### Memoria y sesiones

| ID | Requisito | MVP |
|---|---|---|
| RF-70 | Registro cronológico de acontecimientos (append-only) | Sí |
| RF-71 | Iniciar, pausar, cerrar y reanudar sesiones | Sí |
| RF-72 | Resumen estructurado al cerrar sesión | Sí |
| RF-73 | Memoria por campaña, personaje, NPC, misión y lugar | Sí (básica) |
| RF-74 | Corrección manual de recuerdos | Sí |
| RF-75 | Guardar y recuperar partidas; copias de seguridad | Sí |

### Panel del DM

| ID | Requisito | MVP |
|---|---|---|
| RF-80 | Modo privado que oculta la interfaz pública | Sí |
| RF-81 | Consultar secretos, CD, estadísticas, trampas, futuros eventos, contenido original | Sí |
| RF-82 | Intervenir: corregir PG, posiciones, estados, tiradas, eventos; pausar la IA | Parcial |
| RF-83 | Toda intervención queda registrada | Sí |

## 1.3 Requisitos no funcionales

| ID | Categoría | Requisito |
|---|---|---|
| RNF-01 | Ejecución | Funciona en `localhost` en Windows, macOS y Linux con Python 3.12+ y Node 20+ |
| RNF-02 | Sin conexión | Todo lo que no depende del LLM (fichas, dados, mapas, memoria, consulta por texto) funciona sin Internet |
| RNF-03 | Proveedor de IA | El proveedor se cambia por configuración (Anthropic, OpenAI, Ollama) sin tocar el resto del código |
| RNF-04 | Integridad | Ninguna escritura de estado mecánico se hace desde texto libre de la IA; todo pasa por comandos validados |
| RNF-05 | Trazabilidad | Cada cambio de estado genera un evento con autor (jugador, IA, DM, sistema), sesión y marca de tiempo |
| RNF-06 | Confidencialidad | La información `dm` y la `condicionada` no descubierta nunca sale por la API de jugadores |
| RNF-07 | Robustez frente a inyección | El contenido de los PDF se trata como datos; no puede cambiar instrucciones ni permisos |
| RNF-08 | Rendimiento | Respuesta del motor < 100 ms; primera palabra de narración < 3 s con un LLM en la nube (streaming) |
| RNF-09 | Coste | Contexto por turno acotado (objetivo: < 12 000 tokens de entrada) mediante RAG y resúmenes |
| RNF-10 | Persistencia | Escrituras transaccionales; migraciones versionadas; copia de seguridad antes de migrar |
| RNF-11 | Idioma | Interfaz y narración en español; textos de UI en archivos de traducción para añadir idiomas |
| RNF-12 | Accesibilidad | Contraste suficiente, navegación por teclado, tamaños legibles en pantalla compartida (TV o monitor grande) |
| RNF-13 | Calidad | Tipado estricto (mypy/pyright y TypeScript `strict`), pruebas automatizadas, lint en CI |
| RNF-14 | Licencias | Solo se incluyen reglas del SRD 5.1 (CC-BY-4.0); los PDF del usuario no se redistribuyen ni se suben al repositorio |
| RNF-15 | Extensibilidad | Reglas de 5e aisladas tras una interfaz de sistema de juego; modalidad multijugador posible sin rehacer el núcleo |
