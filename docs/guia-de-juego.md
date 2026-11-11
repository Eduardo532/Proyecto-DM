# Guía de juego

## 1. Preparar la campaña (una vez)

1. **Crea la campaña** en la biblioteca. Pon un PIN si alguien va a preparar la aventura sin que los demás vean los secretos.
2. **Personajes → Participantes:** añade a cada jugador (Eduardo, Felipe, Juan…).
3. **Personajes → Nuevo:** crea cada personaje y asígnale su participante. Las bonificaciones (habilidades, salvaciones, ataques, percepción pasiva) se calculan solas.
4. **🔒 Modo DM** (con el PIN). Que los jugadores no miren mientras está abierto.
   - **Documentos:** sube el PDF de la aventura. Al terminar verás fragmentos clasificados como *Público* (texto para leer en voz alta), *Condicionado* (se descubre con una prueba) o *Solo DM*. Revisa los importantes: ante la duda, el sistema los deja como *Solo DM*.
   - **Escenas:** se crean a partir de las áreas numeradas del PDF ("1. Entrada…"). Puedes editarlas o crear otras. Cada escena tiene una descripción para la mesa y notas del DM.
   - **Documentos → Imágenes:** en las que sean mapas, pulsa *Crear mapa* e indica el tamaño de la casilla en píxeles.
   - **Mapas:** ajusta la calibración hasta que la cuadrícula coincida con el dibujo y pinta muros, puertas, terreno difícil y antorchas. El motor usa esto para el movimiento y la visión; la imagen es solo decoración.
   - **Criaturas y PNJ:** añade enemigos (con nombre real y nombre para la mesa, PG, CA, ataque y daño), márcalos como *ocultos* si están emboscados, y crea los PNJ con su personalidad.
   - **Secretos y memoria:** revisa los hechos con CD que se detectaron en el PDF o añade los tuyos (p. ej. "Tras el tapiz hay una palanca", Investigación CD 15).
5. Sal del modo DM.

## 2. Jugar una sesión

1. **Iniciar sesión** (arriba a la derecha). Si hubo una sesión anterior, el DM virtual narra un "Anteriormente…".
2. En **Modo DM → Escenas**, pulsa **Activar** en la escena inicial: el DM virtual la describe.
3. En **Mesa**, elige al jugador activo (o pulsa *Siguiente →*) y escribe lo que hace su personaje, por ejemplo: *"Examino el altar buscando mecanismos"*.
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
