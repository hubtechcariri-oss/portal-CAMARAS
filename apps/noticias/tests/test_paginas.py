from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.camaras.tests.fabrica import criar_camara
from apps.noticias.models import Noticia


def noticia(camara, slug, titulo, dias=0, **campos):
    return Noticia.objects.create(camara=camara, slug=slug, titulo=titulo, corpo=campos.pop("corpo", "Texto."),
                                  publicada_em=timezone.now() - timedelta(days=dias), **campos)


class ListaTests(TestCase):
    def setUp(self):
        self.a = criar_camara("camara-a.test", "Câmara Municipal A")
        noticia(self.a, "orcamento", "Câmara aprova orçamento", 1, resumo="Segunda votação.")
        noticia(self.a, "coleta", "Coleta seletiva nas escolas", 5)
        noticia(self.a, "antiga", "Sessão solene", 400)
        noticia(self.a, "futura", "Notícia agendada", -3)

    def get(self, url):
        return self.client.get(url, HTTP_HOST="camara-a.test")

    def test_mais_recente_em_destaque_e_futura_oculta(self):
        r = self.get("/noticias/")
        self.assertEqual(r.context["destaque"].slug, "orcamento")
        self.assertEqual([n.slug for n in r.context["itens"]], ["coleta", "antiga"])
        self.assertContains(r, "Mais recente")
        self.assertNotContains(r, "Notícia agendada")

    def test_busca_e_ano_sem_destaque(self):
        r = self.get("/noticias/?q=coleta")
        self.assertIsNone(r.context["destaque"])
        self.assertEqual([n.slug for n in r.context["itens"]], ["coleta"])
        self.assertContains(r, "1 notícia encontrada")
        ano = (timezone.now() - timedelta(days=400)).year
        r = self.get(f"/noticias/?ano={ano}")
        self.assertIn("antiga", [n.slug for n in r.context["itens"]])

    def test_sem_resultado(self):
        self.assertContains(self.get("/noticias/?q=xyzzy"), "Nenhuma notícia encontrada")


class DetalheTests(TestCase):
    def setUp(self):
        self.a = criar_camara("camara-a.test", "Câmara Municipal A")
        self.n = noticia(self.a, "orcamento", "Câmara aprova orçamento", corpo="Primeira linha.\n\nSegunda linha.")
        noticia(self.a, "coleta", "Coleta seletiva", 2)

    def test_texto_puro_vira_paragrafos_sem_mostrar_tags(self):
        r = self.client.get("/noticias/orcamento/", HTTP_HOST="camara-a.test")
        self.assertContains(r, "<p>Primeira linha.</p>", html=False)
        self.assertNotContains(r, "&lt;p&gt;")
        self.assertContains(r, "<p>Segunda linha.</p>", html=False)

    def test_leitura_compartilhar_e_outras(self):
        r = self.client.get("/noticias/orcamento/", HTTP_HOST="camara-a.test")
        self.assertContains(r, "1 min de leitura")
        self.assertContains(r, "api.whatsapp.com/send")
        self.assertEqual([n.slug for n in r.context["outras"]], ["coleta"])
