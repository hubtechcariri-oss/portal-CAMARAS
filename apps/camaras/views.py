from django.shortcuts import render

from apps.legislativo.models import Vereador
from apps.noticias.models import Noticia
from django.utils import timezone


def inicio(request):
    camara = request.camara
    contexto = {
        "noticias": Noticia.objects.da_camara(camara)
        .filter(publicada=True, publicada_em__lte=timezone.now())[:3],
        "vereadores": Vereador.objects.da_camara(camara).filter(em_exercicio=True),
    }
    return render(request, "portal/inicio.html", contexto)


def acessibilidade(request):
    return render(request, "portal/acessibilidade.html")


def privacidade(request):
    return render(request, "portal/privacidade.html")
