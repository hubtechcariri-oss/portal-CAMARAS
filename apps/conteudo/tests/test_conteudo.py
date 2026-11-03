import shutil
import tempfile
from datetime import timedelta

from django.core.files.base import ContentFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.camaras.models import Camara
from apps.camaras.tests.fabrica import criar_camara
from apps.conteudo.models import Banner, Pagina
from apps.legislativo.models import Vereador

MIDIA = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=MIDIA)
class ConteudoTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MIDIA, ignore_errors=True)

    def setUp(self):
        self.a = criar_camara("camara-a.test", "Câmara Municipal A")
        self.b = criar_camara("camara-b.test", "Câmara Municipal B")

    def banner(self, camara, titulo, **kw):
        b = Banner(camara=camara, titulo=titulo, **kw)
        b.imagem.save("b.jpg", ContentFile(b"x"), save=False)
        b.save()
        return b

    def test_banners_vigentes_respeitam_periodo_ativo_e_camara(self):
        agora = timezone.now()
        self.banner(self.a, "Vigente")
        self.banner(self.a, "Expirado", fim=agora - timedelta(days=1))
        self.banner(self.a, "Futuro", inicio=agora + timedelta(days=1))
        self.banner(self.a, "Desligado", ativo=False)
        self.banner(self.b, "Da outra câmara")
        self.assertEqual([b.titulo for b in Banner.vigentes(self.a)], ["Vigente"])

    def test_inicio_mostra_carrossel_so_da_propria_camara(self):
        self.banner(self.a, "Destaque A")
        self.banner(self.b, "Destaque B")
        r = self.client.get("/", HTTP_HOST="camara-a.test")
        self.assertContains(r, "Destaque A")
        self.assertNotContains(r, "Destaque B")
        self.assertContains(r, "data-carrossel")

    def test_pagina_e_menu_isolados_por_camara(self):
        Pagina.objects.create(camara=self.a, titulo="Sobre a Câmara A", slug="sobre", corpo="Texto A")
        Pagina.objects.create(camara=self.b, titulo="Sobre a Câmara B", slug="sobre", corpo="Texto B")
        r = self.client.get("/institucional/sobre/", HTTP_HOST="camara-a.test")
        self.assertContains(r, "Texto A")
        self.assertNotContains(r, "Câmara B")
        r = self.client.get("/", HTTP_HOST="camara-b.test")
        self.assertContains(r, "Sobre a Câmara B")
        self.assertNotContains(r, "Sobre a Câmara A")

    def test_pagina_nao_publicada_da_404(self):
        Pagina.objects.create(camara=self.a, titulo="Rascunho", slug="rascunho", corpo="x", publicada=False)
        self.assertEqual(self.client.get("/institucional/rascunho/", HTTP_HOST="camara-a.test").status_code, 404)

    def test_mesa_diretora_em_ordem_de_cargo(self):
        for nome, cargo in [("Zeca", "1º Secretário"), ("Maria", "Presidente"), ("Joana", "Vice-Presidente"),
                            ("Sem cargo", "")]:
            Vereador.objects.create(camara=self.a, nome_parlamentar=nome, cargo_mesa=cargo)
        r = self.client.get("/institucional/mesa-diretora/", HTTP_HOST="camara-a.test")
        self.assertEqual([v.nome_parlamentar for v in r.context["membros"]], ["Maria", "Joana", "Zeca"])


@override_settings(MEDIA_ROOT=MIDIA)
class DemoVisualTests(TestCase):
    def test_criar_demo_gera_visual_e_e_idempotente(self):
        call_command("criar_demo", host=["demo.test"], stdout=open("/dev/null", "w"))
        camara = Camara.objects.get(dominios__host="demo.test")
        self.assertTrue(camara.brasao)
        self.assertEqual(Banner.vigentes(camara).count(), 3)
        self.assertFalse(Vereador.objects.da_camara(camara).filter(foto="").exists())
        camara.brasao.delete(save=True)
        call_command("criar_demo", host=["demo.test"], stdout=open("/dev/null", "w"))
        camara.refresh_from_db()
        self.assertTrue(camara.brasao)
        self.assertEqual(Banner.objects.da_camara(camara).count(), 3)
        self.assertEqual(Pagina.objects.da_camara(camara).count(), 3)
        r = self.client.get("/", HTTP_HOST="demo.test")
        self.assertContains(r, "Sobre a Câmara")
        self.assertContains(r, "class=\"carrossel__slide\"", count=3)
