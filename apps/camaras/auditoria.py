"""Trilha de auditoria: registra quem criou, alterou ou excluiu cada registro, e as entradas no painel.

Funciona por sinais do Django, então cobre o painel inteiro (inclusive itens em linha, como anexos e
membros) sem que cada tela precise lembrar de registrar. Só grava o que um usuário logado faz numa
requisição: importações automáticas, comandos e envios de cidadãos (e-SIC, Ouvidoria) ficam de fora.
"""

import threading

from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.db import models
from django.db.models.signals import m2m_changed, post_delete, post_save, pre_delete, pre_save
from django.utils import timezone
from django.utils.html import strip_tags

_local = threading.local()

LIMITE_TEXTO = 300
CAMPOS_OCULTOS = {"password"}  # nunca guarda o valor, só que mudou
CAMPOS_IGNORADOS = {"last_login", "criado_em", "atualizado_em"}
# Modelos que não interessam à auditoria ou que só mudam por importação automática.
IGNORADOS = {
    "camaras.registroauditoria", "admin.logentry", "sessions.session", "contenttypes.contenttype",
    "integracoes.importacao", "transparencia.licitacao", "transparencia.contrato",
    "transparencia.despesa", "transparencia.movimentodespesa",
}


class AuditoriaMiddleware:
    """Guarda a requisição atual para os sinais saberem quem está agindo e de qual IP."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _local.request = request
        try:
            return self.get_response(request)
        finally:
            _local.request = None


def _requisicao():
    return getattr(_local, "request", None)


def _usuario_atual():
    request = _requisicao()
    usuario = getattr(request, "user", None)
    return usuario if usuario is not None and usuario.is_authenticated else None


def ip_de(request):
    if request is None:
        return None
    encaminhado = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return (encaminhado.split(",")[0].strip() if encaminhado else request.META.get("REMOTE_ADDR")) or None


def _chave(modelo):
    return f"{modelo._meta.app_label}.{modelo._meta.model_name}"


def _auditavel(instancia):
    return _usuario_atual() is not None and _chave(type(instancia)) not in IGNORADOS


def _texto(valor):
    if valor is None or valor == "":
        return ""
    texto = strip_tags(str(valor)).strip()
    return texto if len(texto) <= LIMITE_TEXTO else texto[:LIMITE_TEXTO - 1] + "…"


def _campos(modelo):
    return [c for c in modelo._meta.concrete_fields
            if not c.primary_key and c.name not in CAMPOS_IGNORADOS and not getattr(c, "auto_now", False)]


def _valor(instancia, campo):
    if campo.name in CAMPOS_OCULTOS:
        return "••••••"
    if isinstance(campo, models.ForeignKey):
        if getattr(instancia, campo.attname) is None:
            return ""
        return _texto(getattr(instancia, campo.name, None))
    if campo.choices:
        return _texto(getattr(instancia, f"get_{campo.name}_display")())
    if isinstance(campo, models.BooleanField):
        valor = getattr(instancia, campo.attname)
        return "" if valor is None else ("sim" if valor else "não")
    if isinstance(campo, models.DateTimeField):
        valor = getattr(instancia, campo.attname)
        return timezone.localtime(valor).strftime("%d/%m/%Y %H:%M") if valor else ""
    if isinstance(campo, models.DateField):
        valor = getattr(instancia, campo.attname)
        return valor.strftime("%d/%m/%Y") if valor else ""
    if isinstance(campo, models.FileField):
        arquivo = getattr(instancia, campo.attname)
        return arquivo.name.rsplit("/", 1)[-1] if arquivo else ""
    return _texto(getattr(instancia, campo.attname))


def _comparavel(instancia, campo):
    """O valor exibido, exceto nos campos ocultos, que são comparados pelo valor bruto e nunca exibidos."""
    return getattr(instancia, campo.attname) if campo.name in CAMPOS_OCULTOS else _valor(instancia, campo)


def _retrato(instancia):
    """{rótulo do campo: valor} dos campos preenchidos (para guardar o que foi excluído)."""
    return {str(c.verbose_name): v for c in _campos(type(instancia)) if (v := _valor(instancia, c))}


def _camara_de(instancia, usuario):
    from .admin_mixins import camaras_do_usuario
    from .models import Camara

    if isinstance(instancia, Camara):
        return instancia.pk
    if getattr(instancia, "camara_id", None):
        return instancia.camara_id
    for campo in type(instancia)._meta.concrete_fields if instancia is not None else []:
        if isinstance(campo, models.ForeignKey) and getattr(instancia, campo.attname, None):
            relacionado = getattr(instancia, campo.name, None)  # ex.: anexo -> pedido -> câmara
            if getattr(relacionado, "camara_id", None):
                return relacionado.camara_id
    if usuario is not None and not usuario.is_superuser:
        camaras = list(camaras_do_usuario(usuario).values_list("pk", flat=True)[:2])
        if len(camaras) == 1:
            return camaras[0]
    return None


def registrar(acao, instancia=None, detalhes=None, usuario=None, request=None, nome="", camara_id=None):
    from django.contrib.contenttypes.models import ContentType

    from .models import RegistroAuditoria

    request = request or _requisicao()
    usuario = usuario or _usuario_atual()
    dados = {"acao": acao, "usuario": usuario, "detalhes": detalhes or {}, "ip": ip_de(request),
             "usuario_nome": (usuario.get_full_name() or usuario.get_username()) if usuario else nome}
    if instancia is not None:
        dados.update(
            content_type=ContentType.objects.get_for_model(type(instancia)),
            object_id=str(instancia.pk or ""), objeto=_texto(instancia)[:200],
            tipo=str(type(instancia)._meta.verbose_name)[:100],
        )
    dados["camara_id"] = camara_id or _camara_de(instancia, usuario)
    return RegistroAuditoria.objects.create(**dados)


# --- criação, alteração e exclusão ------------------------------------------------------------

def _antes(sender, instance, raw=False, **kwargs):
    if raw or instance._state.adding or not instance.pk or not _auditavel(instance):
        return
    anterior = sender._base_manager.filter(pk=instance.pk).first()
    if anterior is not None:
        instance._auditoria_antes = {c.name: _comparavel(anterior, c) for c in _campos(sender)}


def _depois(sender, instance, created, raw=False, **kwargs):
    if raw or not _auditavel(instance):
        return
    if created:
        registrar("criou", instance)
        return
    antes = getattr(instance, "_auditoria_antes", None)
    if antes is None:
        return
    del instance._auditoria_antes
    mudancas = {}
    for campo in _campos(sender):
        if antes.get(campo.name) == _comparavel(instance, campo):
            continue
        if campo.name in CAMPOS_OCULTOS:
            mudancas[str(campo.verbose_name)] = {"antes": "••••••", "depois": "(alterada)"}
        else:
            mudancas[str(campo.verbose_name)] = {"antes": antes.get(campo.name, ""), "depois": _valor(instance, campo)}
    if mudancas:  # o painel grava mesmo sem mudança; só vale registrar o que mudou de fato
        registrar("alterou", instance, mudancas)


def _antes_de_excluir(sender, instance, **kwargs):
    if _auditavel(instance):
        instance._auditoria_retrato = _retrato(instance)
        instance._auditoria_camara = _camara_de(instance, _usuario_atual())


def _excluido(sender, instance, **kwargs):
    retrato = getattr(instance, "_auditoria_retrato", None)
    if retrato is None:
        return
    registrar("excluiu", instance, retrato, camara_id=instance._auditoria_camara)


def _relacao(sender, instance, action, reverse, model, pk_set, **kwargs):
    """Grupos e permissões de usuário, matérias ligadas a autores etc. (campos muitos-para-muitos)."""
    if action not in ("post_add", "post_remove", "post_clear") or not _auditavel(instance):
        return
    campo = next((c for c in type(instance)._meta.many_to_many if c.remote_field.through is sender), None)
    if campo is None or reverse:
        return
    nomes = [_texto(o) for o in model._base_manager.filter(pk__in=pk_set or [])]
    if action == "post_clear":
        detalhe = {"antes": "(todos)", "depois": ""}
    elif action == "post_add":
        detalhe = {"antes": "", "depois": "incluiu: " + ", ".join(nomes)}
    else:
        detalhe = {"antes": "retirou: " + ", ".join(nomes), "depois": ""}
    if nomes or action == "post_clear":
        registrar("alterou", instance, {str(campo.verbose_name): detalhe})


# --- acesso ao painel ----------------------------------------------------------------------

def _entrou(sender, request, user, **kwargs):
    registrar("entrou", usuario=user, request=request)


def _saiu(sender, request, user, **kwargs):
    if user is not None:
        registrar("saiu", usuario=user, request=request)


def _falhou(sender, credentials, request=None, **kwargs):
    nome = str(credentials.get("username", ""))[:150]
    registrar("falhou", request=request, nome=nome, detalhes={"usuário informado": nome})


def conectar():
    pre_save.connect(_antes, dispatch_uid="auditoria_antes")
    post_save.connect(_depois, dispatch_uid="auditoria_depois")
    pre_delete.connect(_antes_de_excluir, dispatch_uid="auditoria_antes_de_excluir")
    post_delete.connect(_excluido, dispatch_uid="auditoria_excluido")
    m2m_changed.connect(_relacao, dispatch_uid="auditoria_relacao")
    user_logged_in.connect(_entrou, dispatch_uid="auditoria_entrou")
    user_logged_out.connect(_saiu, dispatch_uid="auditoria_saiu")
    user_login_failed.connect(_falhou, dispatch_uid="auditoria_falhou")
