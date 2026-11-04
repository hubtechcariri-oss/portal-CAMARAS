from datetime import date, timedelta

from django.contrib.auth.models import Permission, User
from django.test import TestCase
from django.utils import timezone

from apps.camaras import indicadores
from apps.camaras.models import Membro
from apps.camaras.tests.fabrica import criar_camara
from apps.transparencia.models import CategoriaTransparencia, Contrato, Licitacao


def licitacao(camara, n, modalidade="Pregão - Eletrônico", objeto="Material de expediente", ano=2026, dias=10):
    return Licitacao.objects.create(
        camara=camara, id_origem=f"{camara.pk}-1-{n}/{ano}", numero=f"{n}/{ano}", ano=ano, modalidade=modalidade,
        objeto=objeto, valor_estimado="1234567.80", publicada_em=timezone.now() - timedelta(days=dias),
        link_origem=f"https://pncp.gov.br/app/editais/x/{ano}/{n}",
    )


def contrato(camara, n, documento="32170863000101", fornecedor="PAPELARIA LTDA"):
    return Contrato.objects.create(
        camara=camara, id_origem=f"{camara.pk}-2-{n}/2026", numero=f"{n}/2026", ano=2026, objeto="Fornecimento",
        fornecedor=fornecedor, fornecedor_documento=documento, valor_global="5000.00",
        vigencia_inicio=date(2026, 5, 2), vigencia_fim=date(2027, 4, 30), publicado_em=timezone.now(),
    )


class PaginasPublicasTests(TestCase):
    def setUp(self):
        self.a = criar_camara("camara-a.test", "Câmara Municipal A")
        self.b = criar_camara("camara-b.test", "Câmara Municipal B")
        licitacao(self.a, 1, objeto="Aquisição de cadeiras")
        licitacao(self.a, 2, objeto="Serviço de limpeza", ano=2025)
        licitacao(self.a, 3, modalidade="Dispensa", objeto="Conserto do ar-condicionado")
        licitacao(self.b, 1, objeto="Objeto da outra câmara")
        contrato(self.a, 1)
        contrato(self.a, 2, documento="12345678901", fornecedor="FULANO DE TAL")

    def get(self, url):
        return self.client.get(url, HTTP_HOST="camara-a.test")

    def test_licitacoes_sem_dispensas_e_so_da_camara(self):
        r = self.get("/transparencia/licitacoes/")
        self.assertContains(r, "Aquisição de cadeiras")
        self.assertContains(r, "Serviço de limpeza")
        self.assertNotContains(r, "Conserto do ar-condicionado")
        self.assertNotContains(r, "Objeto da outra câmara")
        self.assertContains(r, "Ver no PNCP")
        self.assertContains(r, "1.234.567,80")

    def test_dispensas_em_categoria_propria(self):
        r = self.get("/transparencia/dispensas-e-inexigibilidades/")
        self.assertContains(r, "Conserto do ar-condicionado")
        self.assertNotContains(r, "Aquisição de cadeiras")

    def test_busca_e_filtro_por_ano(self):
        r = self.get("/transparencia/licitacoes/?q=cadeira")
        self.assertContains(r, "Aquisição de cadeiras")
        self.assertNotContains(r, "Serviço de limpeza")
        r = self.get("/transparencia/licitacoes/?ano=2025")
        self.assertContains(r, "Serviço de limpeza")
        self.assertNotContains(r, "Aquisição de cadeiras")

    def test_contratos_mascaram_cpf_na_pagina_e_no_csv(self):
        r = self.get("/transparencia/contratos/")
        self.assertContains(r, "32.170.863/0001-01")
        self.assertContains(r, "***.456.789-**")
        self.assertNotContains(r, "12345678901")
        csv = self.get("/transparencia/contratos/?formato=csv").content.decode("utf-8-sig")
        self.assertIn("***.456.789-**", csv)
        self.assertNotIn("12345678901", csv)

    def test_csv_respeita_filtros(self):
        csv = self.get("/transparencia/licitacoes/?q=cadeira&formato=csv").content.decode("utf-8-sig")
        linhas = csv.strip().splitlines()
        self.assertEqual(len(linhas), 2)
        self.assertIn("Aquisição de cadeiras", linhas[1])

    def test_indice_conta_registros_importados(self):
        r = self.get("/transparencia/")
        cats = {c.slug: c.total for g in r.context["grupos"] for c in g.categorias.all()}
        self.assertEqual((cats["licitacoes"], cats["dispensas-e-inexigibilidades"], cats["contratos"]), (2, 1, 2))
        self.assertEqual(r.context["total_importados"], 5)
        self.assertContains(r, "<strong>5</strong> registros de licitações e contratos (PNCP)", html=False)
        self.assertContains(r, "Mais procurados")

    def test_sem_importados_mostra_documentos_como_antes(self):
        r = self.client.get("/transparencia/licitacoes/", HTTP_HOST="camara-b.test")
        self.assertContains(r, "Objeto da outra câmara")
        Licitacao.objects.filter(camara=self.b).delete()
        r = self.client.get("/transparencia/licitacoes/", HTTP_HOST="camara-b.test")
        self.assertContains(r, "Nenhuma informação publicada nesta categoria.")


class IndicadorTests(TestCase):
    def test_importados_contam_como_publicacao_em_dia(self):
        a = criar_camara("camara-a.test", "Câmara Municipal A")
        CategoriaTransparencia.objects.update(obrigatoria=False)
        CategoriaTransparencia.objects.filter(slug__in=["licitacoes", "contratos"]).update(obrigatoria=True)
        u = User.objects.create_user("t", password="x", is_staff=True)
        u.user_permissions.add(*Permission.objects.filter(codename="view_documento"))
        Membro.objects.create(usuario=u, camara=a)
        self.assertEqual(indicadores.transparencia(u, a)["publicados"], 0)
        licitacao(a, 1)
        t = indicadores.transparencia(u, a)
        self.assertEqual((t["publicados"], t["total"]), (1, 2))
        self.assertEqual([p["nome"] for p in t["pendencias"]], ["Contratos"])


class NomeTests(TestCase):
    def test_numero_com_ano_nao_repete_o_ano(self):
        self.assertEqual(str(Licitacao(modalidade="Pregão", numero="004/2026", ano=2026)), "Pregão nº 004/2026")
        self.assertEqual(str(Licitacao(modalidade="Pregão", numero="4", ano=2026)), "Pregão nº 4/2026")
