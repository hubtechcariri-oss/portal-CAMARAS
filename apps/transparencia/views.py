from django.core.paginator import Paginator
from django.db.models import Count
from django.shortcuts import get_object_or_404, render

from apps.camaras.exportacao import exportar, formato_pedido

from .models import CategoriaTransparencia, Documento, GrupoTransparencia


def indice(request):
    contagens = dict(
        Documento.objects.da_camara(request.camara)
        .filter(publicado=True)
        .values("categoria_id")
        .annotate(n=Count("id"))
        .values_list("categoria_id", "n")
    )
    grupos = list(GrupoTransparencia.objects.prefetch_related("categorias"))
    for grupo in grupos:
        for cat in grupo.categorias.all():
            cat.total = contagens.get(cat.pk, 0)
    return render(request, "portal/transparencia/indice.html", {"grupos": grupos})


def categoria(request, slug):
    cat = get_object_or_404(CategoriaTransparencia, slug=slug)
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
