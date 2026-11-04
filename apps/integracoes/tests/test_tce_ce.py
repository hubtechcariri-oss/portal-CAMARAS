import io
import json
from datetime import date
from decimal import Decimal
from unittest import mock
from urllib.error import HTTPError

from django.test import TestCase

from apps.camaras.tests.fabrica import criar_camara
from apps.integracoes.conectores import ErroDeImportacao, executar, tce_ce
from apps.integracoes.models import FonteDados
from apps.transparencia.models import Despesa, MovimentoDespesa

CNPJ = "06580377000143"

# Formatos copiados de respostas reais do SIM/TCE-CE (Aratuba, nov/2026).
ORGAOS = [
    {"codigo_municipio": "017", "exercicio_orcamento": 202600, "codigo_orgao": "01", "codigo_tipo_unidade": "01",
     "cgc_orgao": "07387509000106", "nome_orgao": "GABINETE DO PREFEITO"},
    {"codigo_municipio": "017", "exercicio_orcamento": 202600, "codigo_orgao": "11", "codigo_tipo_unidade": "02",
     "cgc_orgao": CNPJ, "nome_orgao": "CAMARA MUNICIPAL DE ARATUBA"},
]
EMPENHO = {
    "codigo_municipio": "017", "exercicio_orcamento": 202600, "codigo_orgao": "11", "codigo_unidade_orcamentaria": "01  ",
    "data_emissao_empenho": "2026-09-01T00:00:00Z", "numero_empenho": "01090004", "codigo_funcao": "01",
    "codigo_elemento_despesa": "33903500", "modalidade_nota_empenho": "G",
    "descricao_historico_empenho": "Serviços de assessoria contábil  ", "valor_empenhado": 59500,
    "numero_documento_negociante": "32.170.863/0001-01", "nome_negociante": "CONTABIL LTDA ",
    "numero_contrato": "001/2026", "numero_licitacao": "", "data_referencia_doc": 202609,
}
DIARIA = {**EMPENHO, "numero_empenho": "01090005", "codigo_elemento_despesa": "33901400", "valor_empenhado": 450,
          "descricao_historico_empenho": "Diárias para viagem a Fortaleza", "nome_negociante": "FULANO DE TAL",
          "numero_documento_negociante": "12345678901", "numero_contrato": ""}
LIQUIDACAO = {"exercicio_orcamento": 202600, "codigo_orgao": "11", "codigo_unidade_orcamentaria": "01  ",
              "data_emissao_empenho": "2026-09-01T00:00:00Z", "numero_empenho": "01090004",
              "data_liquidacao": "2026-09-10T00:00:00Z", "numero_sub_empenho_liquidacao": "1",
              "valor_liquidado": 59500, "status_estornado": None}
PAGAMENTOS = [
    {**LIQUIDACAO, "numero_nota_pagamento": "17090001", "data_nota_pagamento": "2026-09-15T00:00:00Z",
     "valor_nota_pagamento": 30000, "estado_de_estornado": None},
    {**LIQUIDACAO, "numero_nota_pagamento": "17090002", "data_nota_pagamento": "2026-09-16T00:00:00Z",
     "valor_nota_pagamento": 5000, "estado_de_estornado": "S"},
    {**LIQUIDACAO, "numero_empenho": "99999999", "numero_nota_pagamento": "17090003",
     "data_nota_pagamento": "2026-09-16T00:00:00Z", "valor_nota_pagamento": 10, "estado_de_estornado": None},
]


def api_falsa(chamadas, mes_com_dados=202609):
    def buscar(caminho, parametros):
        chamadas.append((caminho, dict(parametros)))
        if caminho == "municipios":
            return [{"codigo_municipio": "017", "nome_municipio": "ARATUBA"}]
        if caminho == "orgaos":
            return ORGAOS
        if parametros.get("data_referencia_doc") != mes_com_dados:
            return []
        return {"notas_empenhos": [EMPENHO, DIARIA], "liquidacoes": [LIQUIDACAO], "notas_pagamentos": PAGAMENTOS}[caminho]

    return buscar


class AuxiliaresTests(TestCase):
    def test_meses_atravessa_o_ano(self):
        self.assertEqual(list(tce_ce.meses(date(2025, 11, 20), date(2026, 2, 1))),
                         [(2025, 11), (2025, 12), (2026, 1), (2026, 2)])

    def test_voltar_meses(self):
        self.assertEqual(tce_ce.voltar_meses(date(2026, 2, 17), 2), date(2025, 12, 1))

    def test_paginacao_por_start_index(self):
        paginas = {0: list(range(1000)), 1000: [1000, 1001]}
        with mock.patch.object(tce_ce, "_get", side_effect=lambda c, p: paginas[p["$start_index"]]):
            self.assertEqual(len(tce_ce.buscar("notas_empenhos", {})), 1002)

    def resposta(self, corpo):
        ok = mock.MagicMock()
        ok.__enter__.return_value.read.return_value = json.dumps(corpo).encode()
        return ok

    def test_erro_do_tce_vira_erro_de_importacao(self):
        corpo = {"__errors__": [{"message": "Parâmetro obrigatório: data_referencia_doc"}]}
        with mock.patch.object(tce_ce, "urlopen", return_value=self.resposta(corpo)), \
                mock.patch.object(tce_ce.time, "sleep"), \
                self.assertRaisesMessage(ErroDeImportacao, "Parâmetro obrigatório: data_referencia_doc"):
            tce_ce._get("notas_empenhos", {})

    def test_5xx_tenta_de_novo(self):
        erro = HTTPError("u", 503, "Unavailable", {}, io.BytesIO(b""))
        with mock.patch.object(tce_ce, "urlopen", side_effect=[erro, self.resposta({"elements": [1]})]), \
                mock.patch.object(tce_ce.time, "sleep"):
            self.assertEqual(tce_ce._get("orgaos", {}), [1])

    def test_sem_resposta_desiste_logo_com_mensagem_clara(self):
        from urllib.error import URLError
        with mock.patch.object(tce_ce, "urlopen", side_effect=URLError("timed out")) as abrir, \
                mock.patch.object(tce_ce.time, "sleep"), self.assertRaisesMessage(ErroDeImportacao, "fora do Brasil"):
            tce_ce._get("orgaos", {})
        self.assertEqual(abrir.call_count, 2)

    def test_orgao_pelo_cnpj_e_pelo_tipo_legislativo(self):
        with mock.patch.object(tce_ce, "buscar", return_value=ORGAOS):
            self.assertEqual(tce_ce.codigo_orgao("017", 2026, CNPJ, {}), "11")
            self.assertEqual(tce_ce.codigo_orgao("017", 2026, "", {}), "11")
        with mock.patch.object(tce_ce, "buscar", return_value=[ORGAOS[0]]), \
                self.assertRaisesMessage(ErroDeImportacao, "codigo_orgao"):
            tce_ce.codigo_orgao("017", 2026, "", {})


class ConectorTCECETests(TestCase):
    def setUp(self):
        self.a = criar_camara("camara-a.test", "Câmara Municipal A")
        self.a.cnpj = "06.580.377/0001-43"
        self.a.municipio = "Aratuba"
        self.a.save()
        self.fonte = FonteDados.objects.create(camara=self.a, tipo="tce-ce", configuracao={"codigo_municipio": "17"})
        self.chamadas = []

    def importar(self, desde=date(2026, 9, 1), ate=date(2026, 10, 31)):
        with mock.patch.object(tce_ce, "buscar", side_effect=api_falsa(self.chamadas)):
            return executar(self.fonte, desde, ate)

    def test_importa_empenhos_liquidacoes_e_pagamentos(self):
        imp = self.importar()
        self.assertEqual(imp.situacao, "sucesso", imp.mensagem)
        self.assertEqual(imp.novos, 2)
        d = Despesa.objects.get(numero_empenho="01090004")
        self.assertEqual((d.camara, d.ano, d.data_empenho), (self.a, 2026, date(2026, 9, 1)))
        self.assertEqual(d.unidade_orcamentaria, "01")
        self.assertEqual(d.historico, "Serviços de assessoria contábil")
        self.assertEqual(d.fornecedor_documento, "32170863000101")
        self.assertEqual(d.nome_elemento, "Serviços de consultoria")
        self.assertEqual(d.valor_empenhado, Decimal("59500.00"))
        self.assertEqual(d.valor_liquidado, Decimal("59500.00"))
        self.assertEqual(d.valor_pago, Decimal("30000.00"))  # o pagamento estornado não conta
        self.assertEqual(d.movimentos.count(), 3)
        self.assertIn("empenho 99999999 não encontrado", imp.mensagem)

    def test_consulta_mes_a_mes_com_o_orgao_da_camara(self):
        self.importar()
        empenhos = [p for c, p in self.chamadas if c == "notas_empenhos"]
        self.assertEqual([p["data_referencia_doc"] for p in empenhos], [202608, 202609, 202610])  # relê o atraso
        self.assertTrue(all(p["codigo_municipio"] == "017" and p["codigo_orgao"] == "11"
                            and p["exercicio_orcamento"] == 202600 for p in empenhos))
        self.assertEqual(sum(c == "orgaos" for c, _ in self.chamadas), 1)

    def test_reimportar_nao_duplica(self):
        self.importar()
        imp = self.importar()
        self.assertEqual((imp.novos, imp.atualizados), (0, 2))
        self.assertEqual(Despesa.objects.count(), 2)
        self.assertEqual(MovimentoDespesa.objects.count(), 3)

    def test_acha_o_municipio_pelo_nome_sem_acento(self):
        self.fonte.configuracao = {}
        self.fonte.save()
        self.importar()
        (municipio,) = [p for c, p in self.chamadas if c == "municipios"]
        self.assertEqual(municipio, {"nome_municipio": "ARATUBA"})


class PaginasDespesasTests(TestCase):
    def setUp(self):
        self.a = criar_camara("camara-a.test", "Câmara Municipal A")
        self.b = criar_camara("camara-b.test", "Câmara Municipal B")
        for item in (EMPENHO, DIARIA):
            tce_ce.ConectorTCECE.gravar_empenho(self.a, item)
        tce_ce.ConectorTCECE.gravar_empenho(self.b, {**EMPENHO, "descricao_historico_empenho": "Da outra câmara"})
        tce_ce.ConectorTCECE.gravar_movimento(self.a, PAGAMENTOS[0], "P")
        for d in Despesa.objects.all():
            d.recalcular()
            d.save()

    def get(self, url):
        return self.client.get(url, HTTP_HOST="camara-a.test")

    def test_despesas_com_totais_e_so_da_camara(self):
        r = self.get("/transparencia/despesas/")
        self.assertContains(r, "Serviços de assessoria contábil")
        self.assertContains(r, "Diárias para viagem a Fortaleza")
        self.assertNotContains(r, "Da outra câmara")
        self.assertContains(r, "59.950,00")  # total empenhado
        self.assertContains(r, "30.000,00")
        self.assertContains(r, "TCE-CE")

    def test_diarias_so_elemento_14_e_cpf_mascarado(self):
        r = self.get("/transparencia/diarias/")
        self.assertContains(r, "Diárias para viagem a Fortaleza")
        self.assertNotContains(r, "Serviços de assessoria contábil")
        self.assertContains(r, "***.456.789-**")
        self.assertNotContains(r, "12345678901")

    def test_busca_e_csv(self):
        r = self.get("/transparencia/despesas/?q=contabil")
        self.assertEqual(r.context["total"], 1)
        r = self.get("/transparencia/despesas/?formato=csv")
        corpo = r.content.decode("utf-8-sig")
        self.assertIn("01090004", corpo)
        self.assertNotIn("12345678901", corpo)

    def test_indice_conta_as_despesas(self):
        r = self.get("/transparencia/")
        cats = {c.slug: c.total for g in r.context["grupos"] for c in g.categorias.all()}
        self.assertEqual((cats["despesas"], cats["diarias"]), (2, 1))
