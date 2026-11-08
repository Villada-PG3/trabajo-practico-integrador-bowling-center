from django.urls import path
from . import views

app_name = "myapp"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("reserva/", views.ReservaView.as_view(), name="reserva"),
    path(
        "reserva/disponibilidad/",
        views.DisponibilidadView.as_view(),
        name="disponibilidad",
    ),
    path(
        "mi-reserva/",
        views.ConsultaReservaView.as_view(),
        name="consulta_reserva",
    ),
    path(
        "mi-reserva/<str:codigo>/",
        views.DetalleReservaView.as_view(),
        name="detalle_reserva",
    ),
    path(
        "mi-reserva/<str:codigo>/cancelar/",
        views.CancelarReservaView.as_view(),
        name="cancelar_reserva",
    ),
    path(
        "mi-reserva/<str:codigo>/pedido/",
        views.AgregarPedidoView.as_view(),
        name="agregar_pedido",
    ),
    path(
        "mi-reserva/<str:codigo>/juego/",
        views.PartidaView.as_view(),
        name="partida",
    ),
    path(
        "mi-reserva/<str:codigo>/juego/tirar/",
        views.TirarView.as_view(),
        name="tirar",
    ),
    path(
        "mi-reserva/<str:codigo>/juego/jugador/",
        views.AgregarJugadorJuegoView.as_view(),
        name="agregar_jugador_partida",
    ),
]