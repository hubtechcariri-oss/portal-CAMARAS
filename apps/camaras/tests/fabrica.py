from datetime import date

from apps.camaras.models import Camara, Dominio


def criar_camara(host="camara-a.test", nome="Câmara Municipal A"):
    camara = Camara.objects.create(nome=nome, municipio=nome.split()[-1], uf="CE")
    Dominio.objects.create(camara=camara, host=host, principal=True)
    return camara


HOJE = date(2026, 11, 3)
