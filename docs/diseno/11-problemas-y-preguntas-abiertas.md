# 11. Problemas detectados y preguntas abiertas

> Responde a la petición de la sección 22: "Identifica también posibles problemas, contradicciones o requisitos que necesiten mayor definición" y "plantea preguntas concretas antes de asumirlas".

## 11.1 Contradicciones y tensiones en los requisitos

| # | Tensión | Propuesta |
|---|---|---|
| C1 | **Pantalla compartida vs. información privada por personaje.** La especificación pide visibilidad individual y que cada jugador vea solo lo que percibe su personaje, pero todos miran la misma pantalla. | Por defecto, **visión de grupo** (unión de lo que perciben los personajes). La visión individual queda como opción. La información estrictamente privada (lo que solo ve un personaje) se muestra con un aviso "solo para Felipe" que requiere confirmar antes de enseñarse. |
| C2 | **DM de IA vs. panel privado del DM.** Si todos juegan, ¿quién abre el panel del DM sin destriparse la aventura? | El panel se usa para **preparar** (revisar el PDF, clasificar secretos, calibrar mapas) y para **corregir** errores. Recomiendo designar a una persona como "organizador" que acepte ver spoilers, o usar el panel solo antes de empezar. |
| C3 | **Orden de fases.** La fase 3 (IA) necesita dados y pruebas, que están en la fase 4. | Adelantar el núcleo de reglas como fase 3a (ver 10.2). |
| C4 | **"Mapas generados mediante IA"** puede entenderse como generación de imágenes. Una imagen generada no da una capa lógica fiable. | Generar primero la capa lógica (estructurada y validada) y dibujar a partir de ella (ver 7.3). |
| C5 | **Detección automática de paredes en mapas del PDF** no es fiable con la tecnología actual. | MVP con editor manual rápido; detección automática como borrador posterior. |
| C6 | **"La IA no debe inventar tiradas"** vs. **tiradas físicas**: con dados físicos el sistema confía en lo que se introduce. | Correcto para juego presencial; se registra como `manual` y no se modifica. |
| C7 | **Funcionar sin Internet** vs. **LLM en la nube**. | Todo lo no narrativo funciona sin conexión; la narración requiere el proveedor o Ollama. Se indica en la interfaz cuando no hay proveedor disponible. |
| C8 | **Reglas 2014 completas vs. licencia.** El SRD 5.1 no contiene todo el PHB. | Incluir solo SRD; el resto lo aporta el usuario como datos locales. |
| C9 | La primera especificación (`especificacion-inicial.md`) pedía multijugador online y la sección 13 hablaba de un DM humano interviniendo. | Prevalece el prompt maestro: local y compartido, arquitectura preparada para multijugador (UUID, eventos, proyecciones por destinatario). |

## 11.2 Preguntas que necesito que respondas antes de la fase 1

Las marcadas con ★ bloquean el inicio; el resto pueden responderse durante la fase 1.

1. ★ **Sistema operativo** del equipo donde se ejecutará (Windows, macOS, Linux). Determina los comandos de instalación y las pruebas de dependencias nativas.
2. ★ **Proveedor de IA** para el desarrollo: ¿Anthropic (Claude), OpenAI, Ollama local, u otro? ¿Tienes ya una clave de API? ¿Hay un presupuesto mensual orientativo?
3. ★ **¿Aceptas los añadidos tecnológicos** (Alembic, Zustand + TanStack Query, sqlite-vec, Hypothesis, Playwright) y el **RAG propio** en lugar de LlamaIndex?
4. ★ **¿Aceptas el cambio de orden** de fases (núcleo de reglas antes del motor narrativo)?
5. **Modo DM en la mesa:** ¿habrá una persona que haga de organizador y pueda ver spoilers, o el panel del DM será solo de preparación?
6. **Visión en pantalla compartida:** ¿visión de grupo por defecto (recomendado) o individual?
7. **Idioma de los PDF:** ¿las aventuras estarán en español, en inglés o en ambos? Afecta al OCR, al parser de bloques de estadísticas y al glosario (p. ej. "Clase de Armadura" / "Armor Class").
8. **Terminología en español:** ¿prefieres la terminología de la traducción oficial española de 5e (p. ej. "puntos de golpe", "tirada de salvación", "acción adicional") o alguna otra variante?
9. **Importación de fichas:** ¿necesitas importar personajes desde algún formato concreto (D&D Beyond, PDF de ficha rellenable, Foundry, otro) o basta con crearlos en la aplicación?
10. **Dados:** ¿modo por defecto digital, manual o preguntar en cada tirada?
11. **PG de enemigos visibles:** ¿estado aparente por umbrales (recomendado) o PG exactos?
12. **Gestión del repositorio:** ¿trabajo con ramas y PR que tú revisas y fusionas (recomendado), o fusiono yo directamente a `main` cuando las pruebas pasen?

## 11.3 Requisitos que necesitarán más definición más adelante

- Lista concreta de reglas caseras habituales en tu mesa.
- Nivel de detalle de narración preferido (párrafos cortos vs. descripciones largas).
- Si se quiere voz (lectura en voz alta de la narración) en el futuro: afecta a la elección de proveedor.
- Qué hacer con contenido sensible en las aventuras (violencia explícita, temas adultos): ¿ajustes de tono por campaña?
