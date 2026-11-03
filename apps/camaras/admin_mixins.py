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
