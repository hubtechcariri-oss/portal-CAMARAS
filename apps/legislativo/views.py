from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.core.paginator import Paginator
from django.db.models import Count, F
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from apps.camaras.exportacao import exportar, formato_pedido

from .models import Materia, Norma, Sessao, Vereador

# Configuração criada na migração 0002_busca_sem_acento (ignora acentos).
CONFIG_BUSCA = "portugues"


def vereadores(request):
    lista = Vereador.objects.da_camara(request.camara).filter(em_exercicio=True)
    return render(request, "portal/vereadores/lista.html", {"vereadores": lista})


def vereador(request, pk):
    obj = get_object_or_404(Vereador.objects.da_camara(request.camara), pk=pk)
    materias_autor = obj.materias.filter(publicada=True)
    contexto = {
        "vereador": obj,
        "materias": materias_autor[:10],
        "total_materias": materias_autor.count(),
        "total_presencas": obj.presencas.filter(publicada=True).count(),
    }
    return render(request, "portal/vereadores/detalhe.html", contexto)


def busca_textual(qs, termo):
    """Busca em português sem acento nos campos `ementa` (peso maior) e `texto`."""
    vetor = SearchVector("ementa", weight="A", config=CONFIG_BUSCA) + SearchVector(
        "texto", weight="B", config=CONFIG_BUSCA
    )
    consulta = SearchQuery(termo, config=CONFIG_BUSCA, search_type="websearch")
    return qs.annotate(busca=vetor, rank=SearchRank(vetor, consulta)).filter(busca=consulta).order_by(F("rank").desc())


def _url_arquivo(request, arquivo):
    return request.build_absolute_uri(arquivo.url) if arquivo else ""


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
        qs = busca_textual(qs, termo)

    formato = formato_pedido(request)
    if formato:
        campos = ["tipo", "numero", "ano", "data", "ementa", "url_arquivo"]
        linhas = (
            {
                "tipo": n.get_tipo_display(), "numero": n.numero, "ano": n.ano, "data": n.data,
                "ementa": n.ementa, "url_arquivo": _url_arquivo(request, n.arquivo),
            }
            for n in qs
        )
        return exportar(formato, "legislacao", campos, linhas)

    pagina = Paginator(qs, 20).get_page(request.GET.get("pagina"))
    contexto = {"pagina": pagina, "termo": termo, "tipo": tipo, "ano": ano, "tipos": Norma.Tipo.choices}
    return render(request, "portal/normas/lista.html", contexto)


def sessoes(request):
    qs = Sessao.objects.da_camara(request.camara).filter(publicada=True)
    tipo = request.GET.get("tipo", "")
    ano = request.GET.get("ano", "")
    if tipo in Sessao.Tipo.values:
        qs = qs.filter(tipo=tipo)
    if ano.isdigit():
        qs = qs.filter(data_hora__year=int(ano))
    qs = qs.annotate(n_presentes=Count("presentes"))

    formato = formato_pedido(request)
    if formato:
        campos = ["tipo", "numero", "data_hora", "presentes", "url_pauta", "url_ata", "video_url"]
        linhas = (
            {
                "tipo": s.get_tipo_display(), "numero": s.numero, "data_hora": timezone.localtime(s.data_hora),
                "presentes": s.n_presentes, "url_pauta": _url_arquivo(request, s.pauta),
                "url_ata": _url_arquivo(request, s.ata), "video_url": s.video_url,
            }
            for s in qs
        )
        return exportar(formato, "sessoes", campos, linhas)

    pagina = Paginator(qs, 20).get_page(request.GET.get("pagina"))
    contexto = {"pagina": pagina, "tipo": tipo, "ano": ano, "tipos": Sessao.Tipo.choices}
    return render(request, "portal/sessoes/lista.html", contexto)


def sessao(request, pk):
    obj = get_object_or_404(Sessao.objects.da_camara(request.camara).filter(publicada=True), pk=pk)
    contexto = {
        "sessao": obj,
        "presentes": obj.presentes.all(),
        "deliberacoes": obj.tramitacoes.filter(materia__publicada=True).select_related("materia"),
    }
    return render(request, "portal/sessoes/detalhe.html", contexto)


def materias(request):
    qs = Materia.objects.da_camara(request.camara).filter(publicada=True).prefetch_related("autores")
    termo = request.GET.get("q", "").strip()
    tipo = request.GET.get("tipo", "")
    ano = request.GET.get("ano", "")
    situacao = request.GET.get("situacao", "")
    autor = request.GET.get("autor", "")
    if tipo in Materia.Tipo.values:
        qs = qs.filter(tipo=tipo)
    if ano.isdigit():
        qs = qs.filter(ano=int(ano))
    if situacao in Materia.Situacao.values:
        qs = qs.filter(situacao=situacao)
    if autor.isdigit():
        qs = qs.filter(autores=int(autor))
    if termo:
        qs = busca_textual(qs, termo)

    formato = formato_pedido(request)
    if formato:
        campos = ["tipo", "numero", "ano", "data_apresentacao", "ementa", "autoria", "situacao", "url_arquivo"]
        linhas = (
            {
                "tipo": m.get_tipo_display(), "numero": m.numero, "ano": m.ano,
                "data_apresentacao": m.data_apresentacao, "ementa": m.ementa, "autoria": m.autoria,
                "situacao": m.get_situacao_display(), "url_arquivo": _url_arquivo(request, m.arquivo),
            }
            for m in qs
        )
        return exportar(formato, "materias", campos, linhas)

    pagina = Paginator(qs, 20).get_page(request.GET.get("pagina"))
    contexto = {
        "pagina": pagina, "termo": termo, "tipo": tipo, "ano": ano, "situacao": situacao, "autor": autor,
        "tipos": Materia.Tipo.choices, "situacoes": Materia.Situacao.choices,
        "autores": Vereador.objects.da_camara(request.camara),
    }
    return render(request, "portal/materias/lista.html", contexto)


def materia(request, pk):
    qs = Materia.objects.da_camara(request.camara).filter(publicada=True)
    obj = get_object_or_404(qs, pk=pk)
    tramitacoes = obj.tramitacoes.select_related("sessao")
    return render(request, "portal/materias/detalhe.html", {"materia": obj, "tramitacoes": tramitacoes})
