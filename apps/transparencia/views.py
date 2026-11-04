from django.core.paginator import Paginator
from django.db.models import Count
from django.shortcuts import get_object_or_404, render

from apps.camaras.exportacao import exportar, formato_pedido

from . import importados
from .models import CategoriaTransparencia, Documento, GrupoTransparencia


def indice(request):
    contagens = dict(
        Documento.objects.da_camara(request.camara)
        .filter(publicado=True)
        .values("categoria_id")
        .annotate(n=Count("id"))
        .values_list("categoria_id", "n")
    )
    importados_ = importados.contagens(request.camara)
    grupos = list(GrupoTransparencia.objects.prefetch_related("categorias"))
    for grupo in grupos:
        for cat in grupo.categorias.all():
            cat.total = contagens.get(cat.pk, 0) + importados_.get(cat.slug, 0)
    return render(request, "portal/transparencia/indice.html", {"grupos": grupos})


CAMPOS_EXPORTACAO = {
    "licitacao": ["modalidade", "numero", "ano", "processo", "situacao", "objeto", "valor_estimado",
                  "valor_homologado", "abertura_propostas", "publicada_em", "link_origem", "link_sistema"],
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
    return render(request, "portal/transparencia/importados.html", {
        "categoria": cat, "pagina": Paginator(qs, 20).get_page(request.GET.get("pagina")),
        "contratos": registros.model._meta.model_name == "contrato", "total": qs.count(),
        "termo": termo, "ano": ano, "anos": anos, "modalidade": modalidade, "modalidades": modalidades,
        "documentos": documentos,
    })
