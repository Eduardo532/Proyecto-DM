# Registro del proyecto

Registro vivo pedido en la sección 21 del prompt maestro. Se actualiza en cada PR.

## Estado actual

- **Fase:** 0 — Análisis y diseño (entregado, pendiente de tu revisión).
- **Código:** ninguno todavía, a propósito (sección 22: "no generes código hasta que el análisis y la arquitectura estén definidos").

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
| D-01 | Monolito modular FastAPI + SPA React; la IA solo actúa mediante herramientas validadas | Propuesta | [02](./diseno/02-arquitectura.md) |
| D-02 | Event log inmutable + estado actual en tablas | Propuesta | [03](./diseno/03-modelo-de-datos.md) |
| D-03 | Tres niveles de conocimiento, cerrado por defecto (`dm`) | Propuesta | [03](./diseno/03-modelo-de-datos.md), [05](./diseno/05-ia-narrativa-rag-y-secretos.md) |
| D-04 | RAG propio con FTS5 + sqlite-vec, filtro de nivel dentro de la consulta | Propuesta | [05](./diseno/05-ia-narrativa-rag-y-secretos.md) |
| D-05 | Adaptador de proveedor LLM propio (Anthropic, OpenAI, Ollama) | Propuesta | [02](./diseno/02-arquitectura.md) |
| D-06 | Mapas: capa lógica manda; mapas generados lógica → visual | Propuesta | [07](./diseno/07-mapas.md) |
| D-07 | Solo reglas del SRD 5.1 en el repositorio | Propuesta | [08](./diseno/08-reglas-y-combate.md) |
| D-08 | Núcleo de reglas adelantado a fase 3a | Propuesta | [10](./diseno/10-pruebas-fases-riesgos-mvp.md) |
| D-09 | Visión de grupo por defecto en pantalla compartida | Propuesta | [07](./diseno/07-mapas.md), [11](./diseno/11-problemas-y-preguntas-abiertas.md) |

## Próxima tarea

1. Que respondas las preguntas ★ de [11-problemas-y-preguntas-abiertas.md](./diseno/11-problemas-y-preguntas-abiertas.md).
2. Con eso, cerrar las decisiones D-01 a D-09 y comenzar la **Fase 1**: estructura del repositorio, backend y frontend base, CI.
