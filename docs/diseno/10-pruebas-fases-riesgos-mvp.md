# 10. Pruebas, plan por fases, riesgos y MVP

> Cubre los puntos 21 (plan de pruebas), 22 (plan de desarrollo por fases), 23 (riesgos técnicos) y 24 (alcance realista del MVP).

## 10.1 Plan de pruebas

| Nivel | Qué se prueba | Herramienta | Cuándo |
|---|---|---|---|
| Unitarias del motor | Dados (con semilla), modificadores, pruebas, daño y resistencias, 0 PG y salvaciones contra muerte, condiciones, distancias, movimiento, línea de visión, cobertura | Pytest | Cada commit (CI) |
| Propiedades | Invariantes: `0 ≤ PG ≤ máx`; ningún dado fuera de rango; el movimiento nunca supera la velocidad; una casilla tras una pared nunca es visible; la proyección de jugador nunca contiene `knowledge_level='dm'` | Hypothesis | Cada commit |
| Integración | Servicios + SQLite en memoria: transacciones evento + cambio, versiones, migraciones Alembic arriba/abajo | Pytest | Cada commit |
| API | Rutas REST y WebSocket con `TestClient`; **las rutas de jugadores nunca devuelven campos secretos** (prueba que recorre todas las rutas y busca marcadores sembrados) | Pytest + httpx | Cada commit |
| Procesamiento PDF | Aventura de prueba propia (PDF generado por el proyecto) con salas, recuadros, bloque de estadísticas, tabla, mapa y puerta secreta; se comparan resultados con un "dorado" | Pytest | Cada commit |
| Comportamiento de la IA | Escenarios grabados: no actúa por los jugadores; pide la tirada correcta; no revela CD; no revela el secreto ante 20 intentos de manipulación conocidos; usa herramientas para cambiar PG; respeta "no inventar tiradas" | Pytest con Ollama real (marcadas `@pytest.mark.llm`, fuera del CI porque requieren GPU) y con respuestas grabadas (en CI) | Antes de cada versión |
| Frontend unitario | Componentes de ficha, panel de tiradas, selector de jugador, stores (el store DM se vacía al salir) | Vitest + Testing Library | Cada commit |
| Extremo a extremo | Crear campaña → subir PDF de prueba → crear personajes → iniciar sesión → acción → tirada → resultado → cerrar → reanudar | Playwright con proveedor LLM simulado | Cada PR a `main` |
| Manual | Lista de verificación por fase con pasos para que tú la pruebes y confirmes | Documento en `docs/` | Al cerrar cada fase |

Regla del proyecto: **no se afirma que algo funciona sin prueba ejecutada**. Cada PR indica qué pruebas se corrieron y su resultado real.

## 10.2 Plan de desarrollo por fases

Se mantiene el plan del prompt maestro con **un cambio de orden recomendado**: adelantar el núcleo de reglas (dados, ficha, pruebas) antes del motor narrativo, porque la IA de la fase 3 necesita poder solicitar y resolver tiradas para ser verificable. El resto de la fase 4 (creación completa de personajes, UI de fichas) se queda donde estaba.

| Fase | Contenido | Resultado verificable |
|---|---|---|
| **1. Estructura y base** | Repositorio, CI, backend FastAPI + SQLite + Alembic, frontend React + Tailwind, WebSocket de prueba, tema visual, CRUD de campañas, jugadores y personajes (ficha mínima), copias de seguridad | Crear/editar campaña, reiniciar el servidor y seguir viéndola |
| **2. PDF** | Subida, extracción de texto con estructura, imágenes, tablas, bloques de estadísticas, candidatos a mapa, clasificación de conocimiento, indexación FTS + vectores, pantalla de revisión | Importar el PDF de prueba y buscar "puerta secreta" obteniendo la página correcta solo en modo DM |
| **3a. Núcleo de reglas** *(adelantado de la fase 4)* | Dados, modificadores, pruebas, ventaja/desventaja, CD, registro de tiradas, modo manual/digital | Pruebas unitarias + panel de tiradas funcionando |
| **3b. Motor narrativo e IA** | Adaptador de proveedores, prompts, herramientas, ciclo de turno, RAG en el contexto, gestión de secretos, filtro de fugas, improvisación registrada | Jugar la primera escena de la aventura de prueba: describir, actuar, tirar, descubrir la puerta secreta solo con éxito |
| **4. Personajes y reglas** | Creación guiada de personajes 5e (SRD), ficha completa, recursos, descansos, inventario, experiencia y nivel | Crear 3 personajes de clases distintas y que sus valores derivados coincidan con el cálculo manual |
| **5. Memoria y continuidad** | Resúmenes de sesión validados, memoria por ámbito, memoria de NPC, reanudación, corrección manual | Cerrar y reanudar; la IA recuerda decisiones y un NPC recuerda una mentira |
| **6. Mapas y exploración** | Visor Konva, calibración, editor de capa lógica, tokens, línea de visión, iluminación, niebla, elementos interactivos | Explorar el mapa de prueba sin ver la sala oculta hasta abrir la puerta |
| **7. Combate táctico** | Iniciativa, turnos, economía de acción, movimiento validado, ataques, daño, cobertura, oportunidad, conjuros básicos, concentración, condiciones, 0 PG, IA enemiga | Combate completo de la aventura de prueba, con un enemigo que huye y otro que se cubre |
| **8. Generación avanzada** | Mapas generados (lógica → visual), editor avanzado, tokens personalizados, efectos y sonido ambiental | Generar un mapa desde una descripción y jugar en él |

Cada fase se entrega en una rama con PR, lista de verificación manual y registro actualizado. No se pasa a la siguiente con errores críticos abiertos.

## 10.3 Riesgos técnicos

| # | Riesgo | Prob. | Impacto | Mitigación |
|---|---|---|---|---|
| R1 | Extracción de PDF imprecisa por maquetación variable | Alta | Alto | Borrador + revisión rápida; heurísticas por tipo de bloque; PDF de prueba propio; aceptar que la revisión humana es parte del flujo |
| R2 | Capa lógica de mapas del PDF costosa de crear a mano | Alta | Medio | Editor con herramientas rápidas; propuesta automática como borrador en fase 6+; mapas sin capa lógica utilizables en exploración simple |
| R3 | Filtración de secretos por el LLM | Media | Alto | Defensa estructural en capas (5.5); batería de pruebas de manipulación; "ante la duda, `dm`" |
| R4 | Inconsistencia narrativa en campañas largas | Media | Alto | Hechos estructurados, resúmenes validados contra estado, verificador opcional |
| R5 | El LLM no usa bien las herramientas o "inventa" números | Media | Alto | Toda mecánica solo por herramientas; validación y mensajes de error claros; pruebas de comportamiento |
| R6 | Latencia del modelo local | Alta | Medio | Presupuesto de contexto, streaming, modelo pequeño para clasificar/resumir y grande para narrar, táctica rápida sin LLM para esbirros |
| R7 | Calidad del modelo local (herramientas, secretos, español) | Alta | **Alto** | Ollama es ahora el proveedor principal (D-10): defensas estructurales, salidas con esquema JSON, batería de pruebas de comportamiento con el modelo real antes de cada versión y requisitos de hardware documentados |
| R8 | Amplitud de las reglas de 5e | Alta | Medio | Cubrir primero el SRD; reglas no implementadas → el LLM propone y el DM confirma, con aviso explícito |
| R9 | Pantalla compartida y modo DM | Media | Medio | PIN, aviso previo, expiración, store separado; documentar el límite |
| R10 | Alcance excesivo para un proyecto personal | Alta | Alto | MVP estricto, fases con entregables verificables, registro de pendientes |
| R11 | Licencias (material no SRD, PDF comerciales) | Baja | Alto | No versionar `data/`; aventura de prueba propia; atribución SRD |
| R12 | Dependencias nativas en Windows (sqlite-vec, Tesseract) | Media | Medio | CI en Windows y Linux desde la fase 1; embeddings vía Ollama (sin PyTorch) |

## 10.4 Alcance realista del MVP

Los 15 puntos de la sección 19 del prompt maestro son alcanzables si se acotan así:

| # | Punto del MVP | Alcance acotado |
|---|---|---|
| 1 | Crear una campaña | Completo |
| 2 | Cargar un PDF | PDF con texto seleccionable (OCR fuera del MVP) |
| 3 | Procesar y consultar | Estructura, fragmentos, clasificación con revisión, búsqueda híbrida con cita de página. Extracción de entidades en modo borrador |
| 4 | Crear varios personajes | Ficha completa introducida a mano con valores derivados calculados; sin asistente de creación paso a paso |
| 5 | Registrar participantes | Completo, con selector de jugador activo |
| 6 | Iniciar sesión | Completo |
| 7 | Narrar escenarios | Completo, con solo información permitida |
| 8 | Recibir acciones | Texto libre |
| 9 | Evaluar acciones | Las cuatro categorías |
| 10 | Solicitar tiradas | Pruebas de característica, habilidad y salvación |
| 11 | Resolver tiradas | Digital y manual, ventaja/desventaja, CD oculta |
| 12 | Mantener memoria | Eventos, hechos, resumen de sesión, memoria de NPC básica |
| 13 | Mostrar mapas originales | Visor con calibración y asociación a escena; capa lógica mínima (paredes y puertas) |
| 14 | Posicionar en cuadrícula | Tokens arrastrables con coordenadas y distancia; sin validación de combate |
| 15 | Guardar y recuperar | Completo, con copia de seguridad automática |

**Fuera del MVP:** combate táctico completo, niebla de guerra con línea de visión, OCR, generación de mapas, creación guiada de personajes, multijugador por dispositivos.

No se da una estimación de plazos todavía: depende de la dedicación disponible y de cómo se comporte la extracción de PDF reales. Se propondrá una al cerrar la fase 1, con datos.
