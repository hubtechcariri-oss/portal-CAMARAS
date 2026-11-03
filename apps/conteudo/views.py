from django.shortcuts import get_object_or_404, render

from apps.legislativo.models import Vereador

from .models import Pagina


def pagina(request, slug):
    obj = get_object_or_404(Pagina.objects.da_camara(request.camara).filter(publicada=True), slug=slug)
    return render(request, "portal/pagina.html", {"pagina": obj})


def mesa_diretora(request):
    membros = list(Vereador.objects.da_camara(request.camara).filter(em_exercicio=True).exclude(cargo_mesa=""))
    ordem = ["presidente", "vice", "1", "primeir", "2", "segund", "3", "terceir"]

    def posicao(v):
        cargo = v.cargo_mesa.lower()
        return next((i for i, p in enumerate(ordem) if cargo.startswith(p)), len(ordem))

    membros.sort(key=posicao)
    return render(request, "portal/mesa_diretora.html", {"membros": membros})
