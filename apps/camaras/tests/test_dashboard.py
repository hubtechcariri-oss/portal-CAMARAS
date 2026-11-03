from datetime import date, timedelta

from django.contrib.auth.models import Permission, User
from django.test import TestCase
from django.utils import timezone

from apps.camaras import indicadores
from apps.camaras.models import Membro
from apps.esic.models import Pedido

from .fabrica import criar_camara


def pedido(camara, criado_ha, respondido_em_dias=None, prazo_dias=20):
    """Pedido criado há `criado_ha` dias; respondido `respondido_em_dias` dias depois (ou em aberto)."""
    p = Pedido.objects.create(camara=camara, nome="X", email="x@exemplo.com", pedido="Informação")
    criado = timezone.now() - timedelta(days=criado_ha)
    campos = {"criado_em": criado, "prazo": (timezone.localtime(criado) + timedelta(days=prazo_dias)).date()}
    if respondido_em_dias is not None:
        campos.update(situacao=Pedido.Situacao.RESPONDIDO, respondido_em=criado + timedelta(days=respondido_em_dias))
    Pedido.objects.filter(pk=p.pk).update(**campos)
    return p


class SerieMensalTests(TestCase):
    def test_doze_meses_terminando_no_atual_com_virada_de_ano(self):
        serie = indicadores._serie_mensal([date(2026, 2, 10), date(2026, 2, 11), date(2025, 3, 1)], date(2026, 2, 20))
        rotulos = [(b["rotulo"], b["ano"]) for b in serie["barras"]]
        self.assertEqual(rotulos[0], ("mar", 2025))
        self.assertEqual(rotulos[-1], ("fev", 2026))
        self.assertEqual(len(rotulos), 12)
        self.assertEqual(serie["barras"][-1]["valor"], 2)
        self.assertEqual(serie["barras"][-1]["altura"], 100)
        self.assertEqual(serie["barras"][0]["altura"], 50)
        self.assertEqual(serie["total"], 3)

    def test_serie_vazia_nao_divide_por_zero(self):
        serie = indicadores._serie_mensal([], date(2026, 11, 3))
        self.assertEqual({b["altura"] for b in serie["barras"]}, {0})


class AtendimentoTests(TestCase):
    def setUp(self):
        self.a = criar_camara("camara-a.test", "Câmara Municipal A")
        self.b = criar_camara("camara-b.test", "Câmara Municipal B")
        pedido(self.a, 60, respondido_em_dias=5)      # no prazo
        pedido(self.a, 90, respondido_em_dias=15)     # no prazo
        pedido(self.a, 120, respondido_em_dias=25)    # fora do prazo (prazo de 20 dias)
        pedido(self.a, 30)                            # em aberto, prazo vencido
        pedido(self.a, 400, respondido_em_dias=1)     # fora da janela de 12 meses
        pedido(self.b, 10, respondido_em_dias=30)     # outra câmara
        self.u = User.objects.create_user("atendente", password="x", is_staff=True)
        self.u.user_permissions.add(*Permission.objects.filter(content_type__app_label="esic"))
        Membro.objects.create(usuario=self.u, camara=self.a)

    def test_numeros_da_propria_camara(self):
        (fila,) = indicadores.atendimento(self.u)
        self.assertEqual(fila["recebidos"], 4)
        self.assertEqual(fila["concluidos"], 3)
        self.assertEqual(fila["no_prazo"], 2)
        self.assertEqual(fila["percentual_no_prazo"], 67)
        self.assertEqual(fila["tempo_medio"], 15)
        self.assertEqual(fila["vencidos"], 1)
        self.assertEqual(fila["estado"], "critico")
        self.assertEqual(fila["serie"]["total"], 4)

    def test_bloco_aparece_no_inicio_com_tabela_acessivel(self):
        self.client.force_login(self.u)
        r = self.client.get("/admin/", HTTP_HOST="camara-a.test")
        self.assertContains(r, "Atendimento ao cidadão")
        self.assertContains(r, "Respondidos no prazo")
        self.assertContains(r, "67%")
        self.assertContains(r, "2 de 3 respondidos")
        self.assertContains(r, '<table class="visually-hidden">')
        self.assertNotContains(r, "Ouvidoria (manifestações)")  # sem permissão na Ouvidoria

    def test_sem_permissao_o_bloco_some(self):
        u = User.objects.create_user("comunicacao", password="x", is_staff=True)
        Membro.objects.create(usuario=u, camara=self.a)
        self.assertIsNone(indicadores.atendimento(u))
        self.client.force_login(u)
        r = self.client.get("/admin/", HTTP_HOST="camara-a.test")
        self.assertNotContains(r, "Atendimento ao cidadão")

    def test_sem_respostas_mostra_traco(self):
        Pedido.objects.all().delete()
        (fila,) = indicadores.atendimento(self.u)
        self.assertIsNone(fila["percentual_no_prazo"])
        self.assertEqual(fila["rotulo_estado"], "Sem respostas")
