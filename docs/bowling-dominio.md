# Dominio de Bowling

Este documento resume el dominio general del bowling center. El issue actual de tarifas modela principalmente la parte de reservas, pistas y precios.

## Pistas y reservas

- El centro tiene varias pistas de bowling.
- Cada pista tiene un identificador único y una capacidad máxima de jugadores.
- Los clientes pueden reservar una pista en un día y hora específicos.
- Cada reserva corresponde a una sola pista.
- La pista queda bloqueada durante el turno reservado.

## Clientes

- Los clientes deben registrarse en el centro para poder realizar reservas.
- Cada cliente tiene un número de cliente único, nombre, dirección, teléfono y correo electrónico.

## Tarifas

- El costo de una reserva depende de una tarifa configurable asociada a la pista.
- Las tarifas varían según el día y la hora.
- El dueño configura las tarifas por pista y las actualiza semanalmente.
- El sistema se comporta como un calendario por día y hora para mostrar disponibilidad y calcular el precio.

## Cafetería

- El centro cuenta con una cafetería que ofrece comida y bebida.
- Los pedidos realizados durante el juego se registran en la reserva para calcular el costo total.

## Partidas y jugadores

- Durante una reserva se registra al menos una partida.
- Cada partida tiene un identificador único y se asocia a una reserva y a una pista determinada.
- En cada partida participan varios jugadores.
- Cada jugador tiene un identificador único y un nombre.
- En cada turno se registra el puntaje de los jugadores.
