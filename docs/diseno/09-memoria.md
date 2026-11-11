# 9. Sistema de memoria y continuidad

> Cubre el punto 17 y la sección 11 del prompt maestro.

## 9.1 Capas de memoria

La memoria **no depende del historial de conversación del modelo**. Son datos estructurados en SQLite, de los que se extrae en cada turno lo relevante.

| Capa | Dónde vive | Cómo se genera | Uso |
|---|---|---|---|
| 1. Historial cronológico | `event` | Automático, por cada acción, tirada y cambio | Fuente de verdad; auditoría; reconstrucción |
| 2. Estado actual del mundo | Tablas de estado (`entity`, `character`, `quest`, `scene`, `npc`…) | Lo mantienen los motores | Contexto inmediato en cada turno |
| 3. Hechos | `fact` + `fact_awareness` | Al extraer el PDF, al revelar, al improvisar | Qué es verdad y quién lo sabe |
| 4. Memoria de campaña, personaje, NPC, misión, lugar | `memory_entry` con `scope` | Resumen por el LLM al final de escenas y sesiones; editable por el DM | Recuperación por relevancia |
| 5. Resumen de sesión | `session.summary` | Al cerrar sesión, salida estructurada validada | Reanudación |
| 6. Resumen de campaña ("la historia hasta ahora") | `memory_entry` con `scope='campaign'`, importancia alta | Se reescribe cada pocas sesiones a partir de los resúmenes de sesión | Contexto de largo plazo |

## 9.2 Resumen de sesión (esquema)

```json
{
  "acontecimientos": ["El grupo entró en la cripta por el pozo norte", "..."],
  "decisiones": [{"quien": "Lyra", "decision": "Perdonó al ghoul que hablaba", "consecuencia_potencial": "..."}],
  "personajes_presentes": ["Thorin", "Lyra", "Brom"],
  "objetos_obtenidos": [{"personaje": "Brom", "objeto": "Llave de hueso"}],
  "misiones": [{"mision": "Encontrar al heredero", "estado": "activa", "avance": "Saben que está bajo el osario"}],
  "cambios_de_estado": ["Thorin: 2 niveles de agotamiento"],
  "npc": [{"npc": "Hermana Velda", "cambio": "Ahora es hostil con Thorin"}],
  "situacion_final": "Descansando en la capilla, puerta atrancada.",
  "ganchos_abiertos": ["¿Quién dejó las velas encendidas?"]
}
```

El resumen se **valida contra el estado**: los objetos obtenidos deben existir en `inventory_entry`, los cambios de PG en `character_change`, etc. Lo que no cuadra se marca para revisión del DM en lugar de guardarse como verdad.

## 9.3 Recuperación en cada turno

1. Siempre: estado de la escena, fichas implicadas, misiones activas, resumen de campaña y de la última sesión.
2. Por relevancia (FTS + vectores sobre `memory_entry` y `fact`, con el mismo filtro de visibilidad que el RAG): recuerdos relacionados con los nombres y lugares mencionados en la acción y en la escena.
3. Para NPC: solo sus recuerdos y sus hechos conocidos.

## 9.4 Protección contra contradicciones

- Antes de narrar una afirmación sobre una entidad, el contexto incluye los hechos `true` de esa entidad.
- Se distinguen explícitamente: **hechos confirmados** (`status='true'` y conocido), **hipótesis de personajes** (`fact_awareness.confidence='suspected'` o `status='hypothesis'`), **rumores falsos** (`false_rumor`) y **secretos no descubiertos**.
- Un verificador posterior (opcional, configurable por coste) revisa la narración contra los hechos de las entidades mencionadas y marca posibles contradicciones para el DM.

## 9.5 Corrección manual

El DM puede editar o eliminar recuerdos y hechos. Nada se borra físicamente: se crea una entrada nueva que reemplaza a la anterior (`superseded_by`) y un evento `correction`, para mantener la trazabilidad.

## 9.6 Reanudación

Al iniciar una sesión:

1. Se carga el estado (instantáneo, es la base de datos).
2. Se construye un "Anteriormente en…" a partir del resumen de la última sesión, que el LLM narra en 4–6 frases.
3. Se vuelve a describir la escena actual con la información pública y descubierta.

## 9.7 Copias de seguridad

- Copia automática de `vdm.sqlite3` (API de *backup* en línea de SQLite) al cerrar sesión y antes de cada migración, en `data/backups/` con rotación (últimas 20).
- Exportación de una campaña completa a un `.zip` (base de datos filtrada + assets, sin los PDF salvo que se pida) para mover a otro equipo.
