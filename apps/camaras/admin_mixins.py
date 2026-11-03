from django import forms
from django.contrib import admin
from django.db import models

from .models import Camara


def camaras_do_usuario(usuario):
    if usuario.is_superuser:
        return Camara.objects.all()
    return Camara.objects.filter(membros__usuario=usuario)


class RestringeRelacoesMixin:
    """Em listas de seleção (FK e M2M), só oferece registros das câmaras do usuário."""

    def _restringir(self, db_field, request, kwargs):
        if db_field.name == "camara":
            kwargs["queryset"] = camaras_do_usuario(request.user)
        elif hasattr(db_field.related_model, "camara") and not request.user.is_superuser:
            kwargs["queryset"] = db_field.related_model.objects.filter(
                camara__in=camaras_do_usuario(request.user)
            )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        self._restringir(db_field, request, kwargs)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        self._restringir(db_field, request, kwargs)
        return super().formfield_for_manytomany(db_field, request, **kwargs)


class AdminDaCamara(RestringeRelacoesMixin, admin.ModelAdmin):
    """Admin que só mostra e só permite gravar conteúdo das câmaras do usuário.

    Se o usuário pertence a uma única câmara, o campo `camara` some do formulário
    e é preenchido automaticamente.
    """

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(camara__in=camaras_do_usuario(request.user))

    def _camara_unica(self, request):
        camaras = list(camaras_do_usuario(request.user)[:2])
        return camaras[0] if len(camaras) == 1 and not request.user.is_superuser else None

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if not self.fieldsets or not self._camara_unica(request):
            return fieldsets
        return [(nome, {**opcoes, "fields": [f for f in opcoes["fields"] if f != "camara"]})
                for nome, opcoes in fieldsets]

    def get_exclude(self, request, obj=None):
        excluidos = list(super().get_exclude(request, obj) or [])
        if self._camara_unica(request):
            excluidos.append("camara")
        return excluidos

    def save_model(self, request, obj, form, change):
        unica = self._camara_unica(request)
        if unica and not obj.camara_id:
            obj.camara = unica
        if not request.user.is_superuser and obj.camara not in camaras_do_usuario(request.user):
            raise PermissionError("Usuário não pertence a esta câmara.")
        super().save_model(request, obj, form, change)


class FormDaCamara(forms.ModelForm):
    """Impede ligar conteúdo de câmaras diferentes (ex.: autor da Câmara B numa matéria da Câmara A).

    Relevante sobretudo para superusuários, que enxergam todas as câmaras.
    """

    def clean(self):
        dados = super().clean()
        camara = dados.get("camara") or (self.instance.camara if self.instance.camara_id else None)
        if camara is None:
            return dados
        for nome, valor in list(dados.items()):
            if nome == "camara" or valor is None:
                continue
            itens = valor if hasattr(valor, "__iter__") and not isinstance(valor, (str, bytes)) else [valor]
            for item in itens:
                if hasattr(item, "camara_id") and isinstance(item, models.Model) and item.camara_id != camara.pk:
                    self.add_error(nome, f"“{item}” pertence a outra câmara.")
                    break
        return dados


AdminDaCamara.form = FormDaCamara


class PrazoFilter(admin.SimpleListFilter):
    """Filas de atendimento (e-SIC, Ouvidoria): em aberto ou com prazo vencido.

    O modelo precisa ter `ABERTAS` (situações que ainda pedem resposta) e `prazo`.
    É o mesmo critério dos cartões do Início, então o número do cartão bate com a lista.
    """

    title = "prazo"
    parameter_name = "prazo"

    def lookups(self, request, model_admin):
        return [("abertas", "Em aberto"), ("vencidas", "Prazo vencido")]

    def queryset(self, request, queryset):
        from django.utils import timezone

        if self.value() not in ("abertas", "vencidas"):
            return queryset
        abertas = queryset.filter(situacao__in=queryset.model.ABERTAS)
        if self.value() == "vencidas":
            return abertas.filter(prazo__lt=timezone.localdate())
        return abertas


ALERTA_DIAS = 5  # "vence em breve": prazo nos próximos 5 dias


def texto_do_prazo(dias):
    if dias == 0:
        return "vence hoje"
    if dias == 1:
        return "vence amanhã"
    return f"vence em {dias} dias"


def selo_do_prazo(obj):
    """Selo em texto para um pedido/manifestação: Encerrado, Vencido há N dias, Vence em N dias, No prazo."""
    from django.utils import timezone
    from django.utils.html import format_html

    if obj.situacao not in obj.ABERTAS:
        return format_html('<span class="selo selo--ok">{}</span>', "Encerrado")
    dias = (obj.prazo - timezone.localdate()).days
    if dias < 0:
        return format_html('<span class="selo selo--critico">Vencido há {} dia{}</span>', -dias, "s" if dias < -1 else "")
    if dias <= ALERTA_DIAS:
        return format_html('<span class="selo selo--atencao">{}</span>', texto_do_prazo(dias).capitalize())
    return format_html('<span class="selo selo--neutro">{}</span>', "No prazo")


class FilaDeAtendimentoMixin:
    """Filas do e-SIC e da Ouvidoria.

    - Ao filtrar por prazo, a lista vem ordenada pelo prazo mais próximo (o mais urgente primeiro).
    - A coluna "prazo" mostra o estado em texto (selo), não só um ícone colorido.
    """

    @admin.display(description="situação do prazo", ordering="prazo")
    def selo_prazo(self, obj):
        return selo_do_prazo(obj)

    def get_ordering(self, request):
        if request.GET.get(PrazoFilter.parameter_name) in ("abertas", "vencidas"):
            return ["prazo", "pk"]
        return super().get_ordering(request)


# ---------------------------------------------------------------------------
# Selos de situação nas listas (texto + cor; a cor nunca é a única pista).
# ---------------------------------------------------------------------------

def selo(estado, texto):
    from django.utils.html import format_html

    return format_html('<span class="selo selo--{}">{}</span>', estado, texto)


def situacao_publicacao(publicada, quando=None):
    """("publicada" | "agendada" | "rascunho", rótulo)."""
    from django.utils import timezone

    if not publicada:
        return "rascunho", "Rascunho"
    if quando and quando > timezone.now():
        return "agendada", "Agendada"
    return "publicada", "Publicada"


ESTADO_DO_SELO = {"publicada": "ok", "agendada": "atencao", "rascunho": "neutro"}


def selo_publicacao(publicada, quando=None):
    chave, rotulo = situacao_publicacao(publicada, quando)
    return selo(ESTADO_DO_SELO[chave], rotulo)


class SituacaoPublicacaoFilter(admin.SimpleListFilter):
    """Publicada / Agendada / Rascunho, para modelos com `publicada` e `publicada_em`."""

    title = "situação"
    parameter_name = "situacao_publicacao"

    def lookups(self, request, model_admin):
        return [("publicada", "Publicada"), ("agendada", "Agendada"), ("rascunho", "Rascunho")]

    def queryset(self, request, queryset):
        from django.utils import timezone

        agora = timezone.now()
        if self.value() == "publicada":
            return queryset.filter(publicada=True, publicada_em__lte=agora)
        if self.value() == "agendada":
            return queryset.filter(publicada=True, publicada_em__gt=agora)
        if self.value() == "rascunho":
            return queryset.filter(publicada=False)
        return queryset


class ColunaPublicacaoMixin:
    """Coluna "situação" (Publicada / Rascunho) para modelos com o campo booleano `publicada`."""

    @admin.display(description="situação", ordering="publicada")
    def situacao_publicacao(self, obj):
        return selo_publicacao(obj.publicada)


class UltimosDiasFilter(admin.SimpleListFilter):
    """Publicadas nos últimos 30 dias (mesmo critério do indicador do Início)."""

    title = "período"
    parameter_name = "ultimos_dias"
    DIAS = 30

    def lookups(self, request, model_admin):
        return [(str(self.DIAS), f"Últimos {self.DIAS} dias")]

    def queryset(self, request, queryset):
        from datetime import timedelta

        from django.utils import timezone

        if self.value() != str(self.DIAS):
            return queryset
        agora = timezone.now()
        return queryset.filter(publicada=True, publicada_em__gt=agora - timedelta(days=self.DIAS),
                               publicada_em__lte=agora)
