"""O requisito mais importante do SaaS: uma câmara nunca vê dados de outra."""

from datetime import date

from django.contrib.auth.models import Permission, User
from django.test import TestCase

from apps.camaras.models import Membro
from apps.legislativo.models import Norma, Vereador
from apps.noticias.models import Noticia
from apps.transparencia.models import CategoriaTransparencia, Documento

from .fabrica import criar_camara


class IsolamentoPortalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.a = criar_camara("camara-a.test", "Câmara Municipal A")
        cls.b = criar_camara("camara-b.test", "Câmara Municipal B")
        Vereador.objects.create(camara=cls.a, nome_parlamentar="Ana da Câmara A")
        Vereador.objects.create(camara=cls.b, nome_parlamentar="Bruno da Câmara B")
        Noticia.objects.create(camara=cls.a, titulo="Notícia A", slug="noticia", corpo="a")
        Noticia.objects.create(camara=cls.b, titulo="Notícia B", slug="noticia", corpo="b")
        Norma.objects.create(camara=cls.a, tipo="lei", numero="1", ano=2026, data=date(2026, 1, 1), ementa="Lei de A")
        Norma.objects.create(camara=cls.b, tipo="lei", numero="1", ano=2026, data=date(2026, 1, 1), ementa="Lei de B")
        cls.categoria = CategoriaTransparencia.objects.get(slug="diarias")
        Documento.objects.create(camara=cls.a, categoria=cls.categoria, titulo="Diária A", data=date(2026, 1, 1), descricao="x")
        Documento.objects.create(camara=cls.b, categoria=cls.categoria, titulo="Diária B", data=date(2026, 1, 1), descricao="x")

    def test_dominio_desconhecido_retorna_404(self):
        self.assertEqual(self.client.get("/", HTTP_HOST="desconhecido.test").status_code, 404)

    def test_pagina_inicial_mostra_so_a_propria_camara(self):
        r = self.client.get("/", HTTP_HOST="camara-a.test")
        self.assertContains(r, "Ana da Câmara A")
        self.assertNotContains(r, "Bruno da Câmara B")
        self.assertNotContains(r, "Notícia B")

    def test_mesmo_slug_em_camaras_diferentes(self):
        self.assertContains(self.client.get("/noticias/noticia/", HTTP_HOST="camara-b.test"), "Notícia B")

    def test_vereador_de_outra_camara_retorna_404(self):
        bruno = Vereador.objects.get(camara=self.b)
        self.assertEqual(self.client.get(f"/vereadores/{bruno.pk}/", HTTP_HOST="camara-a.test").status_code, 404)

    def test_exportacao_json_isolada(self):
        r = self.client.get("/legislacao/?formato=json", HTTP_HOST="camara-a.test")
        self.assertEqual([n["ementa"] for n in r.json()], ["Lei de A"])
        r = self.client.get("/transparencia/diarias/?formato=json", HTTP_HOST="camara-b.test")
        self.assertEqual([d["titulo"] for d in r.json()], ["Diária B"])


class IsolamentoAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.a = criar_camara("camara-a.test", "Câmara Municipal A")
        cls.b = criar_camara("camara-b.test", "Câmara Municipal B")
        Vereador.objects.create(camara=cls.a, nome_parlamentar="Ana da Câmara A")
        cls.bruno = Vereador.objects.create(camara=cls.b, nome_parlamentar="Bruno da Câmara B")
        cls.usuario = User.objects.create_user("servidor_a", password="x", is_staff=True)
        cls.usuario.user_permissions.set(Permission.objects.filter(content_type__app_label="legislativo"))
        Membro.objects.create(usuario=cls.usuario, camara=cls.a)

    def setUp(self):
        self.client.force_login(self.usuario)

    def test_lista_do_admin_so_tem_a_propria_camara(self):
        r = self.client.get("/admin/legislativo/vereador/", HTTP_HOST="painel.test")
        self.assertContains(r, "Ana da Câmara A")
        self.assertNotContains(r, "Bruno da Câmara B")

    def test_nao_edita_registro_de_outra_camara(self):
        r = self.client.get(f"/admin/legislativo/vereador/{self.bruno.pk}/change/", HTTP_HOST="painel.test")
        self.assertNotEqual(r.status_code, 200)

    def test_criacao_preenche_camara_automaticamente(self):
        r = self.client.post(
            "/admin/legislativo/vereador/add/",
            {"nome_parlamentar": "Carla", "em_exercicio": "on"},
            HTTP_HOST="painel.test",
        )
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Vereador.objects.get(nome_parlamentar="Carla").camara, self.a)
