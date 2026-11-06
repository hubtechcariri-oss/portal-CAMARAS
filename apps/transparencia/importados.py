"""Dados estruturados importados (PNCP etc.) que alimentam categorias do catálogo de transparência.

Cada categoria abaixo mostra, além dos documentos enviados à mão, a tabela de registros importados.
"""

from django.db.models import Max, Q
from django.utils import timezone

from .models import Contrato, Despesa, Licitacao, Receita

DISPENSAS = Q(modalidade__icontains="dispensa") | Q(modalidade__icontains="inexigib")


def _licitacoes(camara):
    return Licitacao.objects.da_camara(camara).exclude(DISPENSAS)


def _dispensas(camara):
    return Licitacao.objects.da_camara(camara).filter(DISPENSAS)


def _contratos(camara):
    return Contrato.objects.da_camara(camara).select_related("licitacao")


DIARIAS = Q(elemento__regex=r"^[0-9]{4}1[45]")  # elemento 14 (diárias civis) ou 15 (militares)


def _despesas(camara):
    return Despesa.objects.da_camara(camara)


def _diarias(camara):
    return Despesa.objects.da_camara(camara).filter(DIARIAS)


def _receitas(camara):
    return Receita.objects.da_camara(camara)


# slug da categoria -> (consulta, campo de data, campos de busca)
CATEGORIAS = {
    "licitacoes": (_licitacoes, "publicada_em", ["objeto", "numero", "processo"]),
    "dispensas-e-inexigibilidades": (_dispensas, "publicada_em", ["objeto", "numero", "processo"]),
    "contratos": (_contratos, "publicado_em", ["objeto", "numero", "processo", "fornecedor", "fornecedor_documento"]),
    "despesas": (_despesas, "data_empenho", ["historico", "numero_empenho", "fornecedor", "fornecedor_documento"]),
    "diarias": (_diarias, "data_empenho", ["historico", "numero_empenho", "fornecedor"]),
    "receitas": (_receitas, "competencia", ["descricao", "conta"]),
}


def registros(camara, slug):
    """Consulta dos registros importados da categoria, ou None se ela não tem dados importados."""
    if slug not in CATEGORIAS:
        return None
    return CATEGORIAS[slug][0](camara)


def filtrar(qs, slug, termo="", ano="", modalidade=""):
    _, _, campos = CATEGORIAS[slug]
    if termo:
        filtro = Q()
        for campo in campos:
            filtro |= Q(**{f"{campo}__icontains": termo})
        qs = qs.filter(filtro)
    if ano.isdigit():
        qs = qs.filter(ano=int(ano))
    if modalidade and qs.model is Licitacao:
        qs = qs.filter(modalidade=modalidade)
    return qs


def contagens(camara):
    """{slug: quantidade} das categorias com dados importados."""
    return {slug: registros(camara, slug).count() for slug in CATEGORIAS}


def ultimas_datas(camara):
    """{slug: data do registro importado mais recente}, para o indicador de transparência."""
    datas = {}
    for slug, (consulta, campo, _) in CATEGORIAS.items():
        ultima = consulta(camara).aggregate(m=Max(campo))["m"]
        if ultima:
            datas[slug] = timezone.localtime(ultima).date() if hasattr(ultima, "hour") else ultima
    return datas
