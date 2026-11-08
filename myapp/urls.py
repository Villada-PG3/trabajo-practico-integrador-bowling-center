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
]