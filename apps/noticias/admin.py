from django.contrib import admin

from apps.camaras.admin_mixins import AdminDaCamara
from apps.camaras.midia import previa

from .models import Noticia


@admin.register(Noticia)
class NoticiaAdmin(AdminDaCamara):
    list_display = ["miniatura", "titulo", "publicada_em", "publicada"]
    list_display_links = ["miniatura", "titulo"]
    readonly_fields = ["imagem_atual"]
    list_filter = ["publicada"]
    search_fields = ["titulo", "corpo"]
    prepopulated_fields = {"slug": ["titulo"]}
    date_hierarchy = "publicada_em"

    @admin.display(description="imagem")
    def miniatura(self, obj):
        return previa(obj.imagem, 40)

    @admin.display(description="imagem atual")
    def imagem_atual(self, obj):
        return previa(obj.imagem, 160)
