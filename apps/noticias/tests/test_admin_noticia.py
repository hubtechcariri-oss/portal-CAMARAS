from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from apps.camaras.models import Membro
from apps.camaras.tests.fabrica import criar_camara
from apps.noticias.models import Noticia


class FormularioNoticiaTests(TestCase):
    """O formulário em duas colunas mantém criar, editar, agendar e excluir funcionando."""

    def setUp(self):
        self.camara = criar_camara("form.test", "Câmara Municipal Form")
        self.u = User.objects.create_superuser("adm_form", "a@a.local", "x")
        self.client.force_login(self.u)

    def dados(self, **extra):
        quando = extra.pop("quando", timezone.localtime())
        base = {
            "camara": self.camara.pk, "titulo": "Sessão especial", "slug": "sessao-especial",
            "resumo": "Resumo", "corpo": "Texto", "texto_alternativo": "",
            "publicada": "True",
            "publicada_em_0": quando.strftime("%d/%m/%Y"), "publicada_em_1": quando.strftime("%H:%M:%S"),
        }
        base.update(extra)
        return base

    def test_tela_tem_duas_colunas_e_acoes_no_cartao(self):
        r = self.client.get("/admin/noticias/noticia/add/")
        self.assertContains(r, 'class="form-duas-colunas__lateral"')
        self.assertContains(r, "data-previa-slug")
        self.assertContains(r, 'data-contador="300"')
        self.assertEqual(r.content.decode().count('name="_save"'), 2)  # topo + cartão

    def test_criar_editar_agendar_e_excluir(self):
        r = self.client.post("/admin/noticias/noticia/add/", self.dados())
        self.assertEqual(r.status_code, 302, getattr(r, "context", None) and r.context["adminform"].form.errors)
        n = Noticia.objects.get()
        self.assertTrue(n.publicada)

        r = self.client.post(f"/admin/noticias/noticia/{n.pk}/change/", self.dados(publicada="False", titulo="Editada"))
        self.assertEqual(r.status_code, 302)
        n.refresh_from_db()
        self.assertEqual((n.titulo, n.publicada), ("Editada", False))

        amanha = timezone.localtime() + timedelta(days=1)
        r = self.client.post(f"/admin/noticias/noticia/{n.pk}/change/", self.dados(quando=amanha))
        self.assertEqual(r.status_code, 302)
        n.refresh_from_db()
        self.assertTrue(n.publicada and n.publicada_em > timezone.now())

        r = self.client.post(f"/admin/noticias/noticia/{n.pk}/delete/", {"post": "yes"})
        self.assertEqual(r.status_code, 302)
        self.assertFalse(Noticia.objects.exists())

    def test_membro_de_uma_camara_nao_ve_o_campo_camara(self):
        u = User.objects.create_user("redator", password="x", is_staff=True)
        from django.contrib.auth.models import Permission
        u.user_permissions.add(*Permission.objects.filter(content_type__app_label="noticias"))
        Membro.objects.create(usuario=u, camara=self.camara)
        self.client.force_login(u)
        r = self.client.get("/admin/noticias/noticia/add/")
        self.assertNotContains(r, 'name="camara"')
        dados = self.dados()
        dados.pop("camara")
        r = self.client.post("/admin/noticias/noticia/add/", dados)
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Noticia.objects.get().camara, self.camara)
