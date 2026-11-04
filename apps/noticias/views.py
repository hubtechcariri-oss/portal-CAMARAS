import math
import re

from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.utils.html import strip_tags

from .models import Noticia


def _publicadas(request):
    return Noticia.objects.da_camara(request.camara).filter(publicada=True, publicada_em__lte=timezone.now())


def lista(request):
    qs = _publicadas(request)
    anos = [d.year for d in qs.dates("publicada_em", "year", order="DESC")]
    termo = request.GET.get("q", "").strip()
    ano = request.GET.get("ano", "").strip()
    if termo:
        qs = qs.filter(Q(titulo__icontains=termo) | Q(resumo__icontains=termo) | Q(corpo__icontains=termo))
    if ano.isdigit():
        qs = qs.filter(publicada_em__year=int(ano))
    filtrando = bool(termo or ano)
    pagina = Paginator(qs, 9).get_page(request.GET.get("pagina"))
    itens = list(pagina)
    # Na primeira página sem filtro, a notícia mais recente ganha destaque.
    destaque = itens.pop(0) if itens and pagina.number == 1 and not filtrando else None
    return render(request, "portal/noticias/lista.html", {
        "pagina": pagina, "itens": itens, "destaque": destaque,
        "termo": termo, "ano": ano, "anos": anos, "filtrando": filtrando, "total": pagina.paginator.count,
    })


def _minutos_de_leitura(html):
    palavras = len(re.findall(r"\w+", strip_tags(html or "")))
    return max(1, math.ceil(palavras / 200))


def detalhe(request, slug):
    publicadas = _publicadas(request)
    noticia = get_object_or_404(publicadas, slug=slug)
    return render(request, "portal/noticias/detalhe.html", {
        "noticia": noticia,
        "minutos": _minutos_de_leitura(noticia.corpo),
        "outras": publicadas.exclude(pk=noticia.pk)[:3],
        "endereco": request.build_absolute_uri(),
    })
