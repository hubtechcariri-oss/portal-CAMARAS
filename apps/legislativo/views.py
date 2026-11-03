from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.core.paginator import Paginator
from django.db.models import F
from django.shortcuts import get_object_or_404, render

from apps.camaras.exportacao import exportar, formato_pedido

from .models import Norma, Vereador

# Configuração criada na migração 0002_busca_sem_acento (ignora acentos).
CONFIG_BUSCA = "portugues"


def vereadores(request):
    lista = Vereador.objects.da_camara(request.camara).filter(em_exercicio=True)
    return render(request, "portal/vereadores/lista.html", {"vereadores": lista})


def vereador(request, pk):
    obj = get_object_or_404(Vereador.objects.da_camara(request.camara), pk=pk)
    return render(request, "portal/vereadores/detalhe.html", {"vereador": obj})


def normas(request):
    qs = Norma.objects.da_camara(request.camara).filter(publicada=True)
    termo = request.GET.get("q", "").strip()
    tipo = request.GET.get("tipo", "")
    ano = request.GET.get("ano", "")
    if tipo in Norma.Tipo.values:
        qs = qs.filter(tipo=tipo)
    if ano.isdigit():
        qs = qs.filter(ano=int(ano))
    if termo:
        vetor = SearchVector("ementa", weight="A", config=CONFIG_BUSCA) + SearchVector(
            "texto", weight="B", config=CONFIG_BUSCA
        )
        consulta = SearchQuery(termo, config=CONFIG_BUSCA, search_type="websearch")
        qs = (
            qs.annotate(busca=vetor, rank=SearchRank(vetor, consulta))
            .filter(busca=consulta)
            .order_by(F("rank").desc(), "-data")
        )

    formato = formato_pedido(request)
    if formato:
        campos = ["tipo", "numero", "ano", "data", "ementa", "url_arquivo"]
        linhas = (
            {
                "tipo": n.get_tipo_display(), "numero": n.numero, "ano": n.ano, "data": n.data,
                "ementa": n.ementa,
                "url_arquivo": request.build_absolute_uri(n.arquivo.url) if n.arquivo else "",
            }
            for n in qs
        )
        return exportar(formato, "legislacao", campos, linhas)

    pagina = Paginator(qs, 20).get_page(request.GET.get("pagina"))
    contexto = {"pagina": pagina, "termo": termo, "tipo": tipo, "ano": ano, "tipos": Norma.Tipo.choices}
    return render(request, "portal/normas/lista.html", contexto)
