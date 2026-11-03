"""Indicadores do Início do painel (dashboard): números do ano, sempre do banco.

Cada função recebe o usuário e devolve None quando ele não pode ver aquela área,
para o bloco nem aparecer. Os dados respeitam a câmara do usuário (superusuário vê
todas). Os volumes de uma câmara são pequenos (centenas de registros por ano),
então parte das contas é feita em Python, o que mantém o código simples.
"""

from datetime import date

from django.utils import timezone

from apps.camaras.admin_mixins import camaras_do_usuario

MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
MESES_NA_SERIE = 12


def _pode_ver(usuario, modelo):
    return usuario.has_perm(f"{modelo._meta.app_label}.view_{modelo._meta.model_name}")


def _escopo(qs, usuario):
    return qs if usuario.is_superuser else qs.filter(camara__in=camaras_do_usuario(usuario))


def _inicio_da_serie(hoje, meses=MESES_NA_SERIE):
    """Primeiro dia do mês, `meses - 1` meses antes do mês atual."""
    total = hoje.year * 12 + hoje.month - 1 - (meses - 1)
    return date(total // 12, total % 12 + 1, 1)


def _serie_mensal(datas, hoje, meses=MESES_NA_SERIE):
    """Conta por mês, do mais antigo ao atual. Cada barra já sai com a altura em %."""
    inicio = _inicio_da_serie(hoje, meses)
    contagem = {}
    for d in datas:
        contagem[(d.year, d.month)] = contagem.get((d.year, d.month), 0) + 1
    barras, ano, mes = [], inicio.year, inicio.month
    for _ in range(meses):
        barras.append({"rotulo": MESES[mes - 1], "ano": ano, "valor": contagem.get((ano, mes), 0)})
        ano, mes = (ano + 1, 1) if mes == 12 else (ano, mes + 1)
    maior = max((b["valor"] for b in barras), default=0)
    for b in barras:
        b["altura"] = round(b["valor"] * 100 / maior) if maior else 0
    return {"barras": barras, "maior": maior, "total": sum(b["valor"] for b in barras)}


def _percentual(parte, todo):
    return round(parte * 100 / todo) if todo else None


# ---------------------------------------------------------------------------
# 1. Atendimento ao cidadão: prazos da LAI (e-SIC) e da Ouvidoria
# ---------------------------------------------------------------------------

def _fila_atendimento(modelo, usuario, campo_resposta, rotulo, url_name):
    from django.urls import reverse

    hoje = timezone.localdate()
    inicio = _inicio_da_serie(hoje)
    qs = _escopo(modelo.objects.filter(criado_em__date__gte=inicio), usuario)
    linhas = list(qs.values_list("criado_em", campo_resposta, "prazo", "situacao"))

    criados = [timezone.localtime(c).date() for c, _, _, _ in linhas]
    concluidos = [(timezone.localtime(c), timezone.localtime(r), p) for c, r, p, _ in linhas if r]
    no_prazo = sum(1 for _, r, p in concluidos if r.date() <= p)
    dias = [(r.date() - c.date()).days for c, r, _ in concluidos]
    vencidos = sum(1 for _, r, p, s in linhas if not r and s in modelo.ABERTAS and p < hoje)

    pct = _percentual(no_prazo, len(concluidos))
    if pct is None:
        estado, rotulo_estado = "neutro", "Sem respostas"
    elif pct >= 90:
        estado, rotulo_estado = "ok", "Bom"
    elif pct >= 70:
        estado, rotulo_estado = "atencao", "Atenção"
    else:
        estado, rotulo_estado = "critico", "Crítico"

    return {
        "rotulo": rotulo,
        "recebidos": len(linhas),
        "concluidos": len(concluidos),
        "no_prazo": no_prazo,
        "percentual_no_prazo": pct,
        "tempo_medio": round(sum(dias) / len(dias)) if dias else None,
        "vencidos": vencidos,
        "estado": estado,
        "rotulo_estado": rotulo_estado,
        "serie": _serie_mensal(criados, hoje),
        "url": reverse(url_name),
    }


def atendimento(usuario):
    from apps.esic.models import Pedido
    from apps.ouvidoria.models import Manifestacao

    filas = []
    if _pode_ver(usuario, Pedido):
        filas.append(_fila_atendimento(Pedido, usuario, "respondido_em", "e-SIC (pedidos de informação)",
                                       "admin:esic_pedido_changelist"))
    if _pode_ver(usuario, Manifestacao):
        filas.append(_fila_atendimento(Manifestacao, usuario, "respondida_em", "Ouvidoria (manifestações)",
                                       "admin:ouvidoria_manifestacao_changelist"))
    return filas or None
