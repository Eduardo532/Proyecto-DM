# Proyecto: Desarrollo de un Dungeon Master Virtual con Inteligencia Artificial

> Primera versión de la especificación, conservada como referencia. **Cuando difiera del [prompt maestro](./prompt-maestro.md), prevalece el prompt maestro** (por ejemplo: modalidad local de pantalla compartida, SQLite, D&D 5e 2014). La sección 16 llegó incompleta.

## 1. VISIÓN Y OBJETIVO DEL PROYECTO

Desarrollar una aplicación web completa que utilice inteligencia artificial para actuar como un Dungeon Master (DM) profesional de juegos de rol de mesa, principalmente Dungeons & Dragons (D&D).

La aplicación debe permitir cargar campañas y aventuras en formato PDF para que la IA pueda interpretarlas, dirigirlas y convertirlas en experiencias de juego interactivas.

El sistema debe ser capaz de dirigir una partida completa sin necesidad de un Dungeon Master humano, encargándose de:

- Narrar escenarios y acontecimientos.
- Interpretar personajes no jugadores (NPC).
- Gestionar diálogos y decisiones.
- Evaluar las acciones de los jugadores.
- Determinar cuándo se necesitan tiradas de dados.
- Aplicar las reglas del sistema de juego.
- Gestionar combates y enemigos.
- Mostrar mapas interactivos.
- Controlar la visibilidad del escenario.
- Administrar fichas de personajes.
- Gestionar inventarios, habilidades y recursos.
- Recordar acontecimientos y decisiones.
- Mantener la coherencia de toda la campaña.
- Adaptar la historia a las decisiones de los jugadores.

La experiencia debe sentirse como jugar una campaña presencial con un Dungeon Master humano experimentado.

La IA debe tener libertad para improvisar cuando sea necesario, pero siempre respetando las reglas, el contexto, la lógica del mundo y el material original de la campaña.

## 2. SISTEMA DE CARGA Y PROCESAMIENTO DE CAMPAÑAS

La aplicación debe permitir cargar campañas y aventuras en formato PDF.

El sistema debe analizar los documentos y extraer toda la información necesaria para dirigir la aventura.

### 2.1 Procesamiento de documentos

Debe poder procesar:

- PDF con texto seleccionable.
- PDF escaneados mediante OCR.
- Documentos con imágenes.
- Mapas incluidos en las campañas.
- Tablas de estadísticas.
- Fichas de monstruos.
- Ilustraciones de personajes.
- Diagramas y planos.
- Notas y anexos.

Debe conservar las relaciones entre capítulos, habitaciones, encuentros y acontecimientos.

### 2.2 Interpretación de campañas

La IA debe identificar y organizar:

- Historia principal.
- Historias secundarias.
- Misiones.
- Escenarios.
- Habitaciones.
- NPC.
- Enemigos.
- Objetos.
- Trampas.
- Acertijos.
- Encuentros.
- Eventos desencadenantes.
- Mapas.
- Secretos.
- Descripciones.
- Reglas especiales.

La información debe almacenarse de manera estructurada para poder consultarse durante la partida.

### 2.3 Clasificación de información

La IA debe mantener tres niveles de conocimiento:

Información pública: datos que los personajes pueden percibir o conocer.

Información oculta: trampas, enemigos escondidos, puertas secretas, pistas y acontecimientos todavía no descubiertos.

Información exclusiva del DM: soluciones, estadísticas completas, secretos de NPC, desenlaces previstos y notas del autor.

Esta separación debe mantenerse tanto en la interfaz como en el backend.

Los jugadores nunca deben poder acceder a la información exclusiva del DM, ni siquiera mediante consultas manipuladas a la IA.

### 2.4 Improvisación controlada

Si los jugadores hacen algo que no está contemplado en el PDF, la IA debe poder improvisar.

Sin embargo, debe:

- Respetar la ambientación.
- Mantener la coherencia histórica y geográfica.
- Respetar las motivaciones de los NPC.
- No contradecir acontecimientos establecidos.
- No revelar información futura.
- No modificar arbitrariamente las reglas.

La improvisación debe complementar la campaña, no reemplazarla.

## 3. DUNGEON MASTER VIRTUAL

La IA debe actuar como un DM experimentado, narrador, árbitro de reglas y director de la aventura.

### 3.1 Narración

Al entrar en una nueva escena, debe describir:

- El entorno.
- La iluminación.
- Los sonidos.
- Los olores relevantes.
- La temperatura.
- Los elementos visibles.
- Los NPC presentes.
- Las amenazas perceptibles.
- Los objetos con los que se puede interactuar.

Debe utilizar una narración inmersiva sin revelar información que los personajes todavía no conocen.

Después de describir la situación, debe detenerse y esperar las decisiones de los jugadores.

No debe continuar desarrollando acciones de los personajes sin su autorización.

### 3.2 Acciones libres

Los jugadores deben poder escribir cualquier acción, sin limitarse a opciones predefinidas.

Ejemplos:

- Examinar una habitación.
- Hablar con un NPC.
- Intentar convencer a un guardia.
- Escalar una pared.
- Buscar trampas.
- Romper una puerta.
- Investigar un objeto.
- Preparar una emboscada.
- Interactuar con elementos del mapa.

La IA debe interpretar la intención, evaluar su viabilidad y determinar las consecuencias.

### 3.3 Evaluación de acciones

Para cada acción debe determinar internamente:

- Qué intenta conseguir el jugador.
- Si la acción es posible.
- Si requiere una tirada.
- Qué habilidad o característica corresponde.
- Qué dificultad tiene.
- Si existe ventaja o desventaja.
- Qué consecuencias puede producir.
- Si intervienen factores externos.

La IA no debe revelar la dificultad numérica antes de una tirada cuando esta sea información reservada.

Debe comunicar al jugador qué tipo de prueba debe realizar y esperar el resultado.

Las acciones sencillas y garantizadas no deben requerir tiradas innecesarias.

Las acciones imposibles bajo las circunstancias actuales deben explicarse narrativamente.

## 4. SISTEMA DE DADOS

Implementar un motor de dados que soporte las reglas de la edición seleccionada.

Debe incluir:

- d4, d6, d8, d10, d12, d20 y d100.
- Tiradas múltiples.
- Tiradas de característica.
- Pruebas de habilidad.
- Tiradas de salvación.
- Ataques.
- Daño.
- Iniciativa.
- Ventaja y desventaja.
- Tiradas enfrentadas.
- Salvaciones contra muerte.
- Tiradas especiales.

#### Modalidad manual

Los jugadores pueden lanzar dados físicos e introducir sus resultados.

#### Modalidad digital

La aplicación debe disponer de dados virtuales con resultados generados mediante un sistema aleatorio fiable.

#### Control de resultados

La IA no debe inventar tiradas.

Debe distinguir entre:

- Tiradas pendientes.
- Tiradas realizadas.
- Tiradas fallidas.
- Tiradas exitosas.
- Tiradas anuladas o repetidas conforme a las reglas.

Debe calcular automáticamente los modificadores de las fichas de personaje.

Debe mostrar el resultado, los modificadores y el total.

Los resultados digitales deben quedar registrados para mantener la trazabilidad de la partida.

## 5. FICHAS DE PERSONAJES COMPLETAS

Cada jugador debe disponer de una ficha de personaje digital.

La ficha debe incluir:

- Nombre.
- Raza o especie.
- Clase.
- Subclase.
- Nivel.
- Trasfondo.
- Alineamiento, cuando se utilice.
- Características.
- Modificadores.
- Competencias.
- Habilidades.
- Tiradas de salvación.
- Puntos de vida.
- Puntos de vida temporales.
- Clase de armadura.
- Velocidad.
- Iniciativa.
- Ataques.
- Hechizos.
- Espacios de conjuro.
- Rasgos.
- Dotes.
- Inventario.
- Equipo.
- Monedas.
- Condiciones.
- Experiencia.

#### Sincronización automática

La ficha debe actualizarse cuando suceda algo en la partida.

Ejemplos:

- Recibir daño.
- Recuperar vida.
- Consumir una poción.
- Obtener un objeto.
- Equipar un arma.
- Gastar un espacio de conjuro.
- Ganar experiencia.
- Subir de nivel.
- Obtener una condición.
- Perder un objeto.

Los cambios deben realizarse mediante operaciones controladas y verificables, no únicamente mediante texto generado por la IA.

La aplicación debe conservar el historial de modificaciones.

## 6. SISTEMA DE MAPAS INTERACTIVOS

Esta es una de las funcionalidades centrales del proyecto.

La aplicación debe disponer de un motor de mapas que permita representar escenarios de exploración y combate.

### 6.1 Mapas originales de las campañas

Cuando un PDF contenga mapas, la aplicación debe extraerlos y permitir utilizarlos directamente.

Debe identificar, cuando sea posible:

- Habitaciones.
- Pasillos.
- Puertas.
- Escaleras.
- Paredes.
- Obstáculos.
- Zonas especiales.
- Elementos importantes.
- Escala del mapa.
- Distribución espacial.

Debe permitir superponer una cuadrícula sobre los mapas originales sin modificar la imagen de fondo.

También debe permitir calibrar la escala para que cada casilla corresponda a la distancia definida por las reglas.

### 6.2 Mapas generados

Cuando no exista un mapa en el documento, el sistema debe permitir:

- Crear mapas mediante generación procedural.
- Generar mapas a partir de descripciones de habitaciones.
- Diseñar mapas manualmente.
- Colocar obstáculos.
- Crear habitaciones y pasillos.
- Colocar puertas y escaleras.
- Añadir objetos interactivos.
- Guardar mapas para reutilizarlos.

Los mapas generados deben respetar las descripciones y dimensiones establecidas en la campaña.

### 6.3 Cuadrícula de coordenadas

Cada mapa debe tener una cuadrícula identificable mediante filas y columnas.

Debe permitir representar:

- Posición de jugadores.
- Posición de enemigos.
- NPC.
- Objetos.
- Obstáculos.
- Puertas.
- Trampas.
- Elementos del entorno.

Las entidades deben estar vinculadas a coordenadas reales dentro del mapa.

El sistema debe calcular distancias, movimiento, alcance y adyacencia según las reglas seleccionadas.

### 6.4 Elementos interactivos

Los elementos del escenario deben poder seleccionarse.

Por ejemplo, un jugador puede seleccionar una puerta y escribir:

- "Quiero intentar abrirla sin hacer ruido".

La IA debe reconocer el elemento seleccionado, consultar su estado y evaluar la acción.

Los elementos pueden tener propiedades como:

- Nombre.
- Tipo.
- Posición.
- Estado.
- Visibilidad.
- Interacciones disponibles.
- Resistencia.
- Información secreta.
- Consecuencias de interacción.

## 7. NIEBLA DE GUERRA Y VISIBILIDAD INTELIGENTE

Implementar un sistema avanzado de Fog of War.

El mapa no debe mostrar toda la información a los jugadores.

Debe existir una diferencia entre:

- Zonas visibles actualmente.
- Zonas exploradas anteriormente.
- Zonas desconocidas.

### 7.1 Visibilidad individual

La visibilidad debe calcularse según:

- Posición del personaje.
- Distancia.
- Iluminación.
- Obstáculos.
- Paredes.
- Puertas.
- Visión normal.
- Visión en la oscuridad.
- Sentidos especiales.
- Habilidades.
- Condiciones del personaje.
- Cada jugador puede tener un campo de visión diferente.

### 7.2 Entidades ocultas

Los enemigos no deben aparecer en el mapa hasta que sean descubiertos o perceptibles.

La aplicación debe diferenciar:

- Enemigos visibles.
- Enemigos detectados, pero cuya posición exacta no se conoce.
- Enemigos ocultos.
- Enemigos fuera de visión.

Los jugadores no deben conocer las posiciones de enemigos ocultos.

### 7.3 Sincronización de visibilidad

Cada jugador debe visualizar únicamente la información que su personaje puede percibir.

El DM debe disponer de una vista completa del escenario.

La niebla de guerra debe ser aplicada desde el backend, no simplemente ocultando elementos en el frontend.

## 8. EXPLORACIÓN E INVESTIGACIÓN

La IA debe administrar las pruebas de percepción, investigación, perspicacia y otras habilidades.

Debe evaluar:

- Qué busca el jugador.
- Dónde busca.
- Qué habilidad corresponde.
- Si el elemento es detectable.
- Qué dificultad tiene.
- Qué información puede descubrir.
- Si existen pistas adicionales.

#### Revelación progresiva

Implementar un sistema de descubrimiento por niveles.

Ejemplo:

- Un jugador investiga una biblioteca.
- Resultado insuficiente: no encuentra nada relevante.
- Resultado suficiente: encuentra un libro extraño.
- Resultado superior: descubre una inscripción oculta.

Resultado excepcional, cuando corresponda: encuentra información adicional.

Estos niveles no deben ser universales ni alterar las reglas de la campaña. Deben depender de las características reales del escenario y de las pruebas establecidas.

La IA debe registrar qué información ha descubierto cada personaje y qué información es conocida por todo el grupo.

Nunca debe revelar la existencia de un secreto por el simple hecho de que el jugador haya fallado una prueba.

## 9. SISTEMA DE COMBATE TÁCTICO

Cuando comience un combate, la aplicación debe cambiar automáticamente a la interfaz táctica.

Debe incluir:

- Mapa de combate.
- Cuadrícula.
- Tokens de personajes.
- Tokens de enemigos.
- NPC aliados.
- Obstáculos.
- Cobertura.
- Terreno difícil.
- Zonas peligrosas.
- Iniciativa.
- Orden de turnos.
- Registro de acontecimientos.

### 9.1 Iniciativa y turnos

La aplicación debe gestionar:

- Tiradas de iniciativa.
- Orden de actuación.
- Turno actual.
- Acción.
- Acción adicional.
- Movimiento.
- Reacción.
- Efectos temporales.
- Condiciones.
- Finalización del turno.

Debe indicar claramente a quién le corresponde actuar.

No debe permitir que un jugador ejecute acciones incompatibles con las reglas o con su turno.

### 9.2 Movimiento

El sistema debe validar:

- Velocidad disponible.
- Distancia recorrida.
- Obstáculos.
- Terreno difícil.
- Casillas ocupadas.
- Alcance.
- Ataques de oportunidad.
- Condiciones de movimiento.

Debe poder visualizarse el área de movimiento disponible para cada personaje.

### 9.3 Inteligencia de los enemigos

Los enemigos deben actuar de forma coherente con su inteligencia, personalidad y objetivos.

La IA debe considerar:

- Capacidades.
- Habilidades.
- Recursos.
- Posición.
- Estado de salud.
- Comportamiento.
- Lealtades.
- Objetivos.
- Conocimiento del entorno.

Un enemigo inteligente puede buscar cobertura, retirarse, proteger a un aliado o negociar.

Una criatura instintiva puede comportarse de forma completamente diferente.

La IA no debe hacer que todos los enemigos actúen de manera idéntica.

### 9.4 Información visible durante el combate

Los jugadores podrán consultar información perceptible:

- Apariencia.
- Tamaño.
- Posición.
- Estado aparente.
- Acciones observables.

No deben conocer automáticamente estadísticas privadas, resistencias, debilidades ni puntos de vida exactos.

El DM debe tener acceso a toda la información.

## 10. NPC AVANZADOS Y DIÁLOGOS

Cada NPC debe tener una identidad persistente.

Su ficha interna debe incluir:

- Nombre.
- Descripción.
- Personalidad.
- Motivaciones.
- Objetivos.
- Miedos.
- Relaciones.
- Actitud hacia cada personaje.
- Información conocida.
- Secretos.
- Historia.
- Estado emocional.
- Voz y estilo de comunicación.

#### Memoria de los NPC

Los NPC deben recordar acontecimientos importantes.

Ejemplos:

- Un guardia recuerda que los jugadores lo engañaron.
- Un comerciante recuerda una deuda.
- Un aliado recuerda que fue rescatado.
- Un enemigo recuerda una traición.

Los NPC no deben compartir información que desconocen.

La IA debe poder interpretar conversaciones de forma natural, sin limitar los diálogos a respuestas predefinidas.

## 11. MEMORIA PERSISTENTE DE CAMPAÑA

La aplicación debe disponer de un sistema de memoria a largo plazo.

Debe almacenar:

- Eventos.
- Decisiones.
- Conversaciones relevantes.
- NPC conocidos.
- Relaciones.
- Misiones.
- Objetos.
- Inventarios.
- Experiencia.
- Lugares visitados.
- Secretos descubiertos.
- Enemigos derrotados.
- Personajes fallecidos.
- Consecuencias.
- Estado actual de la historia.

### 11.1 Memoria por categorías

Separar la memoria en:

- Memoria global de campaña.
- Memoria de cada personaje.
- Memoria de cada NPC.
- Memoria de cada localización.
- Memoria de cada sesión.
- Memoria de acontecimientos.
- Memoria secreta del DM.

### 11.2 Resúmenes de sesión

Al terminar una sesión, generar automáticamente un resumen con:

- Acontecimientos importantes.
- Decisiones.
- Personajes presentes.
- Objetos obtenidos.
- Misiones.
- Cambios de estado.
- Situación final.

Al reanudar la campaña, la IA debe recuperar el contexto necesario.

Debe existir la posibilidad de corregir manualmente recuerdos o acontecimientos registrados incorrectamente.

### 11.3 Protección contra contradicciones

El sistema debe consultar la memoria antes de narrar nuevos acontecimientos.

Debe distinguir entre hechos confirmados, hipótesis de personajes y secretos todavía desconocidos.

## 12. MULTIJUGADOR Y MODO LOCAL

La aplicación debe soportar dos modalidades de juego.

### 12.1 Modo local

Todos los jugadores pueden participar desde un único dispositivo.

Debe existir una interfaz compartida donde:

- Se vea la narración.
- Se introduzcan acciones.
- Se consulten personajes.
- Se lancen dados.
- Se visualicen mapas.
- Se gestione el combate.

Debe poder alternarse entre jugadores sin necesidad de crear cuentas individuales para una sesión local.

También debe permitir ocultar información privada cuando un jugador consulte su ficha.

### 12.2 Modo multijugador online

Cada jugador podrá entrar desde su propio dispositivo.

El sistema debe permitir:

- Crear salas.
- Compartir invitaciones.
- Incorporar jugadores.
- Seleccionar personajes.
- Consultar fichas individuales.
- Enviar acciones.
- Lanzar dados.
- Visualizar mapas.
- Sincronizar turnos.
- Consultar acontecimientos.

### 12.3 Sincronización en tiempo real

Todos los participantes deben compartir el mismo estado de partida.

Si un jugador mueve su personaje, los demás deben visualizar el cambio conforme a sus permisos de visibilidad.

El sistema debe gestionar conflictos de acciones, turnos simultáneos y reconexiones.

### 12.4 Privacidad

Cada jugador debe acceder exclusivamente a:

- Su ficha.
- Su inventario.
- Sus tiradas privadas, cuando existan.
- La información visible para su personaje.
- La información compartida por el grupo.

El DM debe poder enviar información privada a un jugador sin que los demás la reciban.

## 13. PANEL PRIVADO DEL DUNGEON MASTER

Debe existir un panel exclusivo para consultar y administrar la información completa de la aventura.

Debe incluir:

- Campaña original.
- Mapas completos.
- Habitaciones ocultas.
- Enemigos no descubiertos.
- Estadísticas.
- Secretos.
- Trampas.
- Eventos futuros.
- Motivaciones de NPC.
- Misiones.
- Estado de los encuentros.
- Historial de decisiones.
- Memoria interna.
- Estado de todos los personajes.
- También debe permitir intervenir manualmente.

El DM humano debe poder:

- Corregir posiciones.
- Modificar puntos de vida.
- Añadir enemigos.
- Retirar entidades.
- Cambiar estados.
- Ajustar tiradas.
- Editar acontecimientos.
- Modificar dificultades.
- Revelar información.
- Desactivar temporalmente la IA.

La intervención manual debe quedar registrada.

## 14. INTERFAZ Y EXPERIENCIA DE USUARIO

Diseñar una interfaz moderna, inmersiva y funcional con estética de fantasía medieval.

Debe tener las siguientes secciones:

#### Panel principal

Crear campaña.

Cargar PDF.

Administrar campañas.

Continuar partidas.

Crear sala.

Unirse a una sala.

Consultar sesiones guardadas.

#### Sala de juego

Narración.

Conversación.

Entrada de acciones.

Tiradas.

Historial.

Personajes.

Inventarios.

#### Vista de exploración

Mapa.

Cuadrícula.

Niebla de guerra.

Elementos interactivos.

Posiciones.

Indicadores de visibilidad.

#### Vista de combate

Mapa táctico.

Tokens.

Iniciativa.

Turnos.

Acciones.

Vida.

Condiciones.

Registro de combate.

#### Ficha de personaje

Características.

Habilidades.

Equipo.

Inventario.

Hechizos.

Recursos.

Historial.

#### Panel del DM

Información secreta.

Mapas completos.

Enemigos.

NPC.

Memoria.

Eventos.

Herramientas de administración.

La interfaz debe ser adaptable a computadoras, tablets y dispositivos móviles.

## 15. ARQUITECTURA DEL SISTEMA DE IA

No desarrollar la aplicación como un único chatbot.

Implementar un sistema modular donde diferentes componentes colaboren.

#### Módulos internos

1. **Director narrativo.** Se encarga de la narración, diálogos y acontecimientos.
2. **Intérprete de reglas.** Determina las pruebas, habilidades, dificultades y resultados.
3. **Gestor de campañas.** Consulta los documentos originales y sus referencias.
4. **Gestor de combate.** Controla turnos, movimiento, enemigos y condiciones.
5. **Gestor de percepción.** Determina qué puede conocer cada personaje.
6. **Gestor de NPC.** Administra personalidades, conversaciones y recuerdos.
7. **Gestor de memoria.** Mantiene la continuidad de la campaña.
8. **Gestor de mapas.** Controla posiciones, obstáculos, visibilidad y elementos.
9. **Gestor de personajes.** Administra fichas, inventarios, habilidades y recursos.
10. **Coordinador central.** Recibe las acciones, consulta los módulos correspondientes y determina el siguiente paso del juego.

#### Motor determinista

Las operaciones que requieran exactitud deben implementarse mediante código:

- Dados.
- Modificadores.
- Cálculo de daño.
- Puntos de vida.
- Movimiento.
- Distancias.
- Iniciativa.
- Condiciones.
- Visibilidad.
- Estados de entidades.

La IA debe interpretar y tomar decisiones narrativas, pero no ser la única responsable de operaciones matemáticas o cambios críticos del estado.

#### Estado centralizado

La partida debe tener un estado estructurado y persistente.

Cada operación debe validar los cambios antes de guardarlos.

Debe existir un historial de eventos que permita reconstruir el desarrollo de la partida.

## 16. CONFIGURACIÓN DE REGLAS Y PERSONALIZACIÓN

_Pendiente: el texto original termina aquí. Completar esta sección (edición de reglas, reglas opcionales, personalización de la IA, etc.)._
