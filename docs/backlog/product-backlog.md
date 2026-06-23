# Product Backlog - Bowling Center

## Clientes

- Registrar cliente.
- Consultar cliente.
- Modificar datos de cliente.
- Eliminar cliente.
- Buscar cliente por distintos criterios.

## Pistas

- Registrar pista.
- Modificar datos de una pista.
- Configurar capacidad máxima de jugadores.
- Consultar pistas disponibles.
- Bloquear una pista cuando tiene una reserva activa.

## Reservas

- Crear reserva de pista.
- Consultar reservas.
- Modificar reserva.
- Cancelar reserva.
- Registrar cantidad de jugadores de la reserva.
- Registrar estado de la reserva.
- Realizar check-in.
- Finalizar reserva.
- Asociar reserva a una pista.
- Asociar reserva a un cliente.
- Calcular costo total de la reserva.

## Tarifas

- Registrar tarifas para una pista.
- Modificar tarifas existentes.
- Definir día de aplicación de una tarifa.
- Definir horario de aplicación de una tarifa.
- Definir vigencia de una tarifa.
- Consultar tarifas configuradas.
- Aplicar tarifa correspondiente al momento de reservar.
- Calcular precio según pista, día y horario.

## Disponibilidad y Calendario

- Visualizar disponibilidad de pistas.
- Mostrar reservas en formato calendario.
- Consultar disponibilidad por día.
- Consultar disponibilidad por horario.
- Evitar superposición de reservas.
- Mostrar pistas disponibles para un horario determinado.

## Partidas

- Registrar partida.
- Asociar partida a una reserva.
- Asociar partida a una pista.
- Consultar partidas realizadas.
- Determinar ganador de una partida.

## Jugadores

- Registrar jugador.
- Asociar jugadores a una partida.
- Registrar puntajes.
- Consultar resultados de una partida.

## Cafetería

- Gestionar menú de cafetería.
- Registrar pedidos.
- Asociar pedidos a una reserva.
- Incorporar pedidos al costo total.
- Consultar consumos realizados.

---

# Reglas de negocio identificadas

- Un cliente debe estar registrado para realizar reservas.
- Cada pista posee un identificador único.
- La capacidad máxima de una pista es configurable.
- Una reserva corresponde a una sola pista.
- La pista queda ocupada durante el horario reservado.
- Las tarifas dependen del día y la hora.
- Las tarifas se configuran por pista.
- El precio de una reserva depende de la tarifa vigente.
- Toda reserva debe tener al menos una partida registrada.
- Una partida registra jugadores y puntajes.
- Los pedidos de cafetería impactan en el costo total.

---

# Pendientes de validación con el Product Owner

- Confirmar si los jugadores deben registrarse independientemente de los clientes.
- Definir si una reserva puede contener varias partidas.
- Definir si una reserva puede abarcar varias franjas horarias.
- Definir duración de los turnos.
- Definir comportamiento cuando una reserva cruza distintas tarifas.
- Confirmar si las reservas pueden modificarse.
- Confirmar si las reservas pueden cancelarse.
- Confirmar si existe gestión de pagos.
- Confirmar si se mantiene historial de operaciones.
- Confirmar la vigencia exacta de las tarifas.

---

# Prioridad inicial

## Alta

- Clientes
- Pistas
- Reservas
- Disponibilidad y calendario
- Tarifas

## Media

- Partidas
- Jugadores
- Cafetería

## Baja

- Funcionalidades sujetas a validación del PO.
