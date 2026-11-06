from django.core.paginator import Paginator
from django.db.models import Count, Max, Sum
from django.shortcuts import get_object_or_404, render
from django.utils.text import slugify

from apps.camaras.exportacao import exportar, formato_pedido

from . import importados
from .models import CategoriaTransparencia, Documento, GrupoTransparencia


# Ícone de cada grupo do catálogo (pelo slug do nome); grupos novos usam o ícone geral.
ICONES_GRUPO = {
    "atendimento-ao-cidadao": "info", "institucional": "predio", "execucao-orcamentaria-e-financeira": "dinheiro",
    "gestao-fiscal-e-prestacao-de-contas": "grafico", "pessoal": "pessoas", "licitacoes-e-contratos": "licitacao",
    "atos-administrativos": "documento",
}
# Itens mais procurados, em destaque no topo (só os que existem no catálogo).
DESTAQUES = [
    ("receitas", "dinheiro"), ("despesas", "grafico"), ("licitacoes", "licitacao"), ("contratos", "documento"),
    ("quadro-de-pessoal-e-remuneracao", "pessoas"), ("diarias", "diaria"),
]


def indice(request):
    publicados = Documento.objects.da_camara(request.camara).filter(publicado=True)
    contagens = dict(publicados.values("categoria_id").annotate(n=Count("id")).values_list("categoria_id", "n"))
    importados_ = importados.contagens(request.camara)
    grupos = list(GrupoTransparencia.objects.prefetch_related("categorias"))
    por_slug = {}
    for grupo in grupos:
        grupo.icone = f"portal/icones/{ICONES_GRUPO.get(slugify(grupo.nome), 'transparencia')}.svg"
        grupo.total = 0
        for cat in grupo.categorias.all():
            cat.total = contagens.get(cat.pk, 0) + importados_.get(cat.slug, 0)
            grupo.total += cat.total
            por_slug[cat.slug] = cat
    destaques = [(por_slug[slug], f"portal/icones/{icone}.svg") for slug, icone in DESTAQUES if slug in por_slug]

    datas = [d for d in [publicados.aggregate(m=Max("data"))["m"], *importados.ultimas_datas(request.camara).values()] if d]
    return render(request, "portal/transparencia/indice.html", {
        "grupos": grupos, "destaques": destaques,
        "total_publicacoes": sum(contagens.values()), "total_importados": sum(importados_.values()),
        "atualizado_em": max(datas) if datas else None,
    })


CAMPOS_EXPORTACAO = {
    "licitacao": ["modalidade", "numero", "ano", "processo", "situacao", "objeto", "valor_estimado",
                  "valor_homologado", "abertura_propostas", "publicada_em", "link_origem", "link_sistema"],
    "despesa": ["ano", "numero_empenho", "data_empenho", "elemento", "historico", "fornecedor", "fornecedor_documento",
                "numero_contrato", "numero_licitacao", "valor_empenhado", "valor_liquidado", "valor_pago"],
    "receita": ["ano", "competencia", "descricao", "conta", "valor_mes", "valor_acumulado"],
    "contrato": ["tipo", "numero", "ano", "processo", "objeto", "fornecedor", "fornecedor_documento", "valor_inicial",
                 "valor_global", "assinatura", "vigencia_inicio", "vigencia_fim", "publicado_em", "link_origem"],
}


def _exportar_importados(formato, slug, qs):
    campos = CAMPOS_EXPORTACAO[qs.model._meta.model_name]

    def linha(obj):
        dados = {c: getattr(obj, c) for c in campos}
        if "fornecedor_documento" in dados:
            dados["fornecedor_documento"] = obj.fornecedor_documento_publico  # CPF mascarado também no CSV
        return dados

    return exportar(formato, slug, campos, (linha(o) for o in qs.iterator()))


def categoria(request, slug):
    cat = get_object_or_404(CategoriaTransparencia, slug=slug)
    registros = importados.registros(request.camara, slug)
    if registros is not None and registros.exists():
        return categoria_com_importados(request, cat, registros)
    qs = Documento.objects.da_camara(request.camara).filter(categoria=cat, publicado=True)

    formato = formato_pedido(request)
    if formato:
        campos = ["titulo", "numero", "data", "competencia", "valor", "descricao", "url_arquivo", "link_externo"]
        linhas = (
            {
                **{c: getattr(d, c) for c in campos if hasattr(d, c)},
                "url_arquivo": request.build_absolute_uri(d.arquivo.url) if d.arquivo else "",
            }
            for d in qs
        )
        return exportar(formato, cat.slug, campos, linhas)

    pagina = Paginator(qs, 20).get_page(request.GET.get("pagina"))
    return render(request, "portal/transparencia/categoria.html", {"categoria": cat, "pagina": pagina})


def categoria_com_importados(request, cat, registros):
    """Licitações, dispensas e contratos: tabela dos dados importados (PNCP), com busca e filtros,
    seguida dos documentos enviados à mão (editais, atas…), se houver."""
    termo = request.GET.get("q", "").strip()
    ano = request.GET.get("ano", "").strip()
    modalidade = request.GET.get("modalidade", "").strip()
    anos = sorted(set(registros.values_list("ano", flat=True)), reverse=True)
    modalidades = sorted(set(registros.values_list("modalidade", flat=True))) if hasattr(registros.model, "modalidade") else []
    qs = importados.filtrar(registros, cat.slug, termo, ano, modalidade)

    formato = formato_pedido(request)
    if formato:
        return _exportar_importados(formato, cat.slug, qs)

    documentos = Documento.objects.da_camara(request.camara).filter(categoria=cat, publicado=True)[:50]
    modelo = registros.model._meta.model_name
    return render(request, "portal/transparencia/importados.html", {
        "categoria": cat, "pagina": Paginator(qs, 20).get_page(request.GET.get("pagina")),
        "contratos": modelo == "contrato", "despesas": modelo == "despesa", "receitas": modelo == "receita",
        "origens": set(registros.values_list("origem", flat=True).distinct()), "total": qs.count(),
        "somas": qs.aggregate(empenhado=Sum("valor_empenhado"), liquidado=Sum("valor_liquidado"), pago=Sum("valor_pago"))
        if modelo == "despesa" else None,
        "recebido": qs.aggregate(t=Sum("valor_mes"))["t"] if modelo == "receita" else None,
        "termo": termo, "ano": ano, "anos": anos, "modalidade": modalidade, "modalidades": modalidades,
        "documentos": documentos,
    })
