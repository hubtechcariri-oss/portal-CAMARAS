from datetime import date, datetime
from zoneinfo import ZoneInfo

from django.contrib.auth.models import User
from django.test import TestCase

from apps.camaras.tests.fabrica import criar_camara
from apps.legislativo.models import Materia, Sessao, Tramitacao, Vereador

TZ = ZoneInfo("America/Sao_Paulo")


class SessoesMateriasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.a = criar_camara("camara-a.test")
        cls.b = criar_camara("camara-b.test", "Câmara Municipal B")
        cls.ana = Vereador.objects.create(camara=cls.a, nome_parlamentar="Ana")
        cls.beto = Vereador.objects.create(camara=cls.a, nome_parlamentar="Beto")
        cls.sessao = Sessao.objects.create(camara=cls.a, numero=12, data_hora=datetime(2026, 10, 7, 9, tzinfo=TZ))
        cls.sessao.presentes.set([cls.ana, cls.beto])
        cls.pl = Materia.objects.create(
            camara=cls.a, tipo="pl", numero=45, ano=2026, data_apresentacao=date(2026, 9, 1),
            ementa="Institui o programa de coleta seletiva nas escolas municipais", situacao="aprov",
        )
        cls.pl.autores.set([cls.ana])
        Tramitacao.objects.create(materia=cls.pl, data=date(2026, 10, 7), descricao="Votação em plenário",
                                  sessao=cls.sessao, resultado="aprov", votos_sim=8, votos_nao=1, abstencoes=0)
        cls.req = Materia.objects.create(
            camara=cls.a, tipo="req", numero=3, ano=2026, data_apresentacao=date(2026, 9, 2),
            ementa="Requer informações sobre o transporte escolar", autor_externo="Mesa Diretora",
        )
        Materia.objects.create(camara=cls.a, tipo="ind", numero=9, ano=2026, data_apresentacao=date(2026, 9, 3),
                               ementa="Matéria rascunho", publicada=False)
        Materia.objects.create(camara=cls.b, tipo="pl", numero=1, ano=2026, data_apresentacao=date(2026, 9, 3),
                               ementa="Matéria da câmara B")

    def json(self, url):
        return self.client.get(url, HTTP_HOST="camara-a.test").json()

    def test_lista_de_materias_isolada_e_sem_rascunhos(self):
        ementas = {m["ementa"] for m in self.json("/materias/?formato=json")}
        self.assertEqual(ementas, {self.pl.ementa, self.req.ementa})

    def test_filtros_de_materias(self):
        self.assertEqual([m["numero"] for m in self.json("/materias/?formato=json&tipo=req")], [3])
        self.assertEqual([m["numero"] for m in self.json(f"/materias/?formato=json&autor={self.ana.pk}")], [45])
        self.assertEqual([m["numero"] for m in self.json("/materias/?formato=json&situacao=aprov")], [45])
        self.assertEqual([m["numero"] for m in self.json("/materias/?formato=json&q=coleta")], [45])
        # Stemming: "escola" também encontra "escolar".
        self.assertEqual(len(self.json("/materias/?formato=json&q=escola")), 2)

    def test_autoria_combina_vereadores_e_autor_externo(self):
        dados = {m["numero"]: m["autoria"] for m in self.json("/materias/?formato=json")}
        self.assertEqual(dados, {45: "Ana", 3: "Mesa Diretora"})

    def test_detalhe_da_materia_mostra_tramitacao_e_votos(self):
        r = self.client.get(f"/materias/{self.pl.pk}/", HTTP_HOST="camara-a.test")
        self.assertContains(r, "Votação em plenário")
        self.assertContains(r, "8 sim, 1 não")

    def test_materia_de_outra_camara_ou_rascunho_da_404(self):
        outra = Materia.objects.get(camara=self.b)
        rascunho = Materia.objects.get(publicada=False)
        for m in (outra, rascunho):
            self.assertEqual(self.client.get(f"/materias/{m.pk}/", HTTP_HOST="camara-a.test").status_code, 404)

    def test_sessao_lista_e_detalhe(self):
        dados = self.json("/sessoes/?formato=json")
        self.assertEqual(len(dados), 1)
        self.assertEqual(dados[0]["presentes"], 2)
        self.assertTrue(dados[0]["data_hora"].startswith("2026-10-07T09:00"))
        r = self.client.get(f"/sessoes/{self.sessao.pk}/", HTTP_HOST="camara-a.test")
        self.assertContains(r, "Presenças (2)")
        self.assertContains(r, self.pl.ementa[:30])

    def test_perfil_do_vereador_conta_materias_e_presencas(self):
        r = self.client.get(f"/vereadores/{self.ana.pk}/", HTTP_HOST="camara-a.test")
        self.assertContains(r, "<strong>1</strong> matéria(s)", html=False)
        self.assertContains(r, "<strong>1</strong> presença(s)", html=False)


class AdminRelacoesEntreCamarasTests(TestCase):
    def test_superusuario_nao_liga_autor_de_outra_camara(self):
        a = criar_camara("camara-a.test")
        b = criar_camara("camara-b.test", "Câmara Municipal B")
        intruso = Vereador.objects.create(camara=b, nome_parlamentar="Intruso")
        admin = User.objects.create_superuser("root", password="x")
        self.client.force_login(admin)
        r = self.client.post("/admin/legislativo/materia/add/", {
            "camara": a.pk, "tipo": "pl", "numero": 1, "ano": 2026, "data_apresentacao": "2026-01-01",
            "ementa": "x", "situacao": "tram", "publicada": "on", "autores": [intruso.pk],
            "tramitacoes-TOTAL_FORMS": 0, "tramitacoes-INITIAL_FORMS": 0,
        }, HTTP_HOST="painel.test")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "pertence a outra câmara")
        self.assertFalse(Materia.objects.exists())
