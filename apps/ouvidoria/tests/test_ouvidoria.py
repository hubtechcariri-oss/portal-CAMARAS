from datetime import timedelta
from unittest import mock

from django.contrib.auth.models import Permission, User
from django.test import TestCase
from django.utils import timezone

from apps.camaras.models import Membro
from apps.camaras.tests.fabrica import criar_camara
from apps.ouvidoria.models import Manifestacao

BASE = {"tipo": "reclamacao", "assunto": "Iluminação", "descricao": "Poste apagado na rua X.",
        "ciente_privacidade": "on"}


class OuvidoriaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.a = criar_camara("camara-a.test")
        cls.b = criar_camara("camara-b.test", "Câmara Municipal B")

    def enviar(self, **dados):
        return self.client.post("/ouvidoria/", {**BASE, **dados}, HTTP_HOST="camara-a.test", follow=True)

    def test_identificada_fluxo_completo(self):
        r = self.enviar(nome="Maria", email="maria@exemplo.com", sigilo="on")
        m = Manifestacao.objects.get()
        self.assertEqual((m.camara, m.nome, m.sigilo), (self.a, "Maria", True))
        self.assertEqual(m.prazo, timezone.localdate() + timedelta(days=30))
        self.assertContains(r, m.protocolo)
        url = f"/ouvidoria/consulta/?protocolo={m.protocolo}&codigo={m.codigo_consulta}"
        self.assertContains(self.client.get(url, HTTP_HOST="camara-a.test"), "Poste apagado")
        self.assertNotContains(self.client.get(url, HTTP_HOST="camara-b.test"), "Poste apagado")

    def test_anonima_nao_guarda_dados_pessoais(self):
        self.enviar(anonima="on", nome="Fulano", email="f@x.com", telefone="999")
        m = Manifestacao.objects.get()
        self.assertTrue(m.anonima)
        self.assertEqual((m.nome, m.email, m.telefone), ("", "", ""))

    def test_identificada_exige_nome_e_email(self):
        r = self.enviar(nome="Maria")
        self.assertContains(r, "marque a manifestação como anônima")
        self.assertFalse(Manifestacao.objects.exists())

    def test_exige_ciencia_e_bloqueia_robo(self):
        self.enviar(anonima="on", ciente_privacidade="")
        self.enviar(anonima="on", site="spam")
        self.assertFalse(Manifestacao.objects.exists())

    def test_protocolo_independente_do_esic_e_por_camara(self):
        from apps.esic.models import Pedido

        Pedido.objects.create(camara=self.a, nome="x", email="x@x.com", pedido="x")
        m1 = Manifestacao.objects.create(camara=self.a, tipo="elogio", assunto="a", descricao="b", anonima=True)
        m2 = Manifestacao.objects.create(camara=self.b, tipo="elogio", assunto="a", descricao="b", anonima=True)
        ano = timezone.localdate().year
        self.assertEqual((m1.protocolo, m2.protocolo), (f"{ano}00001", f"{ano}00001"))

    def test_prazo_prorrogacao_unica_e_vencimento(self):
        m = Manifestacao.objects.create(camara=self.a, tipo="denuncia", assunto="a", descricao="b", anonima=True)
        m.prorrogar()
        self.assertEqual(m.prazo, timezone.localdate() + timedelta(days=60))
        with self.assertRaises(ValueError):
            m.prorrogar()
        with mock.patch("django.utils.timezone.localdate", return_value=timezone.localdate() + timedelta(days=61)):
            self.assertTrue(m.vencida)

    def test_resposta_registra_data(self):
        m = Manifestacao.objects.create(camara=self.a, tipo="sugestao", assunto="a", descricao="b", anonima=True)
        m.situacao, m.resposta = "respondida", "Obrigado."
        m.save()
        self.assertIsNotNone(m.respondida_em)


class AdminOuvidoriaTests(TestCase):
    def test_ouvidor_ve_so_a_propria_camara_e_resumo(self):
        a = criar_camara("camara-a.test")
        b = criar_camara("camara-b.test", "Câmara Municipal B")
        Manifestacao.objects.create(camara=a, tipo="elogio", assunto="Elogio A", descricao="x", anonima=True)
        Manifestacao.objects.create(camara=b, tipo="elogio", assunto="Elogio B", descricao="x", anonima=True)
        ouvidor = User.objects.create_user("ouvidor", password="x", is_staff=True)
        ouvidor.user_permissions.set(Permission.objects.filter(content_type__app_label="ouvidoria"))
        Membro.objects.create(usuario=ouvidor, camara=a)
        self.client.force_login(ouvidor)
        r = self.client.get("/admin/ouvidoria/manifestacao/", HTTP_HOST="painel.test")
        self.assertContains(r, "Elogio A")
        self.assertNotContains(r, "Elogio B")
        self.assertContains(r, "Elogio: 1 (1 em aberto)")
        m = Manifestacao.objects.get(camara=a)
        self.assertEqual(
            self.client.get(f"/admin/ouvidoria/manifestacao/{m.pk}/change/", HTTP_HOST="painel.test").status_code, 200
        )
