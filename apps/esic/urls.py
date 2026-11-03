from django.urls import path

from . import views

app_name = "esic"
urlpatterns = [
    path("", views.novo, name="novo"),
    path("enviado/", views.confirmacao, name="confirmacao"),
    path("consulta/", views.consulta, name="consulta"),
    path("consulta/<str:qual>/", views.baixar_anexo, name="anexo"),
]
