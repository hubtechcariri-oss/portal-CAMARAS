from datetime import timedelta
from unittest import mock

from django.test import TestCase
from django.utils import timezone

from apps.camaras.tests.fabrica import criar_camara
from apps.esic.models import Pedido

DADOS = {"nome": "Maria", "email": "maria@exemplo.com", "pedido": "Quero a folha de outubro.", "ciente_privacidade": "on"}


class EsicTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.a = criar_camara("camara-a.test")
        cls.b = criar_camara("camara-b.test", "Câmara Municipal B")

    def test_protocolo_sequencial_por_camara(self):
        p1 = Pedido.objects.create(camara=self.a, nome="x", email="x@x.com", pedido="x")
        p2 = Pedido.objects.create(camara=self.a, nome="x", email="x@x.com", pedido="x")
        p3 = Pedido.objects.create(camara=self.b, nome="x", email="x@x.com", pedido="x")
        ano = timezone.localdate().year
        self.assertEqual([p1.protocolo, p2.protocolo, p3.protocolo], [f"{ano}00001", f"{ano}00002", f"{ano}00001"])

    def test_prazo_e_prorrogacao_unica(self):
        p = Pedido.objects.create(camara=self.a, nome="x", email="x@x.com", pedido="x")
        self.assertEqual(p.prazo, timezone.localdate() + timedelta(days=20))
        p.prorrogar()
        self.assertEqual(p.prazo, timezone.localdate() + timedelta(days=30))
        with self.assertRaises(ValueError):
            p.prorrogar()

    def test_vencido(self):
        p = Pedido.objects.create(camara=self.a, nome="x", email="x@x.com", pedido="x")
        futuro = timezone.localdate() + timedelta(days=21)
        with mock.patch("django.utils.timezone.localdate", return_value=futuro):
            self.assertTrue(p.vencido)

    def test_fluxo_publico_completo(self):
        r = self.client.post("/esic/", DADOS, HTTP_HOST="camara-a.test", follow=True)
        pedido = Pedido.objects.get()
        self.assertEqual(pedido.camara, self.a)
        self.assertContains(r, pedido.protocolo)
        self.assertContains(r, pedido.codigo_consulta)

        url = f"/esic/consulta/?protocolo={pedido.protocolo}&codigo={pedido.codigo_consulta}"
        self.assertContains(self.client.get(url, HTTP_HOST="camara-a.test"), "Quero a folha de outubro.")
        # O mesmo protocolo não é visível pelo domínio de outra câmara.
        self.assertNotContains(self.client.get(url, HTTP_HOST="camara-b.test"), "Quero a folha de outubro.")

    def test_consulta_exige_codigo_correto(self):
        p = Pedido.objects.create(camara=self.a, nome="x", email="x@x.com", pedido="segredo")
        r = self.client.get(f"/esic/consulta/?protocolo={p.protocolo}&codigo=ERRADO", HTTP_HOST="camara-a.test")
        self.assertNotContains(r, "segredo")
        self.assertContains(r, "Nenhum pedido encontrado")

    def test_exige_ciencia_de_privacidade_e_bloqueia_robo(self):
        self.client.post("/esic/", {**DADOS, "ciente_privacidade": ""}, HTTP_HOST="camara-a.test")
        self.client.post("/esic/", {**DADOS, "site": "spam"}, HTTP_HOST="camara-a.test")
        self.assertFalse(Pedido.objects.exists())
