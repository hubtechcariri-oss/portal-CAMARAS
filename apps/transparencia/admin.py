from django.contrib import admin

from apps.camaras.admin_mixins import AdminDaCamara, selo_publicacao

from .models import CategoriaTransparencia, Documento, GrupoTransparencia


class SoPlataforma:
    """O catálogo é mantido pela equipe da plataforma; as câmaras só leem."""

    def has_module_permission(self, request):
        return request.user.is_superuser


class CategoriaInline(admin.TabularInline):
    model = CategoriaTransparencia
    extra = 0
    prepopulated_fields = {"slug": ["nome"]}


@admin.register(GrupoTransparencia)
class GrupoAdmin(SoPlataforma, admin.ModelAdmin):
    list_display = ["nome", "ordem"]
    inlines = [CategoriaInline]


@admin.register(CategoriaTransparencia)
class CategoriaAdmin(SoPlataforma, admin.ModelAdmin):
    list_display = ["nome", "grupo", "obrigatoria", "ordem"]
    list_filter = ["grupo", "obrigatoria"]
    search_fields = ["nome"]


@admin.register(Documento)
class DocumentoAdmin(AdminDaCamara):
    list_display = ["titulo", "categoria", "data", "competencia", "situacao"]
    list_filter = ["categoria__grupo", "categoria", "publicado"]
    search_fields = ["titulo", "numero", "descricao"]
    date_hierarchy = "data"
    autocomplete_fields = ["categoria"]

    @admin.display(description="situação", ordering="publicado")
    def situacao(self, obj):
        return selo_publicacao(obj.publicado)
