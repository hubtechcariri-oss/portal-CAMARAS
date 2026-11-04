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


class TransparenciaTests(TestCase):
    def setUp(self):
        from apps.transparencia.models import CategoriaTransparencia, Documento

        self.a = criar_camara("camara-a.test", "Câmara Municipal A")
        self.b = criar_camara("camara-b.test", "Câmara Municipal B")
        CategoriaTransparencia.objects.update(obrigatoria=False)
        self.rgf, self.contratos, self.diarias, self.receitas = [
            CategoriaTransparencia.objects.get(slug=s)
            for s in ["relatorio-de-gestao-fiscal-rgf", "contratos", "diarias", "receitas"]
        ]
        CategoriaTransparencia.objects.filter(pk__in=[self.rgf.pk, self.contratos.pk, self.diarias.pk, self.receitas.pk]).update(obrigatoria=True)
        hoje = timezone.localdate()
        Documento.objects.create(camara=self.a, categoria=self.rgf, titulo="RGF", data=hoje, descricao="x")
        Documento.objects.create(camara=self.a, categoria=self.contratos, titulo="Antigo", data=hoje - timedelta(days=500), descricao="x")
        Documento.objects.create(camara=self.a, categoria=self.receitas, titulo="Rascunho", data=hoje, descricao="x", publicado=False)
        Documento.objects.create(camara=self.b, categoria=self.diarias, titulo="Outra câmara", data=hoje, descricao="x")
        self.u = User.objects.create_user("transp", password="x", is_staff=True)
        self.u.user_permissions.add(*Permission.objects.filter(content_type__app_label="transparencia",
                                                               codename__in=["view_documento", "add_documento"]))
        Membro.objects.create(usuario=self.u, camara=self.a)

    def test_conta_so_obrigatorias_publicadas_e_recentes_da_camara(self):
        t = indicadores.transparencia(self.u, self.a)
        self.assertEqual((t["total"], t["publicados"], t["desatualizados"], t["sem_publicacao"]), (4, 1, 1, 2))
        self.assertEqual(t["percentual"], 25)
        self.assertEqual(t["estado"], "critico")
        nomes = [p["nome"] for p in t["pendencias"]]
        self.assertNotIn(self.rgf.nome, nomes)
        self.assertEqual(t["pendencias"][-1]["nome"], self.contratos.nome)  # desatualizado depois dos sem publicação
        self.assertTrue(t["pendencias"][0]["url"].endswith(f"?categoria={t_pk(t, self)}"))
        self.assertFalse(t["catalogo_inteiro"])

    def test_sem_obrigatorias_usa_catalogo_inteiro(self):
        from apps.transparencia.models import CategoriaTransparencia

        CategoriaTransparencia.objects.update(obrigatoria=False)
        t = indicadores.transparencia(self.u, self.a)
        self.assertTrue(t["catalogo_inteiro"])
        self.assertEqual(t["total"], CategoriaTransparencia.objects.count())

    def test_nao_mostra_camara_alheia_nem_sem_permissao(self):
        self.assertIsNone(indicadores.transparencia(self.u, self.b))
        u = User.objects.create_user("semperm", password="x", is_staff=True)
        Membro.objects.create(usuario=u, camara=self.a)
        self.assertIsNone(indicadores.transparencia(u, self.a))

    def test_bloco_no_inicio(self):
        self.client.force_login(self.u)
        r = self.client.get("/admin/", HTTP_HOST="camara-a.test")
        self.assertContains(r, "itens obrigatórios (PNTP)")
        self.assertContains(r, "1 de 4 itens com publicação")
        self.assertContains(r, "nada publicado")
        self.assertContains(r, "A avaliação oficial do PNTP")


def t_pk(t, caso):
    """Id da primeira pendência (ordem: sem publicação, por grupo e nome)."""
    from apps.transparencia.models import CategoriaTransparencia

    return CategoriaTransparencia.objects.get(nome=t["pendencias"][0]["nome"]).pk


class LegislativoTests(TestCase):
    def setUp(self):
        from datetime import datetime

        from apps.legislativo.models import Materia, Norma, Sessao, Vereador

        self.a = criar_camara("camara-a.test", "Câmara Municipal A")
        self.b = criar_camara("camara-b.test", "Câmara Municipal B")
        hoje = timezone.localdate()
        ano = hoje.year
        vs = [Vereador.objects.create(camara=self.a, nome_parlamentar=f"V{i}") for i in range(4)]
        for i, (tipo, sit) in enumerate([("req", "aprov"), ("req", "tram"), ("pl", "aprov")]):
            Materia.objects.create(camara=self.a, tipo=tipo, numero=i + 1, ano=ano, data_apresentacao=hoje,
                                   ementa="x", situacao=sit)
        Materia.objects.create(camara=self.a, tipo="ind", numero=9, ano=ano - 1, data_apresentacao=date(ano - 1, 1, 5),
                               ementa="x", situacao="tram")
        Materia.objects.create(camara=self.b, tipo="req", numero=1, ano=ano, data_apresentacao=hoje, ementa="x")
        passada = timezone.now() - timedelta(days=1)
        if passada.year == ano:
            s = Sessao.objects.create(camara=self.a, numero=1, data_hora=passada)
            s.presentes.set(vs[:3])
        Sessao.objects.create(camara=self.a, numero=2, data_hora=timezone.now() + timedelta(days=3))  # futura
        Norma.objects.create(camara=self.a, tipo="lei", numero="1", ano=ano, data=hoje, ementa="x")
        self.passada_no_ano = passada.year == ano
        self.u = User.objects.create_user("leg", password="x", is_staff=True)
        self.u.user_permissions.add(*Permission.objects.filter(content_type__app_label="legislativo",
                                                               codename__startswith="view_"))
        Membro.objects.create(usuario=self.u, camara=self.a)

    def test_numeros_do_ano_da_propria_camara(self):
        l = indicadores.legislativo(self.u)
        n = {x["rotulo"]: x for x in l["numeros"]}
        self.assertEqual(n["Matérias apresentadas"]["valor"], 3)
        self.assertEqual(n["Matérias apresentadas"]["apoio"], "2 aprovadas")
        self.assertEqual(n["Em tramitação"]["valor"], 2)  # inclui a do ano passado
        self.assertEqual(n["Leis e normas"]["valor"], 1)
        if self.passada_no_ano:
            self.assertEqual(n["Sessões realizadas"]["valor"], 1)  # a futura não conta
            self.assertEqual(n["Sessões realizadas"]["apoio"], "presença média de 75%")
        self.assertEqual(l["tipos"][0], {"rotulo": "Requerimento", "valor": 2, "largura": 100})
        self.assertEqual(l["tipos"][1]["largura"], 50)

    def test_bloco_no_inicio_e_links_validos(self):
        self.client.force_login(self.u)
        r = self.client.get("/admin/", HTTP_HOST="camara-a.test")
        self.assertContains(r, "Produção legislativa")
        self.assertContains(r, "Matérias por tipo")
        for n in r.context["dashboard"]["legislativo"]["numeros"]:
            lista = self.client.get(n["url"], HTTP_HOST="camara-a.test")
            self.assertEqual(lista.status_code, 200, n["url"])  # filtro aceito pelo admin (sem ?e=1)

    def test_sem_permissao_o_bloco_some(self):
        u = User.objects.create_user("semleg", password="x", is_staff=True)
        Membro.objects.create(usuario=u, camara=self.a)
        self.assertIsNone(indicadores.legislativo(u))
