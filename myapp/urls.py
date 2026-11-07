from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('reserva/', views.reserva, name='reserva'),   # ← esta línea es la que falta
]