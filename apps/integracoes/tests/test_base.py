from datetime import date, timedelta
from io import StringIO
from unittest import mock

from django.contrib.auth.models import Permission, User
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from apps.camaras.models import Membro
from apps.camaras.tests.fabrica import criar_camara
from apps.integracoes import conectores
from apps.integracoes.conectores import Conector, ErroDeImportacao, Resultado, executar, periodo_padrao
from apps.integracoes.models import FonteDados, Importacao


class ConectorFalso(Conector):
    chamadas = []

    def importar(self, fonte, desde, ate):
        ConectorFalso.chamadas.append((fonte.pk, desde, ate))
        modo = fonte.configuracao.get("modo")
        if modo == "erro":
            raise ErroDeImportacao("CNPJ não cadastrado.")
        if modo == "quebra":
            raise ValueError("formato inesperado")
        return Resultado(novos=3, atualizados=1)


def com_conector_falso(teste):
    return mock.patch.dict(conectores.CONECTORES, {"pncp": ConectorFalso})(teste)


class ExecutarTests(TestCase):
    def setUp(self):
        ConectorFalso.chamadas = []
        self.a = criar_camara("camara-a.test", "Câmara Municipal A")
        self.fonte = FonteDados.objects.create(camara=self.a, tipo="pncp")

    @com_conector_falso
    def test_sucesso_registra_e_marca_ultimo_sucesso(self):
        r = executar(self.fonte)
        self.assertEqual((r.situacao, r.novos, r.atualizados), ("sucesso", 3, 1))
        self.fonte.refresh_from_db()
        self.assertIsNotNone(self.fonte.ultimo_sucesso)
        self.assertFalse(self.fonte.atrasada)
        _, desde, ate = ConectorFalso.chamadas[0]
        self.assertEqual(ate - desde, timedelta(days=conectores.CARGA_INICIAL_DIAS))  # carga inicial: um ano

    @com_conector_falso
    def test_depois_do_primeiro_sucesso_busca_so_a_ultima_semana(self):
        self.fonte.ultimo_sucesso = timezone.now() - timedelta(days=1)
        desde, ate = periodo_padrao(self.fonte)
        self.assertEqual((ate - desde).days, 1 + conectores.SOBREPOSICAO_DIAS)

    @com_conector_falso
    def test_erro_esperado_vira_mensagem_e_nao_marca_sucesso(self):
        self.fonte.configuracao = {"modo": "erro"}
        self.fonte.save()
        r = executar(self.fonte)
        self.assertEqual((r.situacao, r.mensagem), ("erro", "CNPJ não cadastrado."))
        self.fonte.refresh_from_db()
        self.assertIsNone(self.fonte.ultimo_sucesso)
        self.assertIsNotNone(self.fonte.ultima_execucao)

    @com_conector_falso
    def test_erro_inesperado_nao_derruba_a_execucao(self):
        self.fonte.configuracao = {"modo": "quebra"}
        self.fonte.save()
        r = executar(self.fonte)
        self.assertEqual(r.situacao, "erro")
        self.assertIn("ValueError: formato inesperado", r.mensagem)

    def test_tipo_sem_conector(self):
        with mock.patch.dict(conectores.CONECTORES, {}, clear=True):
            with mock.patch("apps.integracoes.conectores.pncp", create=True):
                r = executar(self.fonte)
        self.assertEqual(r.situacao, "erro")

    @com_conector_falso
    def test_comando_roda_so_fontes_ativas_e_aceita_periodo(self):
        b = criar_camara("camara-b.test", "Câmara Municipal B")
        FonteDados.objects.create(camara=b, tipo="pncp", ativa=False)
        saida = StringIO()
        call_command("importar_dados", "--desde", "2026-01-01", stdout=saida)
        self.assertEqual(len(ConectorFalso.chamadas), 1)
        self.assertEqual(ConectorFalso.chamadas[0][1], date(2026, 1, 1))
        self.assertIn("3 novos, 1 atualizados", saida.getvalue())


class PainelTests(TestCase):
    def setUp(self):
        self.a = criar_camara("camara-a.test", "Câmara Municipal A")
        self.b = criar_camara("camara-b.test", "Câmara Municipal B")
        self.fa = FonteDados.objects.create(camara=self.a, tipo="pncp")
        self.fb = FonteDados.objects.create(camara=self.b, tipo="pncp")
        Importacao.objects.create(fonte=self.fa, situacao="erro", mensagem="Origem fora do ar.\nDetalhes")
        Importacao.objects.create(fonte=self.fb, situacao="erro", mensagem="Erro da outra câmara")
        self.u = User.objects.create_user("ti", password="x", is_staff=True)
        self.u.user_permissions.add(*Permission.objects.filter(content_type__app_label="integracoes"))
        Membro.objects.create(usuario=self.u, camara=self.a)
        self.client.force_login(self.u)

    def test_inicio_avisa_so_a_propria_camara(self):
        r = self.client.get("/admin/", HTTP_HOST="camara-a.test")
        self.assertContains(r, "Fontes de dados com problema")
        self.assertContains(r, "Origem fora do ar.")
        self.assertNotContains(r, "Erro da outra câmara")

    def test_sem_problema_nao_avisa(self):
        Importacao.objects.filter(fonte=self.fa).update(situacao="sucesso")
        FonteDados.objects.filter(pk=self.fa.pk).update(ultimo_sucesso=timezone.now())
        r = self.client.get("/admin/", HTTP_HOST="camara-a.test")
        self.assertNotContains(r, "Fontes de dados com problema")

    def test_listas_do_painel_isoladas(self):
        r = self.client.get("/admin/integracoes/importacao/", HTTP_HOST="camara-a.test")
        self.assertEqual(r.context["cl"].result_count, 1)
        r = self.client.get(f"/admin/integracoes/fontedados/{self.fb.pk}/change/", HTTP_HOST="camara-a.test")
        self.assertNotEqual(r.status_code, 200)

    @com_conector_falso
    def test_acao_importar_agora(self):
        # Em teste, roda na mesma thread (a transação do TestCase não é vista por outra thread).
        sincrono = lambda ids: [executar(f) for f in FonteDados.objects.filter(pk__in=ids)]  # noqa: E731
        with mock.patch.object(conectores, "executar_em_segundo_plano", side_effect=sincrono):
            r = self.client.post("/admin/integracoes/fontedados/",
                                 {"action": "importar_agora", "_selected_action": [self.fa.pk]},
                                 HTTP_HOST="camara-a.test", follow=True)
        self.assertContains(r, "Importação iniciada")
        self.assertEqual(self.fa.importacoes.first().novos, 3)
        r = self.client.get(f"/admin/integracoes/fontedados/{self.fa.pk}/change/", HTTP_HOST="camara-a.test")
        self.assertContains(r, "Últimas importações")

    def test_nao_inicia_duas_vezes_a_mesma_fonte(self):
        Importacao.objects.create(fonte=self.fa, desde=date(2026, 1, 1))  # rodando
        with mock.patch.object(conectores, "executar_em_segundo_plano") as iniciar:
            r = self.client.post("/admin/integracoes/fontedados/",
                                 {"action": "importar_agora", "_selected_action": [self.fa.pk]},
                                 HTTP_HOST="camara-a.test", follow=True)
        iniciar.assert_not_called()
        self.assertContains(r, "já há uma importação em andamento")
