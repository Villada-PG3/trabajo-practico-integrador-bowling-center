from django.contrib import admin

from .models import (
    Cliente,
    DetallePedido,
    EstadoPartida,
    EstadoPedido,
    EstadoReserva,
    Jugador,
    Lanzamiento,
    Participacion,
    Partida,
    Pedido,
    Pista,
    Producto,
    Reserva,
    TipoPista,
)

admin.site.register(TipoPista)
admin.site.register(EstadoReserva)
admin.site.register(EstadoPedido)
admin.site.register(EstadoPartida)
admin.site.register(Cliente)
admin.site.register(Jugador)
admin.site.register(Pista)
admin.site.register(Reserva)
admin.site.register(Partida)
admin.site.register(Participacion)
admin.site.register(Lanzamiento)
admin.site.register(Producto)
admin.site.register(Pedido)
admin.site.register(DetallePedido)