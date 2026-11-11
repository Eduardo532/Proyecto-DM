# 7. Sistema de mapas y capas lógicas

> Cubre el punto 14 y la sección 7 del prompt maestro.

## 7.1 Dos capas por mapa

| Capa | Qué es | Quién la usa |
|---|---|---|
| **Visual** | Imagen de fondo (del PDF o generada), más decoración | Solo la interfaz, para pintar |
| **Lógica** | Matriz de casillas con terreno, paredes, puertas, cobertura, luz, trampas y zonas (`map_tile` + `map_feature`) | El motor: movimiento, visión, alcance, colisiones |

El motor **nunca** consulta la imagen. Si la capa lógica no está definida para una zona, esa zona se trata como suelo transitable con aviso en el panel del DM. Esto cumple el requisito de no validar movimientos con interpretación visual de una IA.

## 7.2 Mapas del PDF

1. El procesamiento marca imágenes candidatas (ver 6.2).
2. En modo DM, el usuario confirma cuáles son mapas y las asocia a escenas.
3. **Calibración de cuadrícula:** el usuario marca dos esquinas de una casilla (o arrastra una cuadrícula superpuesta hasta que encaje) y la escala (por defecto 1 casilla = 5 pies). Se guardan `grid_offset_px` y `cell_size_px`. La imagen original no se modifica.
4. **Capa lógica:**
   - MVP: editor manual con pinceles (pared, puerta, terreno difícil, obstáculo, zona) sobre la imagen calibrada. Herramienta de "rellenar sala" y "trazar pared" para hacerlo rápido.
   - Más adelante: propuesta automática (detección de paredes por contraste/bordes con OpenCV y/o un modelo con visión) que el usuario corrige. Siempre como borrador.
5. Los mapas que muestran toda la mazmorra no se enseñan completos: la vista de jugadores solo recibe las casillas exploradas/visibles.

## 7.3 Mapas generados

El orden es el inverso al de un generador de imágenes: **primero la lógica, después la imagen**.

1. El LLM lee la descripción de la escena (y del PDF si existe) y produce una **especificación estructurada** validada por esquema: salas con dimensiones en pies, conexiones, puertas, obstáculos, iluminación, puntos de interés.
2. Un **generador procedural determinista** coloca las salas en la cuadrícula respetando dimensiones y conexiones, y produce la capa lógica.
3. La capa visual se dibuja a partir de la lógica con un conjunto de texturas (piedra, madera, tierra, agua) en el propio cliente. En fase 8 puede añadirse un modelo de generación de imágenes para "embellecer", pero la lógica sigue mandando.
4. El usuario revisa y edita en el mismo editor antes de usarlo.

Esto garantiza que lo que se ve coincide con lo que el motor considera pared o puerta.

## 7.4 Motor de mapas

Funciones puras (sin base de datos), probadas con casos fijos y por propiedades:

| Función | Regla |
|---|---|
| Distancia | 5e 2014 por defecto: cada casilla, incluida la diagonal, cuesta 5 pies. Variante opcional DMG: diagonales alternas 5/10 |
| Movimiento | Dijkstra con coste por casilla; terreno difícil ×2; paredes y casillas ocupadas por hostiles bloquean; se puede atravesar a aliados pero no terminar en su casilla; criaturas dos tamaños mayores/menores se pueden atravesar (regla 5e) |
| Área alcanzable | Conjunto de casillas con coste ≤ movimiento restante, para pintarlo |
| Ataques de oportunidad | Al salir del alcance de un hostil que tenga reacción, salvo Retirada |
| Línea de visión | Trazado entre centros de casilla (y esquinas para cobertura) contra casillas y puertas que bloquean la vista |
| Cobertura | 5e: media (+2 CA), tres cuartos (+5), total; calculada por esquinas según la variante del DMG |
| Iluminación | Por casilla: brillante, tenue, oscuridad; fuentes de luz con radio brillante y tenue (antorcha 20/20, etc.) |
| Visión | Normal; visión en la oscuridad (oscuridad → tenue, tenue → brillante a efectos de ver, sin color); vista ciega; condición cegado |
| Áreas de efecto | Cono, cubo, cilindro, línea, esfera según las plantillas del PHB/SRD sobre cuadrícula |

## 7.5 Niebla de guerra

Tres estados por casilla y por observador:

- **Visible ahora:** dentro de la visión de al menos un personaje (o del observador concreto).
- **Explorada:** vista alguna vez; se muestra el terreno pero no las entidades actuales.
- **Desconocida:** negro.

Configuración por campaña:

- **Visión de grupo** (por defecto en pantalla compartida): la pantalla muestra la unión de lo que ven todos los personajes. Es lo coherente con una sola pantalla.
- **Visión individual:** al seleccionar un personaje, se muestra solo lo suyo. Útil si el grupo quiere más inmersión.

Se recalcula en el backend al mover un token, abrir una puerta o cambiar la luz, y se envía como diff. Las entidades se incluyen en la proyección solo si su `perception_state` para algún personaje es `visible` (o `detected`, mostrando un marcador impreciso sin posición exacta).

## 7.6 Rendimiento

Mapa típico 40×40 = 1 600 casillas. Visión por personaje con recorrido de sombras (*shadowcasting*) es O(casillas en radio); con 6 personajes y radio 12 casillas está muy por debajo de 10 ms en Python. Si hiciera falta, la función se puede vectorizar con NumPy sin cambiar su interfaz.
