"""Anexos do e-SIC e da Ouvidoria: privados, validados e entregues só a quem tem direito."""

import shutil
import tempfile

from django.contrib.auth.models import Permission, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from apps.camaras.anexos import armazenamento_privado
from apps.camaras.models import Membro
from apps.esic.models import Pedido
from apps.ouvidoria.models import Manifestacao

from .fabrica import criar_camara

PDF = b"%PDF-1.4 conteudo de teste"


def pdf(nome="documento.pdf", conteudo=PDF):
    return SimpleUploadedFile(nome, conteudo, content_type="application/pdf")


class AnexosTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.pasta = tempfile.mkdtemp()
        cls.override = override_settings(ANEXOS_ROOT=cls.pasta)
        cls.override.enable()
        armazenamento_privado.__init__()  # relê ANEXOS_ROOT

    @classmethod
    def tearDownClass(cls):
        cls.override.disable()
        armazenamento_privado.__init__()
        shutil.rmtree(cls.pasta, ignore_errors=True)
        super().tearDownClass()

    @classmethod
    def setUpTestData(cls):
        cls.a = criar_camara("camara-a.test")
        cls.b = criar_camara("camara-b.test", "Câmara Municipal B")

    def enviar_esic(self, arquivo):
        dados = {"nome": "Maria", "email": "m@x.com", "pedido": "Folha", "ciente_privacidade": "on", "anexo": arquivo}
        return self.client.post("/esic/", dados, HTTP_HOST="camara-a.test", follow=True)

    def test_cidadao_anexa_no_esic_e_baixa_com_protocolo_e_codigo(self):
        self.enviar_esic(pdf())
        p = Pedido.objects.get()
        self.assertTrue(p.anexo.name.startswith(f"camara_{self.a.pk}/esic/"))
        self.assertTrue(p.anexo.name.endswith("_documento.pdf"))
        url = f"/esic/consulta/anexo/?protocolo={p.protocolo}&codigo={p.codigo_consulta}"
        r = self.client.get(url, HTTP_HOST="camara-a.test")
        self.assertEqual(b"".join(r.streaming_content), PDF)
        self.assertIn('attachment; filename="documento.pdf"', r["Content-Disposition"])
        # Código errado ou domínio de outra câmara: nada.
        self.assertEqual(self.client.get(url.replace(p.codigo_consulta, "ERRADO"), HTTP_HOST="camara-a.test").status_code, 404)
        self.assertEqual(self.client.get(url, HTTP_HOST="camara-b.test").status_code, 404)

    def test_extensao_e_tamanho_invalidos_sao_recusados(self):
        r = self.enviar_esic(SimpleUploadedFile("virus.exe", b"MZ", content_type="application/octet-stream"))
        self.assertContains(r, "extensão")
        with self.settings(ANEXOS_TAMANHO_MAXIMO_MB=0):
            r = self.enviar_esic(pdf())
        self.assertContains(r, "passa de 0 MB")
        self.assertFalse(Pedido.objects.exists())

    def test_ouvidoria_anonima_com_anexo(self):
        dados = {"tipo": "denuncia", "assunto": "Obra", "descricao": "Foto anexa", "anonima": "on",
                 "ciente_privacidade": "on", "anexo": SimpleUploadedFile("foto.jpg", b"\xff\xd8jpg", "image/jpeg")}
        self.client.post("/ouvidoria/", dados, HTTP_HOST="camara-a.test")
        m = Manifestacao.objects.get()
        url = f"/ouvidoria/consulta/anexo/?protocolo={m.protocolo}&codigo={m.codigo_consulta}"
        self.assertEqual(self.client.get(url, HTTP_HOST="camara-a.test").status_code, 200)

    def test_anexo_nao_fica_na_pasta_publica(self):
        self.enviar_esic(pdf())
        p = Pedido.objects.get()
        self.assertEqual(self.client.get(f"/media/{p.anexo.name}", HTTP_HOST="camara-a.test").status_code, 404)
        self.assertEqual(self.client.get(p.anexo.url, HTTP_HOST="camara-a.test").status_code, 302)  # pede login

    def test_atendente_responde_com_anexo_e_so_ve_a_propria_camara(self):
        self.enviar_esic(pdf())
        p = Pedido.objects.get()
        outro = Pedido.objects.create(camara=self.b, nome="x", email="x@x.com", pedido="x",
                                      anexo=pdf("da_b.pdf"))
        atendente = User.objects.create_user("atendente", password="x", is_staff=True)
        atendente.user_permissions.set(Permission.objects.filter(content_type__app_label="esic"))
        Membro.objects.create(usuario=atendente, camara=self.a)
        self.client.force_login(atendente)

        r = self.client.post(f"/admin/esic/pedido/{p.pk}/change/", {
            "nome": p.nome, "email": p.email, "pedido": p.pedido, "situacao": "respondido",
            "resposta": "Segue a folha.", "anexo_resposta": pdf("folha_outubro.pdf"),
        }, HTTP_HOST="painel.test")
        self.assertEqual(r.status_code, 302)
        p.refresh_from_db()
        self.assertTrue(p.anexo_resposta.name.endswith("_folha_outubro.pdf"))
        self.assertEqual(p.anexo.name.endswith("_documento.pdf"), True)  # anexo do cidadão não muda

        self.assertEqual(self.client.get(p.anexo_resposta.url, HTTP_HOST="painel.test").status_code, 200)
        self.assertEqual(self.client.get(outro.anexo.url, HTTP_HOST="painel.test").status_code, 404)
        self.assertEqual(self.client.get("/anexos/camara_1/../../etc/passwd", HTTP_HOST="painel.test").status_code, 404)

        # O cidadão vê a resposta e o anexo da resposta na consulta.
        self.client.logout()
        consulta = f"/esic/consulta/?protocolo={p.protocolo}&codigo={p.codigo_consulta}"
        r = self.client.get(consulta, HTTP_HOST="camara-a.test")
        self.assertContains(r, "Arquivo da resposta")
        r = self.client.get(f"/esic/consulta/anexo_resposta/?protocolo={p.protocolo}&codigo={p.codigo_consulta}",
                            HTTP_HOST="camara-a.test")
        self.assertEqual(r.status_code, 200)
