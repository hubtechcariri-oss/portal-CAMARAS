from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from .models import Noticia


def _publicadas(request):
    return Noticia.objects.da_camara(request.camara).filter(publicada=True, publicada_em__lte=timezone.now())


def lista(request):
    pagina = Paginator(_publicadas(request), 10).get_page(request.GET.get("pagina"))
    return render(request, "portal/noticias/lista.html", {"pagina": pagina})


def detalhe(request, slug):
    noticia = get_object_or_404(_publicadas(request), slug=slug)
    return render(request, "portal/noticias/detalhe.html", {"noticia": noticia})
