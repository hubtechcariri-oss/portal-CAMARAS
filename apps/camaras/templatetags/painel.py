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


def _fila(modelo, usuario, url_name, rotulo, rotulo_curto="", icone="info"):
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
        "rotulo_curto": rotulo_curto or rotulo,
        "icone": icone,
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
        _fila(Pedido, usuario, "admin:esic_pedido_changelist", "Pedidos de informação (e-SIC)", "e-SIC", "transparencia"),
        _fila(Manifestacao, usuario, "admin:ouvidoria_manifestacao_changelist", "Manifestações da Ouvidoria", "Ouvidoria", "ouvidoria"),
    ]
    atalhos = []
    for perm, rotulo, nome, icone in ATALHOS:
        if usuario.has_perm(perm):
            try:
                atalhos.append({"rotulo": rotulo, "url": reverse(nome), "icone": icone})
            except NoReverseMatch:
                pass
    return {"filas": [f for f in filas if f], "atalhos": atalhos, "alerta_dias": ALERTA_DIAS}


# ---------------------------------------------------------------------------
# Início (tarefa 7): tudo vem do banco, respeitando câmara e permissões.
# ---------------------------------------------------------------------------

def _pode_ver(usuario, modelo):
    return usuario.has_perm(f"{modelo._meta.app_label}.view_{modelo._meta.model_name}")


def _escopo(qs, usuario):
    return qs if usuario.is_superuser else qs.filter(camara__in=camaras_do_usuario(usuario))


def _url_objeto(obj):
    return reverse(f"admin:{obj._meta.app_label}_{obj._meta.model_name}_change", args=[obj.pk])


def _indicadores(usuario, filas):
    from apps.camaras.admin_mixins import UltimosDiasFilter
    from apps.legislativo.models import Sessao
    from apps.noticias.models import Noticia

    itens = []
    for f in filas:
        detalhe = []
        if f["vencidas"]:
            detalhe.append(f"{f['vencidas']} com prazo vencido")
        if f["proximo"]:
            detalhe.append(f"próximo {f['proximo']}")
        itens.append({
            "rotulo": f["rotulo_curto"], "numero": f["abertas"], "unidade": "em aberto",
            "detalhe": " · ".join(detalhe) or "nada aguardando resposta",
            "estado": f["estado"], "rotulo_estado": f["rotulo_estado"], "url": f["url"], "icone": f["icone"],
        })

    if _pode_ver(usuario, Noticia):
        agora = timezone.now()
        dias = UltimosDiasFilter.DIAS
        recentes = _escopo(Noticia.objects.filter(
            publicada=True, publicada_em__gt=agora - timedelta(days=dias), publicada_em__lte=agora), usuario)
        agendadas = _escopo(Noticia.objects.filter(publicada=True, publicada_em__gt=agora), usuario).count()
        itens.append({
            "rotulo": "Notícias", "numero": recentes.count(), "unidade": f"nos últimos {dias} dias",
            "detalhe": f"{agendadas} agendada{'s' if agendadas != 1 else ''}" if agendadas else "nenhuma agendada",
            "estado": "neutro", "rotulo_estado": "",
            "url": reverse("admin:noticias_noticia_changelist") + f"?ultimos_dias={dias}", "icone": "noticia",
        })

    if _pode_ver(usuario, Sessao):
        proxima = _escopo(Sessao.objects.filter(data_hora__gte=timezone.now()), usuario).order_by("data_hora").first()
        if proxima:
            quando = timezone.localtime(proxima.data_hora)
            dias = (quando.date() - timezone.localdate()).days
            itens.append({
                "rotulo": "Próxima sessão", "numero": quando.strftime("%d/%m"), "unidade": quando.strftime("às %Hh%M"),
                "detalhe": f"{proxima} · " + ("hoje" if dias == 0 else "amanhã" if dias == 1 else f"em {dias} dias"),
                "estado": "atencao" if dias <= 1 else "neutro", "rotulo_estado": "",
                "url": _url_objeto(proxima), "icone": "sessao",
            })
        else:
            itens.append({
                "rotulo": "Próxima sessão", "numero": "—", "unidade": "nenhuma agendada",
                "detalhe": "Cadastre a próxima sessão", "estado": "neutro", "rotulo_estado": "",
                "url": reverse("admin:legislativo_sessao_add"), "icone": "sessao",
            })
    return itens


def _prazos(usuario, limite=6):
    from apps.camaras.admin_mixins import selo_do_prazo
    from apps.esic.models import Pedido
    from apps.ouvidoria.models import Manifestacao

    itens, alguma = [], False
    for modelo, tipo in [(Pedido, "e-SIC"), (Manifestacao, "Ouvidoria")]:
        if not _pode_ver(usuario, modelo):
            continue
        alguma = True
        for obj in _escopo(modelo.objects.filter(situacao__in=modelo.ABERTAS), usuario).order_by("prazo")[:limite]:
            itens.append({"tipo": tipo, "titulo": f"Protocolo {obj.protocolo}", "prazo": obj.prazo,
                          "selo": selo_do_prazo(obj), "url": _url_objeto(obj)})
    if not alguma:
        return None  # sem permissão no e-SIC nem na Ouvidoria: o bloco nem aparece
    return sorted(itens, key=lambda i: i["prazo"])[:limite]


def _publicados(usuario, limite=6):
    from apps.legislativo.models import Materia, Norma, Sessao
    from apps.noticias.models import Noticia
    from apps.transparencia.models import Documento

    fontes = [
        (Noticia, "Notícia", {"publicada": True, "publicada_em__lte": timezone.now()}, "publicada_em"),
        (Norma, "Lei ou norma", {"publicada": True}, "criado_em"),
        (Sessao, "Sessão", {"publicada": True}, "criado_em"),
        (Materia, "Matéria", {"publicada": True}, "criado_em"),
        (Documento, "Transparência", {"publicado": True}, "criado_em"),
    ]
    itens = []
    for modelo, tipo, filtro, campo in fontes:
        if not _pode_ver(usuario, modelo):
            continue
        for obj in _escopo(modelo.objects.filter(**filtro), usuario).order_by(f"-{campo}")[:limite]:
            itens.append({"tipo": tipo, "titulo": str(obj), "quando": getattr(obj, campo), "url": _url_objeto(obj)})
    return sorted(itens, key=lambda i: i["quando"], reverse=True)[:limite]


def _atividade(usuario, limite=8):
    from django.contrib.admin.models import LogEntry

    from apps.camaras.models import Membro

    qs = LogEntry.objects.select_related("user", "content_type").order_by("-action_time")
    if not usuario.is_superuser:
        equipe = Membro.objects.filter(camara__in=camaras_do_usuario(usuario)).values("usuario")
        qs = qs.filter(user__in=equipe)
    verbos = {1: "adicionou", 2: "alterou", 3: "removeu"}
    itens = []
    for e in qs[:limite]:
        modelo = e.content_type.model_class() if e.content_type_id else None
        tipo = modelo._meta.verbose_name if modelo else ""
        url = None
        if not e.is_deletion():
            try:
                url = e.get_admin_url()
            except NoReverseMatch:
                url = None
        nome = e.user.get_full_name() or e.user.get_username()
        itens.append({"quem": nome, "inicial": nome[:1].upper(), "verbo": verbos.get(e.action_flag, "alterou"),
                      "tipo": tipo, "objeto": e.object_repr, "quando": e.action_time, "url": url})
    return itens


@register.simple_tag(takes_context=True)
def painel_inicio(context):
    usuario = context["request"].user
    resumo = painel_resumo(context)
    return {
        "indicadores": _indicadores(usuario, resumo["filas"]),
        "prazos": _prazos(usuario),
        "publicados": _publicados(usuario),
        "atividade": _atividade(usuario),
        "atalhos": resumo["atalhos"],
    }


# ---------------------------------------------------------------------------
# Menu lateral (tarefa 8): agrupado por tarefa, a partir de `available_apps`
# (já filtrado pelas permissões do usuário). Modelo não listado cai em "Outros".
# ---------------------------------------------------------------------------

MENU = [
    ("conteudo", "Conteúdo", "noticia", [
        ("noticias.noticia", "Notícias"), ("conteudo.banner", "Banners"), ("conteudo.pagina", "Páginas"),
    ]),
    ("legislativo", "Legislativo", "sessao", [
        ("legislativo.sessao", "Sessões"), ("legislativo.materia", "Matérias"), ("legislativo.norma", "Leis e normas"),
        ("legislativo.vereador", "Vereadores"), ("legislativo.legislatura", "Legislaturas"),
    ]),
    ("transparencia", "Transparência", "transparencia", [
        ("transparencia.documento", "Documentos"), ("transparencia.categoriatransparencia", "Categorias"),
        ("transparencia.grupotransparencia", "Grupos"),
    ]),
    ("atendimento", "Atendimento", "ouvidoria", [
        ("esic.pedido", "e-SIC (pedidos)"), ("ouvidoria.manifestacao", "Ouvidoria"),
    ]),
    ("configuracoes", "Configurações", "engrenagem", [
        ("camaras.identidadeportal", "Brasão, cores e contatos"), ("camaras.camara", "Câmaras"),
        ("auth.user", "Usuários"), ("auth.group", "Grupos e permissões"),
    ]),
]


@register.simple_tag(takes_context=True)
def painel_menu(context):
    from apps.esic.models import Pedido
    from apps.ouvidoria.models import Manifestacao

    request = context.get("request")
    caminho = request.path if request else ""
    modelos = {}
    for app in context.get("available_apps", []):
        for m in app["models"]:
            if m.get("admin_url"):
                modelos[f"{app['app_label']}.{m['object_name'].lower()}"] = m

    usuario = request.user
    contadores = {}
    for modelo, chave in [(Pedido, "esic.pedido"), (Manifestacao, "ouvidoria.manifestacao")]:
        if chave in modelos:
            contadores[chave] = _escopo(modelo.objects.filter(situacao__in=modelo.ABERTAS), usuario).count()

    # Item atual: o endereço de lista mais longo que é prefixo do caminho.
    atual = max((m["admin_url"] for m in modelos.values() if caminho.startswith(m["admin_url"])), key=len, default=None)

    grupos, usados = [], set()
    for chave, rotulo, icone, itens in MENU:
        linhas = []
        for modelo, nome in itens:
            if modelo in modelos:
                usados.add(modelo)
                m = modelos[modelo]
                linhas.append({"rotulo": nome, "url": m["admin_url"], "atual": m["admin_url"] == atual,
                               "contador": contadores.get(modelo)})
        if chave == "configuracoes":
            for modelo, m in modelos.items():  # nada fica de fora: modelos novos aparecem aqui
                if modelo not in usados:
                    linhas.append({"rotulo": m["name"], "url": m["admin_url"], "atual": m["admin_url"] == atual,
                                   "contador": None})
        if linhas:
            total = sum(l["contador"] or 0 for l in linhas)
            grupos.append({"chave": chave, "rotulo": rotulo, "icone": icone, "itens": linhas,
                           "contador": total if chave == "atendimento" else None,
                           "atual": any(l["atual"] for l in linhas)})
    inicio_url = reverse("admin:index")
    return {"inicio": {"url": inicio_url, "atual": caminho == inicio_url}, "grupos": grupos}


# ---------------------------------------------------------------------------
# Dashboard do Início: indicadores do ano (apps/camaras/indicadores.py).
# ---------------------------------------------------------------------------

@register.simple_tag(takes_context=True)
def painel_dashboard(context):
    from apps.camaras import indicadores

    usuario = context["request"].user
    return {
        "atendimento": indicadores.atendimento(usuario),
        "transparencia": indicadores.transparencia(usuario, painel_camara(context)),
        "legislativo": indicadores.legislativo(usuario),
    }
