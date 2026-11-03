"""Dados do painel administrativo: identidade da câmara, pendências e atalhos."""

from datetime import timedelta

from django import template
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from apps.camaras.admin_mixins import ALERTA_DIAS, camaras_do_usuario, texto_do_prazo

register = template.Library()

ATALHOS = [
    # (permissão, rótulo, url name, ícone)
    ("noticias.add_noticia", "Nova notícia", "admin:noticias_noticia_add", "noticia"),
    ("conteudo.add_banner", "Novo banner", "admin:conteudo_banner_add", "imagem"),
    ("legislativo.add_sessao", "Nova sessão", "admin:legislativo_sessao_add", "sessao"),
    ("legislativo.add_materia", "Nova matéria", "admin:legislativo_materia_add", "materia"),
    ("legislativo.add_norma", "Nova lei ou norma", "admin:legislativo_norma_add", "lei"),
    ("transparencia.add_documento", "Publicar na transparência", "admin:transparencia_documento_add", "transparencia"),
    ("camaras.change_identidadeportal", "Brasão, cores e contatos", "admin:camaras_identidadeportal_changelist", "paleta"),
]


def camara_do_painel(usuario):
    """A câmara do usuário, quando ele cuida de uma só (para mostrar brasão e cor)."""
    if not usuario.is_authenticated:
        return None
    camaras = list(camaras_do_usuario(usuario)[:2])
    return camaras[0] if len(camaras) == 1 else None


@register.simple_tag(takes_context=True)
def painel_camara(context):
    """Câmara do domínio acessado (se o usuário tiver acesso a ela) ou a única câmara do usuário."""
    from apps.camaras.middleware import resolver_camara

    request = context.get("request")
    if not request or not request.user.is_authenticated:
        return None
    do_dominio = resolver_camara(request.get_host())
    if do_dominio and camaras_do_usuario(request.user).filter(pk=do_dominio.pk).exists():
        return do_dominio
    return camara_do_painel(request.user)


def _fila(modelo, usuario, url_name, rotulo):
    """Resumo de uma fila de atendimento, com o mesmo critério do filtro "Em aberto" da lista."""
    if not usuario.has_perm(f"{modelo._meta.app_label}.view_{modelo._meta.model_name}"):
        return None
    hoje = timezone.localdate()
    qs = modelo.objects.filter(situacao__in=modelo.ABERTAS)
    if not usuario.is_superuser:
        qs = qs.filter(camara__in=camaras_do_usuario(usuario))
    abertas = qs.count()
    vencidas = qs.filter(prazo__lt=hoje).count()
    vencendo = qs.filter(prazo__gte=hoje, prazo__lte=hoje + timedelta(days=ALERTA_DIAS)).count()
    proximo = qs.filter(prazo__gte=hoje).order_by("prazo").values_list("prazo", flat=True).first()

    # Estado sempre em texto (não só cor). Verde ("em dia") só quando não há nada pendente.
    if not abertas:
        estado, rotulo_estado = "ok", "Em dia"
    elif vencidas:
        estado, rotulo_estado = "critico", "Crítico"
    elif vencendo:
        estado, rotulo_estado = "atencao", "Atenção"
    else:
        estado, rotulo_estado = "neutro", "Em andamento"

    return {
        "rotulo": rotulo,
        "abertas": abertas,
        "vencidas": vencidas,
        "vencendo": vencendo,
        "proximo": texto_do_prazo((proximo - hoje).days) if proximo else "",
        "estado": estado,
        "rotulo_estado": rotulo_estado,
        "url": reverse(url_name) + "?prazo=abertas",
    }


@register.simple_tag(takes_context=True)
def painel_resumo(context):
    from apps.esic.models import Pedido
    from apps.ouvidoria.models import Manifestacao

    usuario = context["request"].user
    filas = [
        _fila(Pedido, usuario, "admin:esic_pedido_changelist", "Pedidos de informação (e-SIC)"),
        _fila(Manifestacao, usuario, "admin:ouvidoria_manifestacao_changelist", "Manifestações da Ouvidoria"),
    ]
    atalhos = []
    for perm, rotulo, nome, icone in ATALHOS:
        if usuario.has_perm(perm):
            try:
                atalhos.append({"rotulo": rotulo, "url": reverse(nome), "icone": icone})
            except NoReverseMatch:
                pass
    return {"filas": [f for f in filas if f], "atalhos": atalhos, "alerta_dias": ALERTA_DIAS}
