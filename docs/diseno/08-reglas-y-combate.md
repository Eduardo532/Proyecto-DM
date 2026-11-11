# 8. Motor de reglas D&D 5e (2014) y sistema de combate

> Cubre los puntos 15 y 16, y las secciones 5.3, 5.4, 8 y 17 del prompt maestro.

## 8.1 Alcance y licencia

- Reglas de **D&D 5e 2014** según el **SRD 5.1** (CC-BY-4.0). No se mezclan reglas de 2024.
- El SRD 5.1 incluye las reglas básicas, 9 razas, 12 clases con una subclase cada una, una parte de conjuros, objetos mágicos y criaturas. Lo que no está en el SRD (otras subclases, conjuros, dotes del PHB) **no se incluye en el repositorio**; el usuario puede introducirlo como datos propios de su campaña o desde sus PDF, que se quedan en su equipo.
- Se incluirá el aviso de atribución del SRD en el README y en la aplicación.

## 8.2 Interfaz de sistema de juego

Para poder añadir otros sistemas (RNF-15), las reglas se acceden a través de una interfaz:

```text
GameSystem
  ability_modifier(score) -> int
  proficiency_bonus(level) -> int
  skill_ability(skill) -> ability
  check(actor, kind, target, adv, situational) -> CheckSpec
  resolve(spec, dice_result) -> Outcome
  apply_damage(target, amount, type, is_critical) -> DamageResult
  conditions() -> catálogo
  ...
```

`dnd5e_2014` es la primera implementación.

## 8.3 Jerarquía de reglas configurable

Orden de prioridad por defecto (configurable por campaña):

1. Decisión explícita del DM en la sesión (evento de corrección).
2. Reglas especiales de la aventura (extraídas del PDF y confirmadas).
3. Reglas caseras de la campaña.
4. Reglas opcionales activadas (p. ej. diagonales 5/10, flanqueo, cobertura por esquinas).
5. Reglas base 5e 2014.

Cada regla configurable es un interruptor con nombre (`optional.flanking`, `optional.diagonal_5_10`), para que el motor y el LLM lean la misma configuración.

## 8.4 Dados

- Expresiones: `NdX`, `NdX+M`, `NdXkhK` (conservar las K mayores), `NdXklK`, suma de varias (`1d8+2d6+3`).
- Dados: d4, d6, d8, d10, d12, d20, d100 (como dos d10 o un d100, configurable en la presentación).
- Aleatoriedad: `secrets.SystemRandom` en el servidor (criptográficamente segura). Para pruebas, una semilla inyectable.
- Modo manual: el jugador introduce cada valor; el motor valida rango y número de dados y calcula el total con los modificadores de la ficha.
- Ventaja/desventaja: dos d20, conservar el mayor/menor; si coexisten fuentes de ambas, se anulan (regla 2014: una sola fuente de cada basta para anular, sin acumular).
- Críticos: 20 natural en ataque = crítico (doble de dados de daño); 1 natural = fallo automático. En pruebas de característica y salvaciones, el 20/1 natural no tiene efecto especial en 5e 2014 (salvo salvaciones contra muerte).
- Cada tirada queda en `dice_roll` con todos los dados, los conservados y el desglose: `d20 (14) + DES 3 + competencia 2 = 19`.

## 8.5 Pruebas y CD

- Prueba = d20 + modificador de característica + (competencia, si aplica; doble con pericia; mitad con Polivalente del bardo) + bonificadores situacionales.
- CD orientativas 5e: muy fácil 5, fácil 10, media 15, difícil 20, muy difícil 25, casi imposible 30. Si el PDF indica una CD, prevalece.
- Pruebas pasivas: 10 + modificadores (±5 por ventaja/desventaja).
- Pruebas enfrentadas, de grupo (éxito si al menos la mitad supera la CD) y ayuda (ventaja).
- La CD se guarda en la tirada con `dc_visible`; la interfaz de jugadores solo la recibe si es visible.

### Revelación por niveles

Los hechos condicionados pueden tener niveles de descubrimiento definidos **por la escena**, no universales:

```json
{"skill": "investigation", "tiers": [
  {"min": 10, "fact": "F-30"},   // un libro fuera de lugar
  {"min": 15, "fact": "F-31"},   // inscripción oculta
  {"min": 20, "fact": "F-32"}    // nombre del autor real
]}
```

Fallar no revela que existía algo que encontrar: la narración de un fallo y la de "no hay nada" son indistinguibles.

## 8.6 Fichas y recursos

El gestor de personajes calcula los valores derivados (no se guardan duplicados): modificadores, bonificador de competencia por nivel total, habilidades, salvaciones, CA según armadura equipada y rasgos, iniciativa, percepción pasiva, CD de conjuros y bonificador de ataque de conjuros, capacidad de carga.

Operaciones validadas (cada una genera evento + `character_change`): recibir daño, curar, PG temporales (no se acumulan, se elige el mayor), gastar/recuperar espacios de conjuro, dados de golpe, descanso corto y largo, condiciones, equipar, sintonizar (máx. 3), objetos y monedas, experiencia y subida de nivel (tabla de PX de 2014).

## 8.7 Combate

### Inicio

1. `iniciar_encuentro` crea `combatant` para cada entidad implicada que no esté ya en combate.
2. Sorpresa: los personajes que no perciben a ningún enemigo al inicio están sorprendidos el primer asalto (se compara Sigilo de los ocultos con Percepción pasiva).
3. Iniciativa: d20 + DES (+ rasgos). Los enemigos del mismo tipo pueden tirar en grupo (configurable). Empates: mayor DES; si persiste, decide el DM/aleatorio.
4. La interfaz cambia a vista de combate.

### Turno

Estado por combatiente: `has_action`, `has_bonus_action`, `has_reaction`, `movement_left_ft`. El motor valida:

- Movimiento: camino válido y coste ≤ restante; se puede dividir antes y después de la acción.
- Acciones estándar: Atacar (con Ataque Extra), Lanzar conjuro, Correr (Dash), Retirarse, Esquivar, Ayudar, Esconderse, Preparar, Buscar, Usar objeto.
- Acción adicional solo si un rasgo o conjuro la concede.
- Regla de conjuros 2014: si se lanza un conjuro con acción adicional, el otro conjuro del turno solo puede ser un truco de 1 acción.
- Reacción: una por asalto (ataque de oportunidad, conjuros de reacción, acción preparada).

### Ataque y daño

1. Comprobar alcance (cuerpo a cuerpo/distancia; distancia larga = desventaja; atacar a distancia con un hostil adyacente = desventaja).
2. Tirada de ataque contra CA (+ cobertura).
3. Daño por tipo, con resistencia (½, redondeando abajo), vulnerabilidad (×2) e inmunidad (0), aplicados tras sumar todo el daño de ese tipo.
4. PG temporales absorben primero.
5. Concentración: al recibir daño, salvación de CON con CD = máx(10, ½ daño).

### 0 puntos de golpe

- Daño masivo: si el daño restante tras llegar a 0 ≥ PG máximos, muerte instantánea.
- Si no, inconsciente y salvaciones contra muerte: ≥10 éxito, <10 fallo, 1 natural = dos fallos, 20 natural = recupera 1 PG. Tres éxitos = estable; tres fallos = muerte.
- Recibir daño a 0 PG = un fallo (dos si es crítico).
- Estabilizar: Medicina CD 10 o efecto equivalente. Estable recupera 1 PG en 1d4 horas.
- Las criaturas genéricas mueren al llegar a 0 salvo que el DM decida otra cosa (regla 2014 opcional para PNJ importantes).

### Condiciones

Las 14 condiciones de 5e 2014 más el agotamiento (6 niveles), con efectos aplicados por el motor (p. ej. *derribado*: ventaja de ataques cuerpo a cuerpo adyacentes contra él, desventaja a distancia, se levanta con la mitad del movimiento). Duraciones por asaltos, fin de turno o salvación repetida.

### Inteligencia de los enemigos

El LLM decide **qué quiere hacer** cada enemigo; el motor dice **qué puede hacer**.

1. El motor genera la lista de opciones legales del enemigo (objetivos en alcance, movimientos posibles, conjuros con espacios disponibles, cobertura cercana).
2. El LLM recibe esas opciones + perfil del enemigo (INT, personalidad, objetivos, moral, estado de salud, lo que sabe) y elige una, con motivo breve.
3. El motor ejecuta y narra el resultado mecánico; el LLM lo describe.

Perfiles de comportamiento como guía: *instintivo* (INT ≤ 4: ataca al más cercano o al que le hizo daño, huye con poca vida), *astuto* (busca cobertura, concentra fuego en conjuradores), *disciplinado* (formación, protege al líder), *cobarde* (negocia o huye por debajo de la mitad de PG). Moral configurable: huida o rendición al caer el líder o la mitad del grupo.

Para enemigos menores (decenas de esbirros), un modo "táctica rápida" sin LLM, con reglas simples deterministas, para reducir latencia y coste.

### Información visible durante el combate

Jugadores: nombre público, tamaño, posición, estado aparente por umbrales de PG (100 %, >50 %, >25 %, >0), condiciones visibles y acciones observadas. Resistencias, CA y PG exactos solo si se descubren (p. ej. un ataque que "no parece hacerle tanto daño" revela la resistencia como hecho). DM: todo.
