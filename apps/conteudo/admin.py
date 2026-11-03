from django.contrib import admin
from apps.camaras.admin_mixins import AdminDaCamara, selo
from apps.camaras.midia import previa

from .models import Banner, Pagina


@admin.register(Banner)
class BannerAdmin(AdminDaCamara):
    list_display = ["miniatura", "titulo", "situacao", "ordem", "inicio", "fim", "ativo"]
    list_display_links = ["miniatura", "titulo"]
    list_editable = ["ordem", "ativo"]
    list_filter = ["ativo"]
    readonly_fields = ["imagem_atual"]

    @admin.display(description="situação")
    def situacao(self, obj):
        from django.utils import timezone

        agora = timezone.now()
        if not obj.ativo:
            return selo("neutro", "Desativado")
        if obj.inicio > agora:
            return selo("atencao", "Agendado")
        if obj.fim and obj.fim < agora:
            return selo("neutro", "Encerrado")
        return selo("ok", "No ar")

    @admin.display(description="imagem")
    def miniatura(self, obj):
        return previa(obj.imagem, 45)

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
