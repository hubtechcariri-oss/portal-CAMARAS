from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from apps.camaras.tests.fabrica import criar_camara
from apps.camaras.texto_rico import exibir, limpar_html
from apps.noticias.models import Noticia


class LimpezaTests(TestCase):
    def test_mantem_so_o_permitido(self):
        sujo = ('<h1>Sub</h1><div>Texto <strong>forte</strong> <em>it</em> <b>b</b> '
                '<a href="https://ex.com" onclick="x()" style="color:red">link</a>'
                '<a href="javascript:alert(1)">mau</a></div><script>alert(1)</script>'
                '<img src="x" onerror="y"><blockquote>cit</blockquote><ul><li>a</li></ul><span style="x">s</span>')
        limpo = limpar_html(sujo)
        self.assertIn("<h2>Sub</h2>", limpo)
        self.assertIn("<strong>forte</strong>", limpo)
        self.assertIn("<strong>b</strong>", limpo)
        self.assertIn('<a href="https://ex.com" rel="noopener noreferrer">link</a>', limpo)
        self.assertIn("<blockquote>cit</blockquote>", limpo)
        for proibido in ("script", "onclick", "style", "javascript:", "<img", "onerror", "<span"):
            self.assertNotIn(proibido, limpo)

    def test_texto_antigo_continua_com_quebras_de_linha(self):
        self.assertEqual(str(exibir("Linha 1\nLinha 2\n\nOutro <parágrafo>")),
                         "<p>Linha 1<br>Linha 2</p>\n\n<p>Outro &lt;parágrafo&gt;</p>")


class EditorNoPainelEPortalTests(TestCase):
    def setUp(self):
        self.camara = criar_camara("rico.test", "Câmara Municipal Rica")
        self.client.force_login(User.objects.create_superuser("adm_rico", "a@a.local", "x"))

    def test_formulario_usa_trix_e_grava_html_limpo_que_aparece_no_portal(self):
        r = self.client.get("/admin/noticias/noticia/add/")
        self.assertContains(r, "<trix-editor")
        self.assertContains(r, "vendor/trix-2.1.19/trix.umd.min.js")
        self.assertNotContains(r, "trix-button--icon-attach")
        agora = timezone.localtime()
        r = self.client.post("/admin/noticias/noticia/add/", {
            "camara": self.camara.pk, "titulo": "Rica", "slug": "rica", "resumo": "", "texto_alternativo": "",
            "corpo": '<div>Olá <strong>mundo</strong></div><h1>Pauta</h1><script>x()</script>',
            "publicada": "True",
            "publicada_em_0": agora.strftime("%d/%m/%Y"), "publicada_em_1": agora.strftime("%H:%M:%S"),
        })
        self.assertEqual(r.status_code, 302)
        n = Noticia.objects.get()
        self.assertEqual(n.corpo, "<div>Olá <strong>mundo</strong></div><h2>Pauta</h2>")
        pagina = self.client.get("/noticias/rica/", HTTP_HOST="rico.test")
        self.assertContains(pagina, "<div>Olá <strong>mundo</strong></div><h2>Pauta</h2>", html=False)

    def test_texto_vazio_no_editor_e_recusado(self):
        agora = timezone.localtime()
        r = self.client.post("/admin/noticias/noticia/add/", {
            "camara": self.camara.pk, "titulo": "Vazia", "slug": "vazia", "corpo": "<div><br></div>",
            "publicada": "True",
            "publicada_em_0": agora.strftime("%d/%m/%Y"), "publicada_em_1": agora.strftime("%H:%M:%S"),
        })
        self.assertContains(r, "Escreva o texto da notícia.")

    def test_noticia_antiga_em_texto_puro_abre_no_editor_como_paragrafos(self):
        n = Noticia.objects.create(camara=self.camara, titulo="Antiga", slug="antiga", corpo="Primeira\n\nSegunda")
        r = self.client.get(f"/admin/noticias/noticia/{n.pk}/change/")
        self.assertContains(r, "&lt;p&gt;Primeira&lt;/p&gt;")
