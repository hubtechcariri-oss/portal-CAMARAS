"""Conector do PNCP (Portal Nacional de Contratações Públicas).

Usa a API pública de Consultas (sem senha), filtrando pelo CNPJ da câmara:
- `/v1/contratacoes/publicacao`: licitações, dispensas e inexigibilidades. A API exige a
  modalidade, então é chamada uma vez por modalidade.
- `/v1/contratos`: contratos e empenhos com força de contrato.

Manual: https://www.gov.br/pncp/pt-br/pncp/manuais/ManualPNCPAPIConsultasVerso1.0.pdf
"""

import json
import time
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from django.utils import timezone

from . import Conector, ErroDeImportacao, Resultado, registrar

BASE = "https://pncp.gov.br/api/consulta/v1/"
# Máximo de registros por página que a API aceita em cada consulta (acima disso, HTTP 400).
TAMANHO_PAGINA = {"contratacoes/publicacao": 50, "contratos": 500}
JANELA_DIAS = 180           # a API recusa (HTTP 422) períodos acima de 365 dias; janelas maiores ficam lentas
TENTATIVAS = 5
INTERVALO = 0.5             # pausa entre requisições: o PNCP limita o ritmo (HTTP 429)
ESPERA_MAXIMA = 60          # segundos, ao obedecer o Retry-After
FUSO = ZoneInfo("America/Sao_Paulo")

MODALIDADES = {
    1: "Leilão eletrônico", 2: "Diálogo competitivo", 3: "Concurso", 4: "Concorrência eletrônica",
    5: "Concorrência presencial", 6: "Pregão eletrônico", 7: "Pregão presencial", 8: "Dispensa de licitação",
    9: "Inexigibilidade", 10: "Manifestação de interesse", 11: "Pré-qualificação", 12: "Credenciamento",
    13: "Leilão presencial",
}


def _digitos(texto):
    return "".join(c for c in (texto or "") if c.isdigit())


def _decimal(valor):
    if valor in (None, ""):
        return None
    try:
        return Decimal(str(valor)).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None


def _data_hora(texto):
    """A API devolve datas sem fuso ("2026-10-15T10:00:00"); são horários de Brasília."""
    if not texto:
        return None
    d = datetime.fromisoformat(texto[:19])
    return d if d.tzinfo else d.replace(tzinfo=FUSO)


def _data(texto):
    return date.fromisoformat(texto[:10]) if texto else None


def janelas(desde, ate, dias=JANELA_DIAS):
    inicio = desde
    while inicio <= ate:
        fim = min(inicio + timedelta(days=dias - 1), ate)
        yield inicio, fim
        inicio = fim + timedelta(days=1)


def buscar_json(caminho, parametros):
    """GET na API. Devolve o JSON, ou None quando não há dados (HTTP 204).

    Tenta de novo em falhas de rede, erros 5xx e no limite de requisições (429), esperando
    o tempo que a API pedir no Retry-After.
    """
    url = BASE + caminho + "?" + urlencode(parametros)
    requisicao = Request(url, headers={"Accept": "application/json", "User-Agent": "PortalDasCamaras/1.0"})
    for tentativa in range(1, TENTATIVAS + 1):
        time.sleep(INTERVALO)
        espera = 2 ** tentativa
        try:
            with urlopen(requisicao, timeout=60) as resposta:
                corpo = resposta.read()
                return json.loads(corpo) if resposta.status != 204 and corpo.strip() else None
        except HTTPError as erro:
            if erro.code == 204:
                return None
            repetivel = erro.code == 429 or erro.code >= 500
            if not repetivel or tentativa == TENTATIVAS:
                raise ErroDeImportacao(f"O PNCP respondeu {erro.code} em {caminho}{_motivo(erro)}.") from erro
            if erro.code == 429:
                espera = max(_retry_after(erro), 5 * tentativa)
        except (URLError, TimeoutError) as erro:
            if tentativa == TENTATIVAS:
                raise ErroDeImportacao(f"Não foi possível acessar o PNCP ({erro}).") from erro
        time.sleep(min(espera, ESPERA_MAXIMA))


def _retry_after(erro):
    try:
        return int((erro.headers or {}).get("Retry-After") or 0)
    except (TypeError, ValueError):
        return 0


def _motivo(erro):
    """A API explica o erro no corpo (ex.: {"message": "Tamanho de página inválido"})."""
    try:
        mensagem = json.loads(erro.read() or b"{}").get("message")
    except (ValueError, AttributeError, OSError):
        return ""
    return f": {mensagem}" if mensagem else ""


def paginas(caminho, parametros):
    """Percorre todas as páginas de uma consulta e devolve os itens."""
    pagina = 1
    while True:
        dados = buscar_json(caminho, {**parametros, "pagina": pagina, "tamanhoPagina": TAMANHO_PAGINA[caminho]})
        if not dados:
            return
        yield from dados.get("data") or []
        if pagina >= (dados.get("totalPaginas") or 1):
            return
        pagina += 1


@registrar("pncp")
class ConectorPNCP(Conector):
    rotulo = "PNCP"

    def importar(self, fonte, desde, ate):
        cnpj = _digitos(fonte.configuracao.get("cnpj") or fonte.camara.cnpj)
        if len(cnpj) != 14:
            raise ErroDeImportacao("Cadastre o CNPJ da câmara (Configurações > Câmaras) para importar do PNCP.")
        resultado = Resultado()
        for inicio, fim in janelas(desde, ate):
            periodo = {"dataInicial": f"{inicio:%Y%m%d}", "dataFinal": f"{fim:%Y%m%d}"}
            for codigo in MODALIDADES:
                for item in paginas("contratacoes/publicacao",
                                    {**periodo, "cnpj": cnpj, "codigoModalidadeContratacao": codigo}):
                    resultado.contar(self.gravar_licitacao(fonte.camara, item, codigo))
            for item in paginas("contratos", {**periodo, "cnpjOrgao": cnpj}):
                resultado.contar(self.gravar_contrato(fonte.camara, item))
        return resultado

    @staticmethod
    def gravar_licitacao(camara, item, codigo_modalidade):
        from apps.transparencia.models import Licitacao

        orgao = item.get("orgaoEntidade") or {}
        cnpj, ano, seq = orgao.get("cnpj", ""), item.get("anoCompra"), item.get("sequencialCompra")
        _, criado = Licitacao.objects.update_or_create(
            camara=camara, origem="pncp", id_origem=item["numeroControlePNCP"],
            defaults={
                "numero": str(item.get("numeroCompra") or ""),
                "ano": ano or date.today().year,
                "processo": item.get("processo") or "",
                "modalidade": item.get("modalidadeNome") or MODALIDADES.get(codigo_modalidade, ""),
                "situacao": item.get("situacaoCompraNome") or "",
                "objeto": item.get("objetoCompra") or "",
                "valor_estimado": _decimal(item.get("valorTotalEstimado")),
                "valor_homologado": _decimal(item.get("valorTotalHomologado")),
                "abertura_propostas": _data_hora(item.get("dataAberturaProposta")),
                "publicada_em": _data_hora(item.get("dataPublicacaoPncp")) or timezone.now(),
                "link_origem": f"https://pncp.gov.br/app/editais/{cnpj}/{ano}/{seq}" if cnpj and ano and seq else "",
                "link_sistema": (item.get("linkSistemaOrigem") or "")[:500],
            },
        )
        return criado

    @staticmethod
    def gravar_contrato(camara, item):
        from apps.transparencia.models import Contrato, Licitacao

        orgao = item.get("orgaoEntidade") or {}
        cnpj, ano, seq = orgao.get("cnpj", ""), item.get("anoContrato"), item.get("sequencialContrato")
        tipo = item.get("tipoContrato") or {}
        licitacao = None
        compra = item.get("numeroControlePncpCompra") or item.get("numeroControlePNCPCompra")
        if compra:
            licitacao = Licitacao.objects.filter(camara=camara, origem="pncp", id_origem=compra).first()
        _, criado = Contrato.objects.update_or_create(
            camara=camara, origem="pncp", id_origem=item["numeroControlePNCP"],
            defaults={
                "licitacao": licitacao,
                "numero": str(item.get("numeroContratoEmpenho") or ""),
                "ano": ano or date.today().year,
                "processo": item.get("processo") or "",
                "tipo": tipo.get("nome") or tipo.get("Nome") or "",
                "objeto": item.get("objetoContrato") or "",
                "fornecedor": item.get("nomeRazaoSocialFornecedor") or "",
                "fornecedor_documento": item.get("niFornecedor") or "",
                "valor_inicial": _decimal(item.get("valorInicial")),
                "valor_global": _decimal(item.get("valorGlobal")),
                "assinatura": _data(item.get("dataAssinatura")),
                "vigencia_inicio": _data(item.get("dataVigenciaInicio")),
                "vigencia_fim": _data(item.get("dataVigenciaFim")),
                "publicado_em": _data_hora(item.get("dataPublicacaoPncp")) or timezone.now(),
                "link_origem": f"https://pncp.gov.br/app/contratos/{cnpj}/{ano}/{seq}" if cnpj and ano and seq else "",
            },
        )
        return criado
