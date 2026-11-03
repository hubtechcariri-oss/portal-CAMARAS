from django.http import Http404

from .models import Dominio

# Caminhos que não dependem de uma câmara (painel da plataforma, arquivos estáticos).
CAMINHOS_SEM_CAMARA = ("/admin/", "/static/", "/media/")


def resolver_camara(host):
    host = host.split(":")[0].lower()
    dominio = Dominio.objects.select_related("camara").filter(host=host, camara__ativa=True).first()
    return dominio.camara if dominio else None


class CamaraMiddleware:
    """Identifica a câmara pelo domínio da requisição e a expõe em `request.camara`."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith(CAMINHOS_SEM_CAMARA):
            request.camara = None
        else:
            request.camara = resolver_camara(request.get_host())
            if request.camara is None:
                raise Http404("Nenhuma câmara configurada para este domínio.")
        return self.get_response(request)
