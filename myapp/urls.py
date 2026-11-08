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
]