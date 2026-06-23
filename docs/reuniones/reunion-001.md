# Reunión 001 - Charla con el PO

## Fecha

- No registrada.

## Participantes

- Equipo de desarrollo
- Product Owner

## Temas tratados

- Límite de jugadores por pista.
- Tarifas por día y hora.
- Forma general de visualización y reserva en el sistema.

## Resumen

- Se confirmó que el sistema no tendrá un límite duro de jugadores por pista.
- El límite existe como restricción física y operativa, configurable por el dueño de la pista.
- Las tarifas varían según día y horario.
- Cada dueño define las tarifas por pista y las actualiza semanalmente.
- El sistema se piensa como un calendario por día y hora, donde se visualizan las pistas disponibles y se reserva un turno puntual.
- El precio final de la reserva se calcula a partir de la tarifa vigente para esa pista y horario.
- La reserva corresponde a una sola pista.
- Durante la reserva se registran al menos una partida y los puntajes de los jugadores.
- La cafetería forma parte del dominio y sus pedidos impactan en el costo total.

## Decisiones

- La capacidad máxima de la pista será configurable.
- La reserva se hará por franja horaria y corresponderá a una sola pista.
- El cálculo de precio dependerá de la tarifa configurada para la pista en ese día y horario.

## Pendientes

- Definir si se registran jugadores individuales o solo el cliente que reserva.
- Definir si la cantidad de jugadores se guarda por reserva o por jugador individual.
- Definir si la duración de una reserva es siempre fija o se puede elegir libremente.
- Confirmar si una reserva puede incluir más de una franja horaria consecutiva.
- Definir qué pasa si una reserva cruza dos franjas horarias con precios distintos.
- Confirmar si la reserva se confirma inmediatamente o pasa por un estado de pendiente.
- Definir si se pueden cancelar o modificar reservas ya creadas.
- Confirmar si las tarifas tienen una vigencia exacta por fecha o solo por día de la semana.
- Confirmar si el sistema debe mostrar disponibilidad por pista o solo por horario general.
