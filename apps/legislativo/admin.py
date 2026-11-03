from django.contrib import admin

from apps.camaras.admin_mixins import AdminDaCamara, RestringeRelacoesMixin

from .models import Legislatura, Materia, Norma, Sessao, Tramitacao, Vereador


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


@admin.register(Sessao)
class SessaoAdmin(AdminDaCamara):
    list_display = ["__str__", "tipo", "data_hora", "publicada"]
    list_filter = ["tipo", "publicada"]
    date_hierarchy = "data_hora"
    filter_horizontal = ["presentes"]


class TramitacaoInline(RestringeRelacoesMixin, admin.TabularInline):
    model = Tramitacao
    extra = 1


@admin.register(Materia)
class MateriaAdmin(AdminDaCamara):
    list_display = ["__str__", "data_apresentacao", "ementa", "situacao", "publicada"]
    list_filter = ["tipo", "ano", "situacao", "publicada"]
    search_fields = ["ementa", "texto", "autor_externo", "autores__nome_parlamentar"]
    filter_horizontal = ["autores"]
    date_hierarchy = "data_apresentacao"
    inlines = [TramitacaoInline]
