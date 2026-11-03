from django.contrib import admin

from apps.camaras.admin_mixins import AdminDaCamara

from .models import Legislatura, Norma, Vereador


@admin.register(Legislatura)
class LegislaturaAdmin(AdminDaCamara):
    list_display = ["__str__", "inicio", "fim"]


@admin.register(Vereador)
class VereadorAdmin(AdminDaCamara):
    list_display = ["nome_parlamentar", "partido", "cargo_mesa", "em_exercicio"]
    list_filter = ["em_exercicio", "partido"]
    search_fields = ["nome_parlamentar", "nome_civil"]
    filter_horizontal = ["legislaturas"]


@admin.register(Norma)
class NormaAdmin(AdminDaCamara):
    list_display = ["__str__", "data", "ementa", "publicada"]
    list_filter = ["tipo", "ano", "publicada"]
    search_fields = ["numero", "ementa", "texto"]
    date_hierarchy = "data"
