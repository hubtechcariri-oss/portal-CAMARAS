"""Conector do SIM/TCE-CE (API de Dados Abertos do Tribunal de Contas do Estado do Ceará).

Traz da câmara:
- despesas: notas de empenho, liquidações e pagamentos (as diárias são os empenhos do elemento 14);
- receitas: o repasse mensal do duodécimo (balancete contábil, conta 4.5.1.1.2, transferências recebidas);
- licitações, dispensas e inexigibilidades: os processos de contratação com dotação da câmara;
- contratos e aditivos ligados a esses processos, com o contratado.
Documentação: https://api-dados-abertos.tce.ce.gov.br/sim/

O que a API exige (conferido ao vivo em 11/2026):
- `codigo_municipio` é o código do TCE (Aratuba = "017"), não o do IBGE; achamos pelo IBGE.
- `exercicio_orcamento` vai como AAAA00 (2026 → 202600); só AAAA devolve lista vazia, sem erro.
- `data_referencia_doc` é o mês de envio AAAAMM. Os municípios enviam com cerca de um mês de atraso.
- A câmara é um órgão dentro do município; achamos pelo CNPJ (`cgc_orgao`) ou pelo tipo 02 (Legislativo).
- No máximo 1000 registros por página (`$count`), avançando com `$start_index`.
- Erros vêm em `__errors__`; os dados, em `elements`.
- Processos, contratos e contratados são do município inteiro, sem órgão, e as datas vão como AAAAMMDD
  (o formato AAAA-MM-DD da documentação dá erro). A câmara se acha pelas dotações do órgão.
"""

import json
import time
import unicodedata
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from . import Conector, ErroDeImportacao, Resultado, registrar

BASE = "https://api-dados-abertos.tce.ce.gov.br/sim/"
POR_PAGINA = 1000
TENTATIVAS = 4
INTERVALO = 0.3
TEMPO_LIMITE = 45
TENTATIVAS_SEM_RESPOSTA = 2  # se o TCE nem responde (servidor fora do Brasil, rede bloqueada), desiste logo
MESES_DE_ATRASO = 3  # mesmo numa importação diária, relê os últimos meses: o TCE recebe os dados com atraso
TIPO_LEGISLATIVO = "02"
CONTA_REPASSE = "4511"  # 4.5.1.1 transferências financeiras recebidas (duodécimo)
ESPECIES = {"D": "Dispensa", "I": "Inexigibilidade", "R": "Adesão a ata de registro de preços"}
MODALIDADES = {"1": "Leilão", "2": "Diálogo competitivo", "3": "Concorrência", "6": "Pregão", "7": "Pregão",
               "12": "Credenciamento"}
TIPOS_CONTRATO = {"OR": "Contrato", "AA": "Termo aditivo", "PA": "Termo aditivo"}


def _digitos(texto):
    return "".join(c for c in (texto or "") if c.isdigit())


def _decimal(valor):
    try:
        return Decimal(str(valor)).quantize(Decimal("0.01")) if valor not in (None, "") else Decimal("0")
    except InvalidOperation:
        return Decimal("0")


def _data(texto):
    return date.fromisoformat(texto[:10]) if texto else None


def meses(desde, ate):
    """[(ano, mes), ...] de `desde` até `ate`, inclusive."""
    ano, mes = desde.year, desde.month
    while (ano, mes) <= (ate.year, ate.month):
        yield ano, mes
        ano, mes = (ano + 1, 1) if mes == 12 else (ano, mes + 1)


def voltar_meses(dia, n):
    """Primeiro dia do mês `n` meses antes do mês de `dia`."""
    total = dia.year * 12 + dia.month - 1 - n
    return date(total // 12, total % 12 + 1, 1)


def buscar(caminho, parametros):
    """Todas as páginas de uma consulta. Levanta ErroDeImportacao com a mensagem do TCE."""
    itens, inicio = [], 0
    while True:
        pagina = _get(caminho, {**parametros, "$count": POR_PAGINA, "$start_index": inicio})
        itens.extend(pagina)
        if len(pagina) < POR_PAGINA:
            return itens
        inicio += POR_PAGINA


def _get(caminho, parametros):
    url = BASE + caminho + "?" + urlencode(parametros)
    requisicao = Request(url, headers={"Accept": "application/json", "User-Agent": "PortalDasCamaras/1.0"})
    for tentativa in range(1, TENTATIVAS + 1):
        time.sleep(INTERVALO)
        try:
            with urlopen(requisicao, timeout=TEMPO_LIMITE) as resposta:
                corpo = json.loads(resposta.read() or b"{}")
            if corpo.get("__errors__"):
                raise ErroDeImportacao(f"O TCE-CE recusou a consulta {caminho}: {corpo['__errors__'][0].get('message')}")
            return corpo.get("elements") or []
        except HTTPError as erro:
            if erro.code == 404:
                raise ErroDeImportacao(f"O TCE-CE está sem o conjunto {caminho} agora (HTTP 404). "
                                       "Costuma voltar sozinho; a próxima importação tenta de novo.") from erro
            if (erro.code < 500 and erro.code != 429) or tentativa == TENTATIVAS:
                raise ErroDeImportacao(f"O TCE-CE respondeu {erro.code} em {caminho}.") from erro
        except (URLError, TimeoutError) as erro:
            if tentativa >= TENTATIVAS_SEM_RESPOSTA:
                raise ErroDeImportacao(
                    f"Não foi possível acessar o TCE-CE ({erro}). A API do TCE-CE costuma recusar conexões "
                    "de servidores fora do Brasil; rode a importação num servidor hospedado no Brasil.") from erro
        time.sleep(min(2 ** tentativa, 30))


def codigo_municipio(camara, configuracao):
    if configuracao.get("codigo_municipio"):
        return str(configuracao["codigo_municipio"]).zfill(3)
    ibge = _digitos(configuracao.get("codigo_ibge") or getattr(camara, "codigo_ibge", ""))
    if ibge:
        achados = buscar("municipios", {"codigo_municipio_ibge": ibge})
    else:
        nome = unicodedata.normalize("NFKD", camara.municipio).encode("ascii", "ignore").decode().upper()
        achados = buscar("municipios", {"nome_municipio": nome})
    if len(achados) != 1:
        raise ErroDeImportacao(
            f"Não achei o município “{camara.municipio}” no TCE-CE. Informe o código do TCE em "
            "Fontes de dados > configuração, assim: {\"codigo_municipio\": \"017\"}.")
    return achados[0]["codigo_municipio"]


def codigo_orgao(municipio, ano, cnpj, configuracao):
    if configuracao.get("codigo_orgao"):
        return str(configuracao["codigo_orgao"])
    orgaos = buscar("orgaos", {"codigo_municipio": municipio, "exercicio_orcamento": ano * 100})
    pelo_cnpj = [o for o in orgaos if cnpj and _digitos(o.get("cgc_orgao")) == cnpj]
    legislativo = [o for o in orgaos if o.get("codigo_tipo_unidade") == TIPO_LEGISLATIVO]
    escolhidos = pelo_cnpj or legislativo
    if len(escolhidos) != 1:
        raise ErroDeImportacao(
            f"Não identifiquei a câmara entre os {len(orgaos)} órgãos do município no TCE-CE em {ano}. "
            "Informe o código em Fontes de dados > configuração, assim: {\"codigo_orgao\": \"11\"}.")
    return escolhidos[0]["codigo_orgao"]


def _momento(texto):
    """Data/hora do TCE (sem fuso) como datetime no fuso da aplicação."""
    from django.utils import timezone

    if not texto:
        return None
    return timezone.make_aware(datetime.fromisoformat(texto[:19]))


def _texto(valor):
    return (valor or "").strip()


def _dia(d):
    return d.strftime("%Y%m%d")


def modalidade(processo):
    especie = _texto(processo.get("modalidade_processo_administrativo"))
    if especie in ESPECIES:
        return ESPECIES[especie]
    nome = MODALIDADES.get(_texto(processo.get("modalidade_licitacao")), "Licitação")
    if nome == "Pregão":
        nome += " eletrônico" if _texto(processo.get("tipo_forma_contratacao")) == "E" else " presencial"
    return nome


def chave_empenho(item):
    unidade = (item.get("codigo_unidade_orcamentaria") or "").strip()
    return f"{item['exercicio_orcamento'] // 100}-{item['codigo_orgao']}-{unidade}-" \
           f"{(item.get('data_emissao_empenho') or '')[:10]}-{item['numero_empenho']}"


@registrar("tce-ce")
class ConectorTCECE(Conector):
    rotulo = "TCE-CE"

    def importar(self, fonte, desde, ate):
        camara, config = fonte.camara, fonte.configuracao or {}
        cnpj = _digitos(config.get("cnpj") or camara.cnpj)
        municipio = codigo_municipio(camara, config)
        resultado = Resultado()
        tocadas = set()
        orgaos = {}
        desde = min(desde, voltar_meses(ate, MESES_DE_ATRASO - 1))

        for ano, mes in meses(desde, ate):
            if ano not in orgaos:
                orgaos[ano] = codigo_orgao(municipio, ano, cnpj, config)
            filtro = {"codigo_municipio": municipio, "exercicio_orcamento": ano * 100,
                      "codigo_orgao": orgaos[ano], "data_referencia_doc": ano * 100 + mes}
            for item in buscar("notas_empenhos", filtro):
                despesa, criada = self.gravar_empenho(camara, item)
                resultado.contar(criada)
                tocadas.add(despesa.pk)
            for caminho, tipo in (("liquidacoes", "L"), ("notas_pagamentos", "P")):
                for item in buscar(caminho, filtro):
                    despesa = self.gravar_movimento(camara, item, tipo)
                    if despesa is None:
                        resultado.avisos.append(f"{caminho}: empenho {item.get('numero_empenho')} não encontrado.")
                    else:
                        tocadas.add(despesa.pk)
            for item in buscar("balancetes_contabeis", filtro):
                if _texto(item.get("codigo_conta_contabil")).startswith(CONTA_REPASSE):
                    resultado.contar(self.gravar_repasse(camara, item)[1])

        self.importar_contratacoes(camara, municipio, set(orgaos.values()), desde, ate, resultado)

        from apps.transparencia.models import Despesa

        for despesa in Despesa.objects.filter(pk__in=tocadas):
            despesa.recalcular()
            despesa.save(update_fields=["valor_liquidado", "valor_pago"])
        if len(resultado.avisos) > 20:
            resultado.avisos = resultado.avisos[:20] + [f"… e mais {len(resultado.avisos) - 20} avisos."]
        return resultado

    def importar_contratacoes(self, camara, municipio, orgaos, desde, ate, resultado):
        """Licitações e contratos são do município inteiro: ficam só os processos com dotação da câmara."""
        from apps.transparencia.models import Licitacao

        periodo = {"codigo_municipio": municipio, "data_inicio": _dia(desde), "data_fim": _dia(ate)}
        da_camara = {_texto(d.get("numero_licitacao")) for orgao in orgaos
                     for d in buscar("dotacoes_utilizadas_contratacoes", {**periodo, "codigo_orgao": orgao})}
        for processo in buscar("processos_administrativos_contratacoes", periodo):
            if _texto(processo.get("numero_licitacao")) in da_camara:
                resultado.contar(self.gravar_processo(camara, processo)[1])

        processos = set(Licitacao.objects.filter(camara=camara, origem="tce-ce").values_list("processo", flat=True))
        contratados = {(_texto(c.get("numero_contrato")), (c.get("data_contrato") or "")[:10]): c
                       for c in buscar("contratados", periodo)}
        for contrato in buscar("contratos", periodo):
            if _texto(contrato.get("numero_processo_adm")) in processos:
                chave = (_texto(contrato.get("numero_contrato")), (contrato.get("data_contrato") or "")[:10])
                resultado.contar(self.gravar_contrato(camara, contrato, contratados.get(chave, {}))[1])

    @staticmethod
    def gravar_repasse(camara, item):
        from apps.transparencia.models import Receita

        referencia = item["data_referencia_doc"]
        conta = _texto(item.get("codigo_conta_contabil"))
        unidade = _texto(item.get("codigo_unidade_orcamentaria"))
        competencia = date(referencia // 100, referencia % 100, 1)
        return Receita.objects.update_or_create(
            camara=camara, origem="tce-ce",
            id_origem=f"{referencia}-{item.get('codigo_orgao')}-{unidade}-{conta}-{_texto(item.get('codigo_fonte'))}",
            defaults={
                "ano": competencia.year, "competencia": competencia, "conta": conta,
                "descricao": "Repasse do duodécimo (transferência financeira recebida)",
                "valor_mes": _decimal(item.get("valor_total_creditos")),
                "valor_acumulado": _decimal(item.get("valor_saldo_ate_mes")),
            },
        )

    @staticmethod
    def gravar_processo(camara, item):
        from apps.transparencia.models import Licitacao

        numero = _texto(item.get("numero_licitacao"))
        autuacao = _momento(item.get("data_realizacao_autuacao_licitacao") or item.get("data_realizacao_licitacao"))
        abertura = None
        if item.get("data_realizacao_licitacao") and _texto(item.get("hora_licitacao")):
            abertura = _momento(item["data_realizacao_licitacao"][:10] + "T" + _texto(item["hora_licitacao"]) + ":00")
        plataforma = _texto(item.get("descricao_url_plataforma_contratacao"))
        return Licitacao.objects.update_or_create(
            camara=camara, origem="tce-ce", id_origem=f"{numero}|{autuacao:%Y-%m-%d}"[:60],
            defaults={
                "numero": numero, "ano": autuacao.year, "processo": numero, "modalidade": modalidade(item),
                "situacao": "Homologada" if item.get("data_homologacao") else "Em andamento",
                "objeto": _texto(item.get("descricao_objeto_licitacao")),
                "valor_estimado": _decimal(item.get("valor_orcado_estimado")) if item.get("valor_orcado_estimado") else None,
                "abertura_propostas": abertura, "publicada_em": autuacao,
                "link_sistema": plataforma if plataforma.startswith("http") else "",
            },
        )

    @staticmethod
    def gravar_contrato(camara, item, contratado):
        from apps.transparencia.models import Contrato, Licitacao

        numero = _texto(item.get("numero_contrato"))
        assinatura = _momento(item.get("data_contrato"))
        processo = _texto(item.get("numero_processo_adm"))
        valor = item.get("valor_total_contrato")
        return Contrato.objects.update_or_create(
            camara=camara, origem="tce-ce", id_origem=f"{numero}|{assinatura:%Y-%m-%d}"[:60],
            defaults={
                "numero": numero, "ano": assinatura.year, "processo": processo,
                "tipo": TIPOS_CONTRATO.get(_texto(item.get("modalide_contrato")), "Contrato"),
                "objeto": _texto(item.get("descricao_objeto_contrato")),
                "fornecedor": _texto(contratado.get("nome_negociante"))[:255],
                "fornecedor_documento": _digitos(contratado.get("numero_documento_negociante")),
                "valor_global": _decimal(valor) if valor else None,
                "assinatura": assinatura.date(), "publicado_em": assinatura,
                "vigencia_inicio": _data(item.get("data_inicio_vigencia_contrato")),
                "vigencia_fim": _data(item.get("data_fim_vigencia_contrato")),
                "licitacao": Licitacao.objects.filter(camara=camara, origem="tce-ce", processo=processo)
                .order_by("-publicada_em").first(),
            },
        )

    @staticmethod
    def gravar_empenho(camara, item):
        from apps.transparencia.models import Despesa

        historico = item.get("descricao_historico_empenho") or " ".join(
            filter(None, [item.get("historico1_empenho"), item.get("historico2_empenho")]))
        return Despesa.objects.update_or_create(
            camara=camara, origem="tce-ce", id_origem=chave_empenho(item),
            defaults={
                "ano": item["exercicio_orcamento"] // 100,
                "numero_empenho": item["numero_empenho"],
                "data_empenho": _data(item.get("data_emissao_empenho")),
                "unidade_orcamentaria": (item.get("codigo_unidade_orcamentaria") or "").strip(),
                "funcao": item.get("codigo_funcao") or "",
                "elemento": item.get("codigo_elemento_despesa") or "",
                "modalidade_empenho": item.get("modalidade_nota_empenho") or "",
                "historico": (historico or "").strip(),
                "fornecedor": (item.get("nome_negociante") or "").strip(),
                "fornecedor_documento": _digitos(item.get("numero_documento_negociante")),
                "numero_contrato": (item.get("numero_contrato") or "").strip(),
                "numero_licitacao": (item.get("numero_licitacao") or "").strip(),
                "valor_empenhado": _decimal(item.get("valor_empenhado")),
            },
        )

    @staticmethod
    def gravar_movimento(camara, item, tipo):
        from apps.transparencia.models import Despesa, MovimentoDespesa

        despesa = Despesa.objects.filter(camara=camara, origem="tce-ce", id_origem=chave_empenho(item)).first()
        if despesa is None:
            return None
        if tipo == "L":
            data = item.get("data_liquidacao") or ""
            numero = f"{item.get('numero_sub_empenho_liquidacao') or ''}-{data[:10]}"
            data, valor, estornado = item.get("data_liquidacao"), item.get("valor_liquidado"), item.get("status_estornado")
        else:
            numero = item.get("numero_nota_pagamento") or ""
            data, valor = item.get("data_nota_pagamento"), item.get("valor_nota_pagamento")
            estornado = item.get("estado_de_estornado")
        MovimentoDespesa.objects.update_or_create(
            despesa=despesa, tipo=tipo, numero=str(numero),
            defaults={"data": _data(data), "valor": _decimal(valor), "estornado": bool(estornado)},
        )
        return despesa
