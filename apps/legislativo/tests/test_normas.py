from datetime import date

from django.test import TestCase

from apps.camaras.tests.fabrica import criar_camara
from apps.legislativo.models import Norma


class BuscaNormasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.a = criar_camara()
        Norma.objects.create(camara=cls.a, tipo="lei", numero="10", ano=2025, data=date(2025, 3, 1),
                             ementa="Dispõe sobre a denominação de ruas", texto="")
        Norma.objects.create(camara=cls.a, tipo="res", numero="2", ano=2026, data=date(2026, 2, 1),
                             ementa="Altera o regimento", texto="trata das sessões ordinárias")
        Norma.objects.create(camara=cls.a, tipo="lei", numero="11", ano=2026, data=date(2026, 5, 1),
                             ementa="Norma não publicada", publicada=False)

    def get(self, qs=""):
        return self.client.get(f"/legislacao/?formato=json&{qs}", HTTP_HOST="camara-a.test").json()

    def test_busca_ignora_acentos_e_plural(self):
        self.assertEqual([n["numero"] for n in self.get("q=ordinaria")], ["2"])
        self.assertEqual([n["numero"] for n in self.get("q=denominacao+ruas")], ["10"])
        self.assertEqual(self.get("q=orçamento"), [])

    def test_filtros_e_nao_publicadas(self):
        self.assertEqual([n["numero"] for n in self.get("tipo=lei")], ["10"])
        self.assertEqual([n["numero"] for n in self.get("ano=2026")], ["2"])

    def test_csv_com_bom_para_excel(self):
        r = self.client.get("/legislacao/?formato=csv", HTTP_HOST="camara-a.test")
        self.assertTrue(r.content.decode("utf-8").startswith("﻿tipo;numero"))
        self.assertIn("attachment", r["Content-Disposition"])

    def test_paginas_publicas_respondem(self):
        for url in ["/", "/vereadores/", "/legislacao/", "/noticias/", "/transparencia/",
                    "/transparencia/contratos/", "/esic/", "/esic/consulta/", "/ouvidoria/", "/ouvidoria/consulta/", "/acessibilidade/", "/privacidade/"]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url, HTTP_HOST="camara-a.test").status_code, 200)
