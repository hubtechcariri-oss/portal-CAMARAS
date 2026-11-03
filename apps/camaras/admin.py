from django.contrib import admin

from .models import Camara, Dominio, Membro


class DominioInline(admin.TabularInline):
    model = Dominio
    extra = 1


class MembroInline(admin.TabularInline):
    model = Membro
    extra = 1
    autocomplete_fields = ["usuario"]


@admin.register(Camara)
class CamaraAdmin(admin.ModelAdmin):
    list_display = ["nome", "municipio", "uf", "ativa"]
    list_filter = ["uf", "ativa"]
    search_fields = ["nome", "municipio"]
    inlines = [DominioInline, MembroInline]

    def has_module_permission(self, request):
        # Só a equipe da plataforma (superusuários) gerencia câmaras e domínios.
        return request.user.is_superuser
