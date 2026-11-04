from datetime import date, datetime
from datetime import timezone as dt_timezone
from decimal import Decimal
from unittest import mock
from urllib.error import HTTPError

from django.contrib.auth.models import Permission, User
from django.test import TestCase

from apps.camaras.models import Membro
from apps.camaras.tests.fabrica import criar_camara
from apps.integracoes.conectores import ErroDeImportacao, executar, pncp
from apps.integracoes.models import FonteDados
from apps.transparencia.models import Contrato, Licitacao

CNPJ = "06580377000143"
ORGAO = {"cnpj": CNPJ, "razaoSocial": "MUNICIPIO DE ARATUBA - CAMARA MUNICIPAL", "poderId": "L", "esferaId": "M"}

# Formatos copiados de respostas reais da API de Consultas (nov/2026).
COMPRA = {
    "numeroControlePNCP": f"{CNPJ}-1-000004/2026", "orgaoEntidade": ORGAO, "anoCompra": 2026,
    "sequencialCompra": 4, "numeroCompra": "004/2026", "processo": "2026.07.01", "modalidadeNome": "Pregão - Eletrônico",
    "situacaoCompraNome": "Divulgada no PNCP", "objetoCompra": "Aquisição de material de expediente",
    "valorTotalEstimado": 45210.5, "valorTotalHomologado": None, "dataAberturaProposta": "2026-08-15T09:00:00",
    "dataPublicacaoPncp": "2026-08-03T07:40:00", "linkSistemaOrigem": "https://compras.exemplo/123",
}
CONTRATO = {
    "numeroControlePNCP": f"{CNPJ}-2-000001/2026", "numeroControlePncpCompra": f"{CNPJ}-1-000004/2026",
    "orgaoEntidade": ORGAO, "anoContrato": 2026, "sequencialContrato": 1, "numeroContratoEmpenho": "001/2026",
    "processo": "2026.07.01", "tipoContrato": {"id": 1, "nome": "Contrato (termo inicial)"},
    "objetoContrato": "Fornecimento de material de expediente", "nomeRazaoSocialFornecedor": "PAPELARIA LTDA",
    "niFornecedor": "32170863000101", "valorInicial": 127603.81, "valorGlobal": 127603.81,
    "dataAssinatura": "2026-05-02", "dataVigenciaInicio": "2026-05-02", "dataVigenciaFim": "2027-04-30",
    "dataPublicacaoPncp": "2026-06-02T16:26:20",
}


def api_falsa(chamadas):
    """Responde só à modalidade 6 e a contratos; o resto é HTTP 204 (sem dados)."""

    def buscar(caminho, parametros):
        chamadas.append((caminho, dict(parametros)))
        if caminho == "contratacoes/publicacao" and parametros["codigoModalidadeContratacao"] == 6:
            return {"data": [COMPRA], "totalPaginas": 1}
        if caminho == "contratos":
            return {"data": [CONTRATO], "totalPaginas": 1}
        return None

    return buscar


class JanelasTests(TestCase):
    def test_divide_em_periodos_de_30_dias_sem_buracos(self):
        j = list(pncp.janelas(date(2026, 1, 1), date(2026, 3, 5)))
        self.assertEqual(j[0], (date(2026, 1, 1), date(2026, 1, 30)))
        self.assertEqual(j[1][0], date(2026, 1, 31))
        self.assertEqual(j[-1][1], date(2026, 3, 5))

    def test_um_dia(self):
        self.assertEqual(list(pncp.janelas(date(2026, 1, 1), date(2026, 1, 1))), [(date(2026, 1, 1), date(2026, 1, 1))])


class PaginasTests(TestCase):
    def test_percorre_todas_as_paginas(self):
        respostas = {1: {"data": [1, 2], "totalPaginas": 2}, 2: {"data": [3], "totalPaginas": 2}}
        with mock.patch.object(pncp, "buscar_json", side_effect=lambda c, p: respostas[p["pagina"]]):
            self.assertEqual(list(pncp.paginas("contratos", {})), [1, 2, 3])

    def test_erro_http_vira_erro_de_importacao(self):
        erro = HTTPError("u", 422, "Período maior que 365 dias", {}, None)
        with mock.patch.object(pncp, "urlopen", side_effect=erro), self.assertRaisesMessage(ErroDeImportacao, "422"):
            pncp.buscar_json("contratos", {})


class ConectorPNCPTests(TestCase):
    def setUp(self):
        self.a = criar_camara("camara-a.test", "Câmara Municipal A")
        self.a.cnpj = "06.580.377/0001-43"
        self.a.save()
        self.fonte = FonteDados.objects.create(camara=self.a, tipo="pncp")
        self.chamadas = []

    def importar(self, desde=date(2026, 8, 1), ate=date(2026, 8, 20)):
        with mock.patch.object(pncp, "buscar_json", side_effect=api_falsa(self.chamadas)):
            return executar(self.fonte, desde, ate)

    def test_importa_licitacao_e_contrato_ligados(self):
        imp = self.importar()
        self.assertEqual(imp.situacao, "sucesso", imp.mensagem)
        self.assertEqual((imp.novos, imp.atualizados), (2, 0))
        lic = Licitacao.objects.get()
        self.assertEqual(lic.camara, self.a)
        self.assertEqual(lic.modalidade, "Pregão - Eletrônico")
        self.assertEqual(lic.valor_estimado, Decimal("45210.50"))
        self.assertEqual(lic.link_origem, f"https://pncp.gov.br/app/editais/{CNPJ}/2026/4")
        self.assertEqual(lic.publicada_em, datetime(2026, 8, 3, 10, 40, tzinfo=dt_timezone.utc))  # 07:40 em Brasília
        c = Contrato.objects.get()
        self.assertEqual(c.licitacao, lic)
        self.assertEqual(c.tipo, "Contrato (termo inicial)")
        self.assertEqual(c.vigencia_fim, date(2027, 4, 30))
        self.assertEqual(c.fornecedor_documento_publico, "32.170.863/0001-01")
        self.assertEqual(c.link_origem, f"https://pncp.gov.br/app/contratos/{CNPJ}/2026/1")

    def test_consulta_cada_modalidade_com_cnpj_e_periodo(self):
        self.importar()
        compras = [p for c, p in self.chamadas if c == "contratacoes/publicacao"]
        self.assertEqual(sorted(p["codigoModalidadeContratacao"] for p in compras), list(range(1, 14)))
        self.assertTrue(all(p["cnpj"] == CNPJ and p["dataInicial"] == "20260801" and p["dataFinal"] == "20260820"
                            for p in compras))
        (contratos,) = [p for c, p in self.chamadas if c == "contratos"]
        self.assertEqual(contratos["cnpjOrgao"], CNPJ)

    def test_reimportar_atualiza_sem_duplicar(self):
        self.importar()
        COMPRA_ALTERADA = {**COMPRA, "situacaoCompraNome": "Homologada"}
        with mock.patch.dict(COMPRA, COMPRA_ALTERADA):
            imp = self.importar()
        self.assertEqual((imp.novos, imp.atualizados), (0, 2))
        self.assertEqual(Licitacao.objects.get().situacao, "Homologada")

    def test_sem_cnpj_registra_erro_claro(self):
        self.a.cnpj = ""
        self.a.save()
        imp = self.importar()
        self.assertEqual(imp.situacao, "erro")
        self.assertIn("CNPJ", imp.mensagem)
        self.assertEqual(self.chamadas, [])

    def test_cnpj_da_configuracao_tem_prioridade(self):
        self.fonte.configuracao = {"cnpj": "11.222.333/0001-81"}
        self.fonte.save()
        self.importar()
        self.assertTrue(all(p.get("cnpj", p.get("cnpjOrgao")) == "11222333000181" for _, p in self.chamadas))

    def test_cpf_de_fornecedor_aparece_mascarado(self):
        self.assertEqual(Contrato(fornecedor_documento="123.456.789-01").fornecedor_documento_publico, "***.456.789-**")


class AdminTests(TestCase):
    def setUp(self):
        self.a = criar_camara("camara-a.test", "Câmara Municipal A")
        self.b = criar_camara("camara-b.test", "Câmara Municipal B")
        for camara in (self.a, self.b):
            pncp.ConectorPNCP.gravar_licitacao(camara, {**COMPRA, "objetoCompra": f"Objeto {camara.nome}"}, 6)
        self.u = User.objects.create_user("transp", password="x", is_staff=True)
        self.u.user_permissions.add(*Permission.objects.filter(
            content_type__app_label="transparencia", codename__in=["view_licitacao", "view_contrato"]))
        Membro.objects.create(usuario=self.u, camara=self.a)
        self.client.force_login(self.u)

    def test_lista_so_da_propria_camara_e_sem_botao_de_adicionar(self):
        r = self.client.get("/admin/transparencia/licitacao/", HTTP_HOST="camara-a.test")
        self.assertContains(r, "Objeto Câmara Municipal A")
        self.assertNotContains(r, "Objeto Câmara Municipal B")
        self.assertNotContains(r, "/admin/transparencia/licitacao/add/")
        self.assertContains(r, "ver no PNCP")

    def test_detalhe_abre_somente_leitura(self):
        lic = Licitacao.objects.get(camara=self.a)
        r = self.client.get(f"/admin/transparencia/licitacao/{lic.pk}/change/", HTTP_HOST="camara-a.test")
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, 'name="objeto"')
