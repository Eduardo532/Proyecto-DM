# Virtual Dungeon Master

Aplicación web local que usa inteligencia artificial para dirigir partidas de **Dungeons & Dragons 5e (2014)** a partir de aventuras en PDF, con un motor de reglas determinista, mapas interactivos, niebla de guerra y memoria persistente de campaña.

> **Estado:** diseño aprobado; comenzando la Fase 1. Ver [registro del proyecto](docs/registro-del-proyecto.md).

## Idea en una frase

**La IA proporciona la inteligencia narrativa. El motor de reglas garantiza la coherencia mecánica. La aplicación conecta ambas cosas.**

## Configuración inicial

| Característica | Configuración |
|---|---|
| Tipo | Aplicación web en `localhost` (Windows y Linux) |
| Modalidad | Presencial, una pantalla compartida, varios jugadores |
| Sistema | D&D 5e (2014), reglas del SRD 5.1 |
| Backend | Python + FastAPI + SQLite |
| Frontend | React + TypeScript + Tailwind + Konva |
| IA | Ollama en el propio equipo (por defecto `qwen3.5:2b`, apto para GPU de 4 GB), sin claves de API |
| Idioma | Español |

## Documentación

- [Prompt maestro](docs/prompt-maestro.md): requisitos y forma de trabajo (documento de referencia principal).
- [Especificación inicial](docs/especificacion-inicial.md): primera versión, conservada como referencia.
- Análisis y diseño:
  1. [Producto y requisitos](docs/diseno/01-producto-y-requisitos.md)
  2. [Arquitectura, tecnologías, módulos, estructura y dependencias](docs/diseno/02-arquitectura.md)
  3. [Modelo de datos](docs/diseno/03-modelo-de-datos.md)
  4. [Interfaz y flujo de una sesión](docs/diseno/04-interfaz-y-flujo-de-sesion.md)
  5. [Motor narrativo, IA, RAG y protección de secretos](docs/diseno/05-ia-narrativa-rag-y-secretos.md)
  6. [Procesamiento de PDF](docs/diseno/06-procesamiento-pdf.md)
  7. [Mapas y capas lógicas](docs/diseno/07-mapas.md)
  8. [Reglas 5e (2014) y combate](docs/diseno/08-reglas-y-combate.md)
  9. [Memoria y continuidad](docs/diseno/09-memoria.md)
  10. [Pruebas, fases, riesgos y MVP](docs/diseno/10-pruebas-fases-riesgos-mvp.md)
  11. [Problemas detectados y preguntas abiertas](docs/diseno/11-problemas-y-preguntas-abiertas.md)
- [Guía de desarrollo](docs/desarrollo.md): instalar, ejecutar y probar en Windows y Linux.
- [Guía de Ollama](docs/guia-ollama.md): qué modelo usar según tu tarjeta gráfica e instalación.
- [Registro del proyecto](docs/registro-del-proyecto.md): terminado, pendiente, errores, decisiones y próxima tarea.

## Plan

El trabajo se organiza en hitos (Fase 1 a Fase 8) e issues en este repositorio.

## Licencias y contenido

- Las aventuras en PDF que cargues se quedan en tu equipo (`data/`, excluido de Git) y no se redistribuyen.
- Las reglas incluidas proceden del System Reference Document 5.1 de Wizards of the Coast, disponible bajo licencia [Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/legalcode). Este proyecto no está afiliado a Wizards of the Coast.
