from django.contrib import admin

from apps.camaras.admin_mixins import AdminDaCamara, SituacaoPublicacaoFilter, selo_publicacao
from apps.camaras.midia import previa

from .models import Noticia


@admin.register(Noticia)
class NoticiaAdmin(AdminDaCamara):
    list_display = ["miniatura", "titulo", "publicada_em", "situacao"]
    list_display_links = ["miniatura", "titulo"]
    readonly_fields = ["imagem_atual"]
    list_filter = [SituacaoPublicacaoFilter]
    search_fields = ["titulo", "corpo"]
    prepopulated_fields = {"slug": ["titulo"]}
    date_hierarchy = "publicada_em"

    @admin.display(description="imagem")
    def miniatura(self, obj):
        return previa(obj.imagem, 45)

    @admin.display(description="situação", ordering="publicada")
    def situacao(self, obj):
        return selo_publicacao(obj.publicada, obj.publicada_em)

    @admin.display(description="imagem atual")
    def imagem_atual(self, obj):
        return previa(obj.imagem, 160)
