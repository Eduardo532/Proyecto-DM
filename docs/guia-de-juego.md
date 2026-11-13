# Guía de juego

## 1. Preparar la campaña (una vez)

1. **Crea la campaña** en la biblioteca. Pon un PIN si alguien va a preparar la aventura sin que los demás vean los secretos.
2. **Personajes → Participantes:** añade a cada jugador (Eduardo, Felipe, Juan…).
3. **Personajes:** créalos a mano (*Nuevo*) o impórtalos desde su ficha en PDF (paso 4). Las bonificaciones (habilidades, salvaciones, ataques, percepción pasiva) se calculan solas.
4. **🔒 Modo DM** (con el PIN). Que los jugadores no miren mientras está abierto.
   - **Importar:** arrastra lo que tengas, tal cual lo descargaste: el PDF de la aventura, el ZIP del pack (con sus carpetas de mapas e imágenes), las fichas de los personajes o un set de marcadores. Cada archivo se reconoce solo (ver la tabla de abajo) y verás qué se ha detectado y por qué.
   - **Fichas:** aparecen como borrador con sus características, PG, CA, competencias, ataques y conjuros. Revisa los avisos, corrige el nombre si quieres y pulsa *Crear personaje*. Después asígnale su jugador en *Personajes*.
   - **Fragmentos de la aventura:** se clasifican como *Público* (texto para leer en voz alta), *Condicionado* (se descubre con una prueba) o *Solo DM*. Revisa los importantes: ante la duda, el sistema los deja como *Solo DM*.
   - **Escenas:** se crean a partir de las áreas numeradas ("1. Entrada…", "A3. Almacén") y de los lugares con texto para leer en voz alta. Puedes editarlas o crear otras.
   - **Mapas:** los mapas importados ya llegan con la cuadrícula medida. Si un pack trae *versión DM* y *versión jugadores*, la mesa ve la de jugadores y tú puedes alternar. Si la cuadrícula no cuadra, pulsa *Detectar cuadrícula* o ajusta ancho/alto de casilla y desplazamiento. Pinta muros, puertas, terreno difícil y antorchas: el motor usa esto para el movimiento y la visión; la imagen es solo decoración.
   - **Imágenes:** las ilustraciones quedan ocultas hasta que pulses *Mostrar a la mesa*. Si algo se clasificó mal (un mapa tomado por ilustración, por ejemplo), cambia su tipo o pulsa *Crear mapa*.
   - **Criaturas y PNJ:** añade enemigos (con nombre real y nombre para la mesa, PG, CA, ataque y daño), márcalos como *ocultos* si están emboscados, y crea los PNJ con su personalidad.
   - **Secretos y memoria:** revisa los hechos con CD que se detectaron en el PDF o añade los tuyos (p. ej. "Tras el tapiz hay una palanca", Investigación CD 15).
5. Sal del modo DM.

### Qué reconoce el importador

| Tipo | Cómo lo reconoce | Qué crea |
|---|---|---|
| Aventura en PDF | Documento de texto (también a dos columnas o escaneado) | Fragmentos clasificados, escenas, hechos con CD, imágenes |
| Ficha de D&D Beyond u hoja oficial rellenable | Campos de formulario del PDF | Borrador de personaje |
| Ficha de Nivel20 (compacta o estándar) u hoja impresa | Etiquetas y posiciones del texto (español o inglés) | Borrador de personaje |
| Mapa (PNG, JPG, WebP o PDF de una página) | Nombre (*map*, *mapa*, *battlemap*, *floor*…), carpeta *Maps* o cuadrícula detectada | Mapa con cuadrícula medida |
| Versiones de un mismo mapa | *DM / Player Version*, *with / no Grid*, *with Zones*, *mapa del jugador*… | Un solo mapa con imagen para la mesa y otra para el DM |
| Ilustración | Imagen grande sin cuadrícula | Imagen oculta que puedes mostrar a la mesa |
| Token | Imagen pequeña y cuadrada con fondo transparente o en carpeta *Tokens* | Imagen de token |
| Marcadores de estado | Nombres como `3_Prone.png` o carpeta *Markers* | Iconos que se dibujan sobre los tokens con ese estado (repetidos: se usa uno) |
| ZIP | Se abre entero, también ZIP dentro de ZIP | Todo lo anterior |

## 2. Jugar una sesión

1. **Comenzar la aventura** (la primera vez): en **Mesa** pulsa el botón grande. El DM virtual presenta la historia, nombra a los personajes, os lleva a la primera escena y pregunta qué hacéis. Usa la *Presentación de la campaña* que escribas (o propongas con la IA) en **Modo DM → Ajustes**; si la IA no está disponible, lee esa presentación y el texto de la primera escena.
2. **Sesiones siguientes:** *Iniciar sesión* (arriba a la derecha) y el DM narra un "Anteriormente…". Para cambiar de escena: **Modo DM → Escenas → Activar**.
3. En **Mesa**, elige al jugador activo (o pulsa *Siguiente →*) y elige cómo interviene:
   - **🗡️ Hacer algo:** *"Examino el altar buscando mecanismos"*. El DM decide si hace falta una tirada.
   - **💬 Hablar:** *"¿Hay habitaciones libres?"*, una frase al grupo o una pregunta al DM (*"¿Qué sé de este pueblo?"*). Responde el PNJ presente o el DM, sin tiradas.
4. El DM virtual decide:
   - Si no hace falta tirada, narra el resultado.
   - Si hace falta, aparece el panel **🎲**: pulsa *Tirar dados* o escribe el resultado de tu dado físico. La CD no se muestra.
   - Con éxito, se revela lo que había (aparece en *Descubierto*); con fallo no se insinúa nada.
5. **Mapa:** selecciona la ficha de tu personaje y haz clic en la casilla de destino. Solo verás lo que ve el grupo; lo explorado queda en penumbra.
6. **Combate:** se inicia cuando una acción lo provoca (o el DM lo inicia en *Criaturas*, seleccionando participantes). En el mapa aparece el orden de iniciativa; el personaje en turno se mueve hasta su velocidad y marca sus acciones. Los enemigos actúan solos en su turno.
7. **Daño y curación** a los personajes: pestaña *Personajes*. Las tiradas de daño se hacen con *Tirada libre* (p. ej. `1d8+3`).
8. **Cerrar sesión:** se genera el resumen y queda en *Diario*.

## 3. Si algo sale mal

- **El DM virtual no responde:** comprueba el aviso amarillo (Ollama apagado o modelo sin descargar) y `docker compose logs -f ollama-init`.
- **La IA se equivocó:** en Modo DM puedes anular una tirada, corregir PG, revelar u ocultar entidades, corregir recuerdos o pausar la IA (*Ajustes*) y dirigir tú.
- **Todo lo que pasa** queda en *Modo DM → Registro*, incluidas las decisiones internas de la IA.
