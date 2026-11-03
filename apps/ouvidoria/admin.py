import copy

from django.contrib import admin, messages
from django.db.models import Count, Q
from django.utils import timezone

from apps.camaras.admin_mixins import AdminDaCamara

from .models import Manifestacao


class VencidaFilter(admin.SimpleListFilter):
    title = "prazo"
    parameter_name = "prazo"

    def lookups(self, request, model_admin):
        return [("vencidas", "Vencidas"), ("abertas", "Em aberto")]

    def queryset(self, request, queryset):
        abertas = queryset.filter(situacao__in=Manifestacao.ABERTAS)
        if self.value() == "vencidas":
            return abertas.filter(prazo__lt=timezone.localdate())
        if self.value() == "abertas":
            return abertas
        return queryset


@admin.register(Manifestacao)
class ManifestacaoAdmin(AdminDaCamara):
    list_display = ["protocolo", "tipo", "assunto", "criado_em", "prazo", "situacao", "vencida"]
    list_filter = [VencidaFilter, "tipo", "situacao"]
    search_fields = ["protocolo", "assunto", "descricao", "nome", "email"]
    readonly_fields = ["protocolo", "codigo_consulta", "prazo", "prorrogada", "criado_em", "respondida_em", "anexo"]
    fieldsets = [
        ("Manifestação", {"fields": ["camara", "protocolo", "tipo", "assunto", "descricao", "anexo", "criado_em"]}),
        ("Manifestante", {"fields": ["anonima", "sigilo", "nome", "email", "telefone"]}),
        ("Tratamento", {"fields": ["situacao", "prazo", "prorrogada", "resposta", "anexo_resposta", "respondida_em", "codigo_consulta"]}),
    ]
    actions = ["prorrogar"]

    def get_fieldsets(self, request, obj=None):
        fieldsets = copy.deepcopy(super().get_fieldsets(request, obj))
        if self._camara_unica(request):
            fieldsets[0][1]["fields"] = [f for f in fieldsets[0][1]["fields"] if f != "camara"]
        return fieldsets

    @admin.display(boolean=True)
    def vencida(self, obj):
        return obj.vencida

    @admin.action(description="Prorrogar prazo por 30 dias")
    def prorrogar(self, request, queryset):
        for m in queryset:
            try:
                m.prorrogar()
                m.save()
            except ValueError as erro:
                self.message_user(request, f"{m}: {erro}", messages.WARNING)

    def changelist_view(self, request, extra_context=None):
        # Resumo por tipo no topo da lista: base para o relatório anual de gestão (art. 14, II).
        qs = self.get_queryset(request)
        resumo = qs.values("tipo").annotate(
            total=Count("id"), abertas=Count("id", filter=Q(situacao__in=Manifestacao.ABERTAS))
        )
        rotulos = dict(Manifestacao.Tipo.choices)
        extra_context = {**(extra_context or {}), "subtitle": " · ".join(
            f"{rotulos[r['tipo']]}: {r['total']} ({r['abertas']} em aberto)" for r in resumo
        )}
        return super().changelist_view(request, extra_context)
