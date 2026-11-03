from datetime import timedelta

from django.contrib.auth.models import Group, Permission, User
from django.test import TestCase
from django.utils import timezone

from apps.camaras.models import Membro
from apps.esic.models import Pedido

from .fabrica import criar_camara


class PainelInicioTests(TestCase):
    def setUp(self):
        self.a = criar_camara("camara-a.test", "Câmara Municipal A")
        self.b = criar_camara("camara-b.test", "Câmara Municipal B")
        for camara, dias in [(self.a, -1), (self.a, 2), (self.a, 20), (self.b, -5)]:
            p = Pedido.objects.create(camara=camara, nome="X", email="x@exemplo.com", pedido="Informação")
            Pedido.objects.filter(pk=p.pk).update(prazo=timezone.localdate() + timedelta(days=dias))

    def entrar(self, usuario):
        self.client.force_login(usuario)
        return self.client.get("/admin/", HTTP_HOST="camara-a.test")

    def test_pendencias_contam_so_a_propria_camara(self):
        u = User.objects.create_user("atendente", password="x", is_staff=True)
        u.user_permissions.add(*Permission.objects.filter(content_type__app_label="esic"))
        Membro.objects.create(usuario=u, camara=self.a)
        r = self.entrar(u)
        self.assertContains(r, "Pedidos de informação (e-SIC)")
        self.assertContains(r, '<span class="painel-fila__numero">3</span>', html=False)
        self.assertContains(r, "1 com prazo vencido")
        self.assertContains(r, "Câmara Municipal A")  # nome no cabeçalho

    def test_comunicacao_ve_atalhos_mas_nao_ve_esic(self):
        u = User.objects.create_user("comunicacao", password="x", is_staff=True)
        u.groups.add(Group.objects.get(name="Comunicação"))
        Membro.objects.create(usuario=u, camara=self.a)
        r = self.entrar(u)
        self.assertNotContains(r, "Pedidos de informação (e-SIC)")
        self.assertContains(r, "Nova notícia")
        self.assertContains(r, "Brasão, cores e contatos")
        self.assertNotContains(r, "Nova sessão")
