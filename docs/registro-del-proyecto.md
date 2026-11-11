# Registro del proyecto

Registro vivo pedido en la sección 21 del prompt maestro. Se actualiza en cada PR.

## Estado actual

- **Fase:** 1 — Estructura y aplicación base (en curso).
- **Diseño:** aprobado el 2026-11-10 (respuestas en el issue #1).

## Funcionalidades terminadas

| Fecha | Funcionalidad | Verificación |
|---|---|---|
| 2026-11-10 | Documento de análisis y diseño (24 puntos) en `docs/diseno/` | Revisión de documentos |

## Funcionalidades pendientes

Ver los hitos e issues del repositorio (Fase 1 a Fase 8).

## Errores conocidos

Ninguno (no hay código).

## Decisiones arquitectónicas

| # | Decisión | Estado | Documento |
|---|---|---|---|
| D-01 | Monolito modular FastAPI + SPA React; la IA solo actúa mediante herramientas validadas | Aceptada | [02](./diseno/02-arquitectura.md) |
| D-02 | Event log inmutable + estado actual en tablas | Aceptada | [03](./diseno/03-modelo-de-datos.md) |
| D-03 | Tres niveles de conocimiento, cerrado por defecto (`dm`) | Aceptada | [03](./diseno/03-modelo-de-datos.md), [05](./diseno/05-ia-narrativa-rag-y-secretos.md) |
| D-04 | RAG propio con FTS5 + sqlite-vec, filtro de nivel dentro de la consulta | Aceptada | [05](./diseno/05-ia-narrativa-rag-y-secretos.md) |
| D-05 | Adaptador de proveedor LLM propio (Ollama y compatible con OpenAI) | Aceptada | [02](./diseno/02-arquitectura.md) |
| D-06 | Mapas: capa lógica manda; mapas generados lógica → visual | Aceptada | [07](./diseno/07-mapas.md) |
| D-07 | Solo reglas del SRD 5.1 en el repositorio | Aceptada | [08](./diseno/08-reglas-y-combate.md) |
| D-08 | Núcleo de reglas adelantado a fase 3a | Aceptada | [10](./diseno/10-pruebas-fases-riesgos-mvp.md) |
| D-09 | Visión de grupo por defecto en pantalla compartida | Propuesta (pendiente de confirmar) | [07](./diseno/07-mapas.md), [11](./diseno/11-problemas-y-preguntas-abiertas.md) |
| D-10 | Proveedor de IA: Ollama local, sin claves de API; modelo por defecto `qwen3.8:27b`, ajustable según la VRAM | Aceptada | [guía de Ollama](./guia-ollama.md) |
| D-11 | Embeddings con `qwen3-embedding` vía Ollama (sin PyTorch) | Aceptada | [02](./diseno/02-arquitectura.md) |
| D-12 | Plataformas soportadas: Windows y Linux; CI en ambas | Aceptada | [01](./diseno/01-producto-y-requisitos.md) |

## Próxima tarea

1. Fase 1, primer PR: estructura del repositorio, CI (Windows y Linux) y backend base (issues #10 y #11).
2. Pendiente de ti: memoria de la tarjeta gráfica (VRAM) para fijar el modelo por defecto.
