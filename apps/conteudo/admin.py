from django.contrib import admin
from django.utils.html import format_html

from apps.camaras.admin_mixins import AdminDaCamara

from .models import Banner, Pagina


@admin.register(Banner)
class BannerAdmin(AdminDaCamara):
    list_display = ["miniatura", "titulo", "ordem", "inicio", "fim", "ativo"]
    list_display_links = ["miniatura", "titulo"]
    list_editable = ["ordem", "ativo"]
    list_filter = ["ativo"]

    @admin.display(description="imagem")
    def miniatura(self, obj):
        return format_html('<img src="{}" alt="" style="height:40px;border-radius:4px">', obj.imagem.url) if obj.imagem else "—"


@admin.register(Pagina)
class PaginaAdmin(AdminDaCamara):
    list_display = ["titulo", "menu", "ordem", "publicada"]
    list_editable = ["ordem", "publicada"]
    list_filter = ["menu", "publicada"]
    search_fields = ["titulo", "corpo"]
    prepopulated_fields = {"slug": ["titulo"]}
