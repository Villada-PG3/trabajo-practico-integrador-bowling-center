from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "gestion"

urlpatterns = [
    path("", views.PanelView.as_view(), name="panel"),
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="myapp/gestion/login.html"
        ),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path(
        "tipos-pista/nuevo/",
        views.TipoPistaCreateView.as_view(),
        name="tipo_pista_crear",
    ),
    path(
        "tipos-pista/<int:pk>/editar/",
        views.TipoPistaUpdateView.as_view(),
        name="tipo_pista_editar",
    ),
    path(
        "tipos-pista/<int:pk>/eliminar/",
        views.TipoPistaDeleteView.as_view(),
        name="tipo_pista_eliminar",
    ),
]