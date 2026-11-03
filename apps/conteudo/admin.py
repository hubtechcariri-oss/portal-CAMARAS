from django.contrib import admin
from apps.camaras.admin_mixins import AdminDaCamara
from apps.camaras.midia import previa

from .models import Banner, Pagina


@admin.register(Banner)
class BannerAdmin(AdminDaCamara):
    list_display = ["miniatura", "titulo", "ordem", "inicio", "fim", "ativo"]
    list_display_links = ["miniatura", "titulo"]
    list_editable = ["ordem", "ativo"]
    list_filter = ["ativo"]
    readonly_fields = ["imagem_atual"]

    @admin.display(description="imagem")
    def miniatura(self, obj):
        return previa(obj.imagem, 40)

    @admin.display(description="imagem atual")
    def imagem_atual(self, obj):
        return previa(obj.imagem, 160)


@admin.register(Pagina)
class PaginaAdmin(AdminDaCamara):
    list_display = ["titulo", "menu", "ordem", "publicada"]
    readonly_fields = ["imagem_atual"]

    @admin.display(description="imagem atual")
    def imagem_atual(self, obj):
        return previa(obj.imagem, 160)
    list_editable = ["ordem", "publicada"]
    list_filter = ["menu", "publicada"]
    search_fields = ["titulo", "corpo"]
    prepopulated_fields = {"slug": ["titulo"]}
