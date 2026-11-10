from django.contrib import admin

from .models import (
    Cliente,
    DetallePedido,
    EstadoPartida,
    EstadoPedido,
    EstadoReserva,
    HorarioAtencion,
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

admin.site.site_header = "Pins & Co. Administración"
admin.site.site_title = "Pins & Co."
admin.site.index_title = "Datos del centro"


class DetallePedidoInline(admin.TabularInline):
    model = DetallePedido
    extra = 1


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ("reserva", "fecha_hora_pedido", "estado")
    list_filter = ("estado",)
    search_fields = ("reserva__codigo",)
    inlines = [DetallePedidoInline]


@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = (
        "codigo",
        "cliente",
        "pista",
        "fecha",
        "hora_inicio",
        "hora_fin",
        "estado",
        "cantidad_jugadores",
    )
    list_filter = ("estado", "fecha", "pista__tipo_pista")
    search_fields = ("codigo", "cliente__nombre", "cliente__email")
    date_hierarchy = "fecha"
    ordering = ("-fecha", "hora_inicio")
    readonly_fields = ("codigo", "precio_hora")


@admin.register(Pista)
class PistaAdmin(admin.ModelAdmin):
    list_display = ("numero_pista", "tipo_pista", "precio_hora", "disponible")
    list_filter = ("tipo_pista", "disponible")
    search_fields = ("numero_pista",)


@admin.register(TipoPista)
class TipoPistaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "precio_hora", "capacidad_maxima", "duracion_minima")
    search_fields = ("nombre",)


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("nombre", "email", "telefono", "direccion")
    search_fields = ("nombre", "email")


@admin.register(HorarioAtencion)
class HorarioAtencionAdmin(admin.ModelAdmin):
    list_display = ("dia_semana", "hora_apertura", "hora_cierre")
    list_filter = ("dia_semana",)


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "tipo", "precio")
    list_filter = ("tipo",)
    search_fields = ("nombre",)


@admin.register(Partida)
class PartidaAdmin(admin.ModelAdmin):
    list_display = ("reserva", "numero", "fecha_hora_inicio", "estado")
    list_filter = ("estado",)


admin.site.register(Jugador)
admin.site.register(Participacion)
admin.site.register(Lanzamiento)
admin.site.register(EstadoReserva)
admin.site.register(EstadoPedido)
admin.site.register(EstadoPartida)