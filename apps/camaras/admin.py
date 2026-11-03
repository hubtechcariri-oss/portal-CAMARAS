from django.contrib import admin
from django.shortcuts import redirect
from django.urls import reverse

from .admin_mixins import camaras_do_usuario
from .midia import previa
from .models import Camara, Dominio, IdentidadePortal, Membro


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


@admin.register(IdentidadePortal)
class IdentidadePortalAdmin(admin.ModelAdmin):
    """Onde a equipe da câmara troca brasão, cor, redes sociais e dados de contato.

    Não cria nem apaga câmaras e não mexe em domínios: isso fica com a plataforma.
    """

    list_display = ["miniatura", "nome", "municipio", "uf"]
    list_display_links = ["miniatura", "nome"]
    readonly_fields = ["previa_brasao"]
    fieldsets = [
        ("Identidade visual", {"fields": ["previa_brasao", "brasao", "cor_primaria"]}),
        ("Redes sociais", {"fields": ["facebook", "instagram", "youtube"]}),
        ("Contato e atendimento", {"fields": ["endereco", "telefone", "email", "horario_atendimento",
                                               "encarregado_lgpd", "cnpj"]}),
    ]

    def get_queryset(self, request):
        return super().get_queryset(request).filter(pk__in=camaras_do_usuario(request.user))

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        # Quem cuida de uma câmara só vai direto para o formulário dela.
        camaras = list(self.get_queryset(request)[:2])
        if len(camaras) == 1:
            return redirect(reverse("admin:camaras_identidadeportal_change", args=[camaras[0].pk]))
        return super().changelist_view(request, extra_context)

    @admin.display(description="brasão")
    def miniatura(self, obj):
        return previa(obj.brasao, 32)

    @admin.display(description="brasão atual")
    def previa_brasao(self, obj):
        return previa(obj.brasao, 96)
