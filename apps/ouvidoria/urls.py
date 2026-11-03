from django.urls import path

from . import views

app_name = "ouvidoria"
urlpatterns = [
    path("", views.nova, name="nova"),
    path("enviada/", views.confirmacao, name="confirmacao"),
    path("consulta/", views.consulta, name="consulta"),
]
