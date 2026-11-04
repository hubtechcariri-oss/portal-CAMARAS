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


# ---------------------------------------------------------------------------
# 2. Transparência: itens obrigatórios do catálogo (PNTP) com publicação recente
# ---------------------------------------------------------------------------

MESES_ATUALIZADO = 12  # publicação mais antiga que isso conta como desatualizada
LIMITE_PENDENCIAS = 8


def transparencia(usuario, camara):
    """Quantos itens obrigatórios do catálogo a câmara publicou nos últimos 12 meses.

    É uma estimativa para orientar a equipe: a nota oficial do PNTP usa critérios
    próprios (e pesos). Se nenhuma categoria estiver marcada como obrigatória,
    considera o catálogo inteiro e avisa.
    """
    from django.db.models import Max, Q
    from django.urls import reverse

    from apps.transparencia.models import CategoriaTransparencia, Documento

    if camara is None or not _pode_ver(usuario, Documento):
        return None
    if not usuario.is_superuser and not camaras_do_usuario(usuario).filter(pk=camara.pk).exists():
        return None

    categorias = CategoriaTransparencia.objects.filter(obrigatoria=True)
    catalogo_inteiro = not categorias.exists()
    if catalogo_inteiro:
        categorias = CategoriaTransparencia.objects.all()
    categorias = categorias.select_related("grupo").annotate(
        ultima=Max("documentos__data", filter=Q(documentos__camara=camara, documentos__publicado=True))
    )

    hoje = timezone.localdate()
    limite = _inicio_da_serie(hoje, MESES_ATUALIZADO + 1)
    pode_publicar = usuario.has_perm("transparencia.add_documento")
    url_novo = reverse("admin:transparencia_documento_add")

    publicados, pendencias = 0, []
    for c in categorias:
        if c.ultima and c.ultima >= limite:
            publicados += 1
            continue
        pendencias.append({
            "nome": c.nome, "grupo": c.grupo.nome, "base_legal": c.base_legal,
            "estado": "atencao" if c.ultima else "critico",
            "situacao": f"última em {c.ultima:%m/%Y}" if c.ultima else "nada publicado",
            "url": f"{url_novo}?categoria={c.pk}" if pode_publicar else None,
        })

    total = len(categorias)
    pct = _percentual(publicados, total) or 0
    if pct >= 85:
        estado, rotulo_estado = "ok", "Bom"
    elif pct >= 50:
        estado, rotulo_estado = "atencao", "Atenção"
    else:
        estado, rotulo_estado = "critico", "Crítico"
    pendencias.sort(key=lambda p: (p["estado"] != "critico", p["grupo"], p["nome"]))

    return {
        "total": total,
        "publicados": publicados,
        "desatualizados": sum(1 for p in pendencias if p["estado"] == "atencao"),
        "sem_publicacao": sum(1 for p in pendencias if p["estado"] == "critico"),
        "percentual": pct,
        "estado": estado,
        "rotulo_estado": rotulo_estado,
        "pendencias": pendencias[:LIMITE_PENDENCIAS],
        "mais_pendencias": max(len(pendencias) - LIMITE_PENDENCIAS, 0),
        "catalogo_inteiro": catalogo_inteiro,
        "url_lista": reverse("admin:transparencia_documento_changelist"),
        "url_catalogo": (reverse("admin:transparencia_categoriatransparencia_changelist")
                         if usuario.has_perm("transparencia.change_categoriatransparencia") else None),
    }


# ---------------------------------------------------------------------------
# 3. Produção legislativa do ano
# ---------------------------------------------------------------------------

def legislativo(usuario):
    from django.db.models import Count
    from django.urls import reverse

    from apps.legislativo.models import Materia, Norma, Sessao, Vereador

    ver_materias, ver_sessoes, ver_normas = (_pode_ver(usuario, m) for m in (Materia, Sessao, Norma))
    if not (ver_materias or ver_sessoes or ver_normas):
        return None
    hoje = timezone.localdate()
    ano = hoje.year
    numeros = []

    if ver_sessoes:
        realizadas = _escopo(Sessao.objects.filter(data_hora__year=ano, data_hora__lte=timezone.now()), usuario)
        total = realizadas.count()
        # Presença média: presentes ÷ vereadores em exercício da câmara da sessão,
        # só nas sessões que têm lista de presença.
        com_presenca = list(realizadas.annotate(n=Count("presentes")).filter(n__gt=0).values_list("camara_id", "n"))
        por_camara = dict(Vereador.objects.filter(em_exercicio=True, camara_id__in={c for c, _ in com_presenca})
                          .values("camara_id").annotate(n=Count("id")).values_list("camara_id", "n"))
        vagas = sum(por_camara.get(c, 0) for c, _ in com_presenca)
        presenca = _percentual(sum(n for _, n in com_presenca), vagas) if vagas else None
        numeros.append({"rotulo": "Sessões realizadas", "valor": total,
                        "apoio": f"presença média de {presenca}%" if presenca is not None else "sem lista de presença",
                        "url": reverse("admin:legislativo_sessao_changelist") + f"?data_hora__year={ano}"})

    tipos, serie = [], None
    if ver_materias:
        materias = _escopo(Materia.objects.filter(data_apresentacao__year=ano), usuario)
        apresentadas = materias.count()
        aprovadas = materias.filter(situacao=Materia.Situacao.APROVADA).count()
        tramitando = _escopo(Materia.objects.filter(situacao=Materia.Situacao.TRAMITACAO), usuario).count()
        url = reverse("admin:legislativo_materia_changelist")
        numeros.append({"rotulo": "Matérias apresentadas", "valor": apresentadas,
                        "apoio": f"{aprovadas} aprovada{'s' if aprovadas != 1 else ''}", "url": f"{url}?ano={ano}"})
        numeros.append({"rotulo": "Em tramitação", "valor": tramitando, "apoio": "de todos os anos",
                        "url": f"{url}?situacao__exact={Materia.Situacao.TRAMITACAO}"})
        rotulos = dict(Materia.Tipo.choices)
        contagem = list(materias.values("tipo").annotate(n=Count("id")).order_by("-n", "tipo")[:5])
        maior = contagem[0]["n"] if contagem else 0
        tipos = [{"rotulo": rotulos.get(c["tipo"], c["tipo"]), "valor": c["n"],
                  "largura": round(c["n"] * 100 / maior)} for c in contagem]
        datas = _escopo(Materia.objects.filter(data_apresentacao__gte=_inicio_da_serie(hoje)), usuario)
        serie = _serie_mensal(datas.values_list("data_apresentacao", flat=True), hoje)

    if ver_normas:
        normas = _escopo(Norma.objects.filter(ano=ano, publicada=True), usuario).count()
        numeros.append({"rotulo": "Leis e normas", "valor": normas, "apoio": f"publicadas em {ano}",
                        "url": reverse("admin:legislativo_norma_changelist") + f"?ano={ano}"})

    return {"ano": ano, "numeros": numeros, "tipos": tipos, "serie": serie}
