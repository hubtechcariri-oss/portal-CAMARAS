from django.shortcuts import render

from django.utils import timezone

from apps.conteudo.models import Banner
from apps.legislativo.models import Materia, Sessao, Vereador
from apps.noticias.models import Noticia


def inicio(request):
    camara = request.camara
    contexto = {
        "noticias": Noticia.objects.da_camara(camara)
        .filter(publicada=True, publicada_em__lte=timezone.now())[:3],
        "vereadores": Vereador.objects.da_camara(camara).filter(em_exercicio=True),
        "banners": Banner.vigentes(camara),
        "sessoes": Sessao.objects.da_camara(camara).filter(publicada=True)[:3],
        "materias": Materia.objects.da_camara(camara).filter(publicada=True).prefetch_related("autores")[:4],
    }
    return render(request, "portal/inicio.html", contexto)


def acessibilidade(request):
    return render(request, "portal/acessibilidade.html")


def privacidade(request):
    return render(request, "portal/privacidade.html")
