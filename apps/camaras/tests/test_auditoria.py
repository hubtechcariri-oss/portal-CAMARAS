from django.contrib.auth.models import Group, Permission, User
from django.test import RequestFactory, TestCase

from apps.camaras import auditoria
from apps.camaras.models import Membro, RegistroAuditoria
from apps.camaras.tests.fabrica import criar_camara
from apps.noticias.models import Noticia
from apps.transparencia.models import Despesa


class ComUsuario:
    """Simula uma requisição de um usuário logado (o que o middleware faz)."""

    def __init__(self, usuario, ip="200.1.2.3"):
        self.request = RequestFactory().get("/admin/", REMOTE_ADDR=ip)
        self.request.user = usuario

    def __enter__(self):
        auditoria._local.request = self.request

    def __exit__(self, *exc):
        auditoria._local.request = None


class RegistroTests(TestCase):
    def setUp(self):
        self.a = criar_camara("camara-a.test", "Câmara Municipal A")
        self.u = User.objects.create_user("maria", password="x", first_name="Maria", last_name="Souza", is_staff=True)
        Membro.objects.create(usuario=self.u, camara=self.a)

    def test_criar_alterar_e_excluir(self):
        with ComUsuario(self.u):
            n = Noticia.objects.create(camara=self.a, titulo="Sessão solene", slug="s", corpo="<p>Texto</p>")
            n.titulo = "Sessão solene de 15 de novembro"
            n.publicada = False
            n.save()
            n.save()  # sem mudança: não registra de novo
            n.delete()
        criou, alterou, excluiu = RegistroAuditoria.objects.order_by("pk")
        self.assertEqual((criou.acao, criou.usuario_nome, criou.camara, criou.ip), ("criou", "Maria Souza", self.a, "200.1.2.3"))
        self.assertEqual(criou.tipo, "notícia")
        self.assertEqual(alterou.detalhes["título"], {"antes": "Sessão solene", "depois": "Sessão solene de 15 de novembro"})
        self.assertEqual(alterou.detalhes["publicada"], {"antes": "sim", "depois": "não"})
        self.assertNotIn("atualizado_em", alterou.detalhes)
        self.assertEqual(excluiu.acao, "excluiu")
        self.assertEqual(excluiu.camara, self.a)
        self.assertEqual(excluiu.detalhes["corpo"], "Texto")  # sem tags HTML

    def test_sem_usuario_logado_nao_registra(self):
        Noticia.objects.create(camara=self.a, titulo="Importada", slug="i", corpo="x")
        self.assertFalse(RegistroAuditoria.objects.exists())

    def test_importacoes_ficam_de_fora(self):
        with ComUsuario(self.u):
            Despesa.objects.create(camara=self.a, id_origem="1", ano=2026, numero_empenho="1", valor_empenhado=1,
                                   data_empenho="2026-09-01")
        self.assertFalse(RegistroAuditoria.objects.exists())

    def test_senha_nunca_e_guardada(self):
        with ComUsuario(self.u):
            self.u.set_password("nova-senha-secreta")
            self.u.save()
        r = RegistroAuditoria.objects.get()
        self.assertEqual(r.detalhes["senha"], {"antes": "••••••", "depois": "(alterada)"})
        self.assertNotIn("nova-senha-secreta", str(r.detalhes))
        self.assertNotIn(self.u.password, str(r.detalhes))

    def test_grupos_do_usuario(self):
        grupo = Group.objects.create(name="Comunicação 2")
        with ComUsuario(self.u):
            self.u.groups.add(grupo)
        r = RegistroAuditoria.objects.get()
        self.assertEqual(r.detalhes["grupos"]["depois"], "incluiu: Comunicação 2")

    def test_ip_atras_de_proxy(self):
        request = RequestFactory().get("/", HTTP_X_FORWARDED_FOR="189.10.20.30, 10.0.0.1", REMOTE_ADDR="10.0.0.1")
        self.assertEqual(auditoria.ip_de(request), "189.10.20.30")


class AcessoEPainelTests(TestCase):
    def setUp(self):
        self.a = criar_camara("camara-a.test", "Câmara Municipal A")
        self.b = criar_camara("camara-b.test", "Câmara Municipal B")
        self.u = User.objects.create_user("joao", password="senha-forte-123", is_staff=True)
        Membro.objects.create(usuario=self.u, camara=self.a)

    def test_entrada_e_tentativa_recusada(self):
        self.client.post("/admin/login/", {"username": "joao", "password": "errada"}, HTTP_HOST="camara-a.test")
        self.client.post("/admin/login/", {"username": "joao", "password": "senha-forte-123"}, HTTP_HOST="camara-a.test")
        falhou, entrou = RegistroAuditoria.objects.order_by("pk")
        self.assertEqual((falhou.acao, falhou.detalhes), ("falhou", {"usuário informado": "joao"}))
        self.assertEqual((entrou.acao, entrou.usuario, entrou.camara), ("entrou", self.u, self.a))
        self.assertEqual(RegistroAuditoria.objects.count(), 2)  # o last_login não vira "alterou"

    def test_tela_so_leitura_e_so_da_propria_camara(self):
        RegistroAuditoria.objects.create(camara=self.a, usuario_nome="Fulano", acao="alterou", objeto="Notícia da A",
                                         detalhes={"título": {"antes": "Velho", "depois": "Novo"}})
        RegistroAuditoria.objects.create(camara=self.b, usuario_nome="Beltrano", acao="criou", objeto="Notícia da B")
        self.u.groups.add(Group.objects.get(name="Auditoria"))
        self.client.force_login(self.u)
        r = self.client.get("/admin/camaras/registroauditoria/", HTTP_HOST="camara-a.test")
        self.assertContains(r, "Notícia da A")
        self.assertNotContains(r, "Notícia da B")
        self.assertNotContains(r, "registroauditoria/add/")
        registro = RegistroAuditoria.objects.get(objeto="Notícia da A")
        r = self.client.get(f"/admin/camaras/registroauditoria/{registro.pk}/change/", HTTP_HOST="camara-a.test")
        self.assertContains(r, "Velho")
        self.assertContains(r, "Novo")
        self.assertNotContains(r, 'name="_save"')
        r = self.client.post(f"/admin/camaras/registroauditoria/{registro.pk}/delete/", {"post": "yes"},
                             HTTP_HOST="camara-a.test")
        self.assertEqual(r.status_code, 403)

    def test_sem_o_grupo_nao_ve(self):
        self.client.force_login(self.u)
        r = self.client.get("/admin/camaras/registroauditoria/", HTTP_HOST="camara-a.test")
        self.assertEqual(r.status_code, 403)

    def test_exportar_csv(self):
        RegistroAuditoria.objects.create(camara=self.a, usuario_nome="Fulano", acao="alterou", objeto="Notícia",
                                         detalhes={"título": {"antes": "Velho", "depois": "Novo"}})
        self.u.groups.add(Group.objects.get(name="Auditoria"))
        self.client.force_login(self.u)
        ids = list(RegistroAuditoria.objects.filter(camara=self.a).values_list("pk", flat=True))
        r = self.client.post("/admin/camaras/registroauditoria/", {"action": "exportar_csv", "_selected_action": ids},
                             HTTP_HOST="camara-a.test")
        corpo = r.content.decode("utf-8-sig")
        self.assertIn("título: Velho → Novo", corpo)
        self.assertIn("Fulano", corpo)
