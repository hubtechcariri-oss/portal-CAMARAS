import io
import shutil
import tempfile

from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from apps.camaras.midia import VALIDA_IMAGEM, TamanhoMaximo
from apps.camaras.models import Camara, Membro
from apps.conteudo.models import Banner

from .fabrica import criar_camara

MIDIA = tempfile.mkdtemp()


def png(nome="brasao.png", tamanho=(300, 300)):
    buf = io.BytesIO()
    Image.new("RGB", tamanho, "navy").save(buf, "PNG")
    return SimpleUploadedFile(nome, buf.getvalue(), content_type="image/png")


@override_settings(MEDIA_ROOT=MIDIA)
class IdentidadePortalTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MIDIA, ignore_errors=True)

    def setUp(self):
        self.a = criar_camara("camara-a.test", "Câmara Municipal A")
        self.b = criar_camara("camara-b.test", "Câmara Municipal B")
        self.usuario = User.objects.create_user("comunicacao_a", password="x", is_staff=True)
        self.usuario.groups.add(Group.objects.get(name="Comunicação"))
        Membro.objects.create(usuario=self.usuario, camara=self.a)
        self.client.force_login(self.usuario)

    def test_lista_leva_direto_ao_formulario_da_propria_camara(self):
        r = self.client.get("/admin/camaras/identidadeportal/", HTTP_HOST="camara-a.test")
        self.assertRedirects(r, f"/admin/camaras/identidadeportal/{self.a.pk}/change/", fetch_redirect_response=False)

    def test_nao_acessa_identidade_de_outra_camara(self):
        r = self.client.get(f"/admin/camaras/identidadeportal/{self.b.pk}/change/", HTTP_HOST="camara-a.test")
        self.assertIn(r.status_code, (302, 404))

    def test_nao_gerencia_cadastro_de_camaras(self):
        r = self.client.get("/admin/camaras/camara/", HTTP_HOST="camara-a.test")
        self.assertEqual(r.status_code, 403)

    def test_troca_brasao_e_redes_e_aparece_no_portal(self):
        url = f"/admin/camaras/identidadeportal/{self.a.pk}/change/"
        r = self.client.post(url, {
            "brasao": png(tamanho=(300, 300)), "cor_primaria": "#123456", "instagram": "https://instagram.com/camaraa",
            "facebook": "", "youtube": "", "endereco": "", "telefone": "", "email": "",
            "horario_atendimento": "", "encarregado_lgpd": "", "cnpj": "",
        }, HTTP_HOST="camara-a.test")
        self.assertEqual(r.status_code, 302, getattr(r, "context", None) and r.context["adminform"].form.errors)
        self.a.refresh_from_db()
        self.assertTrue(self.a.brasao.name.startswith(f"camara_{self.a.pk}/identidade/"))
        self.assertEqual((self.a.brasao.width, self.a.brasao.height), (300, 300))  # brasão não é recortado
        pagina = self.client.get("/", HTTP_HOST="camara-a.test")
        self.assertContains(pagina, self.a.brasao.url)
        self.assertContains(pagina, "#123456")
        self.assertContains(pagina, "https://instagram.com/camaraa")

    def test_comunicacao_cadastra_banner(self):
        r = self.client.post("/admin/conteudo/banner/add/", {
            "titulo": "Novo destaque", "imagem": png("destaque.png", (2000, 1500)), "rotulo_link": "Saiba mais", "ordem": 0,
            "inicio_0": "01/01/2026", "inicio_1": "00:00:00", "ativo": "on",
        }, HTTP_HOST="camara-a.test")
        self.assertEqual(r.status_code, 302)
        banner = Banner.objects.get(titulo="Novo destaque")
        self.assertEqual(banner.camara, self.a)
        self.assertTrue(banner.imagem.name.startswith(f"camara_{self.a.pk}/banners/"))
        # Foto 4:3 enviada no lugar do banner: sai recortada no tamanho do layout.
        self.assertEqual((banner.imagem.width, banner.imagem.height), (1600, 500))
        self.assertTrue(banner.imagem.name.endswith(".jpg"))

    def test_recusa_banner_pequeno_com_mensagem_clara(self):
        r = self.client.post("/admin/conteudo/banner/add/", {
            "titulo": "Pequeno", "imagem": png("p.png", (640, 480)), "rotulo_link": "Saiba mais", "ordem": 0,
            "inicio_0": "01/01/2026", "inicio_1": "00:00:00", "ativo": "on",
        }, HTTP_HOST="camara-a.test")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "640 × 480 px e é pequena demais")
        self.assertFalse(Banner.objects.filter(titulo="Pequeno").exists())

    def test_formulario_mostra_tamanho_ideal(self):
        r = self.client.get("/admin/conteudo/banner/add/", HTTP_HOST="camara-a.test")
        self.assertContains(r, "Tamanho ideal: 1600 × 500 px")
        self.assertContains(r, 'accept="image/jpeg,image/png,image/webp"')


class ValidacaoMidiaTests(TestCase):
    def test_recusa_formato_e_tamanho(self):
        texto = SimpleUploadedFile("virus.exe", b"x")
        with self.assertRaises(ValidationError):
            for v in VALIDA_IMAGEM:
                v(texto)
        grande = SimpleUploadedFile("foto.jpg", b"x" * (2 * 1024 * 1024))
        with self.assertRaises(ValidationError):
            TamanhoMaximo(1)(grande)


def foto_ruidosa(nome="foto.jpg", tamanho=(1600, 900)):
    """JPEG com ruído (comprime mal), para testar o limite de peso da miniatura."""
    import os

    img = Image.frombytes("RGB", tamanho, os.urandom(tamanho[0] * tamanho[1] * 3))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=95)
    return SimpleUploadedFile(nome, buf.getvalue(), content_type="image/jpeg")


@override_settings(MEDIA_ROOT=MIDIA)
class ListagensTests(TestCase):
    def setUp(self):
        self.camara = criar_camara("lista.test", "Câmara Municipal Lista")
        self.admin = User.objects.create_superuser("adm_lista", "a@a.local", "x")
        self.client.force_login(self.admin)

    def test_miniatura_leve_na_lista_de_noticias(self):
        from apps.camaras.midia import caminho_miniatura
        from apps.noticias.models import Noticia

        n = Noticia.objects.create(camara=self.camara, titulo="Com foto", slug="com-foto", corpo="x",
                                   imagem=foto_ruidosa())
        r = self.client.get("/admin/noticias/noticia/")
        destino = caminho_miniatura(n.imagem.name)
        self.assertContains(r, destino)
        self.assertTrue(n.imagem.storage.exists(destino))
        self.assertLessEqual(n.imagem.storage.size(destino), 20 * 1024)
        with n.imagem.storage.open(destino) as f:
            self.assertEqual(Image.open(f).size[0], 160)

    def test_selo_publicada_agendada_rascunho(self):
        from datetime import timedelta

        from django.utils import timezone

        from apps.noticias.models import Noticia

        agora = timezone.now()
        Noticia.objects.create(camara=self.camara, titulo="No ar", slug="a", corpo="x")
        Noticia.objects.create(camara=self.camara, titulo="Futura", slug="b", corpo="x",
                               publicada_em=agora + timedelta(days=2))
        Noticia.objects.create(camara=self.camara, titulo="Rascunho", slug="c", corpo="x", publicada=False)
        r = self.client.get("/admin/noticias/noticia/")
        self.assertContains(r, 'class="selo selo--ok">Publicada<')
        self.assertContains(r, 'class="selo selo--atencao">Agendada<')
        self.assertContains(r, 'class="selo selo--neutro">Rascunho<')
        agendadas = self.client.get("/admin/noticias/noticia/?situacao_publicacao=agendada")
        self.assertEqual([n.titulo for n in agendadas.context["cl"].result_list], ["Futura"])
        # URL antiga do filtro booleano continua funcionando
        antigas = self.client.get("/admin/noticias/noticia/?publicada__exact=0")
        self.assertEqual(antigas.status_code, 200)
        self.assertEqual(antigas.context["cl"].result_count, 1)
