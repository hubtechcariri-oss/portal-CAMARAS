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
        self.assertContains(r, '<span class="indicador__rotulo">e-SIC</span>')
        self.assertContains(r, '<span class="indicador__numero">3</span>', html=False)
        self.assertContains(r, "1 com prazo vencido")
        self.assertContains(r, "Câmara Municipal A")  # nome no cabeçalho
        self.assertContains(r, 'class="selo selo--critico">Crítico<')
        self.assertContains(r, "próximo vence em 2 dias")

    def test_numero_do_cartao_igual_ao_total_da_lista(self):
        u = User.objects.create_user("atendente2", password="x", is_staff=True)
        u.user_permissions.add(*Permission.objects.filter(content_type__app_label="esic"))
        Membro.objects.create(usuario=u, camara=self.a)
        Pedido.objects.filter(camara=self.a, prazo__gt=timezone.localdate() + timedelta(days=10)).update(
            situacao=Pedido.Situacao.RESPONDIDO
        )
        r = self.entrar(u)
        self.assertContains(r, 'href="/admin/esic/pedido/?prazo=abertas"')
        self.assertContains(r, '<span class="indicador__numero">2</span>', html=False)
        lista = self.client.get("/admin/esic/pedido/?prazo=abertas", HTTP_HOST="camara-a.test")
        self.assertEqual(lista.context["cl"].result_count, 2)
        prazos = [p.prazo for p in lista.context["cl"].result_list]
        self.assertEqual(prazos, sorted(prazos))  # mais urgente primeiro

    def test_verde_so_quando_nao_ha_pendencia(self):
        u = User.objects.create_superuser("adm_fila", "a@a.local", "x")
        r = self.entrar(u)
        self.assertContains(r, 'indicador indicador--critico" href="/admin/esic/pedido/')
        Pedido.objects.update(prazo=timezone.localdate() + timedelta(days=30))
        r = self.entrar(u)  # pendente sem urgência: neutro, nunca verde
        self.assertContains(r, 'indicador indicador--neutro" href="/admin/esic/pedido/')
        Pedido.objects.update(situacao=Pedido.Situacao.RESPONDIDO)
        r = self.entrar(u)
        self.assertContains(r, 'indicador indicador--ok" href="/admin/esic/pedido/')
        self.assertContains(r, "nada aguardando resposta")

    def test_comunicacao_ve_atalhos_mas_nao_ve_esic(self):
        u = User.objects.create_user("comunicacao", password="x", is_staff=True)
        u.groups.add(Group.objects.get(name="Comunicação"))
        Membro.objects.create(usuario=u, camara=self.a)
        r = self.entrar(u)
        self.assertNotContains(r, '<span class="indicador__rotulo">e-SIC</span>')
        self.assertNotContains(r, "Prazos e pendências")
        self.assertContains(r, "Nova notícia")
        self.assertContains(r, "Brasão, cores e contatos")
        self.assertNotContains(r, "Nova sessão")


class RotulosTest(TestCase):
    def test_campo_camara_com_acento_e_legenda_de_obrigatorio(self):
        from django.contrib.auth import get_user_model

        from apps.noticias.models import Noticia

        self.assertEqual(Noticia._meta.get_field("camara").verbose_name, "câmara")
        admin = get_user_model().objects.create_superuser("adm_rotulo", "a@a.local", "x-Senha-123")
        self.client.force_login(admin)
        resposta = self.client.get("/admin/noticias/noticia/add/")
        self.assertContains(resposta, "Câmara")
        self.assertContains(resposta, 'class="legenda-obrigatorio"')
        self.assertContains(resposta, 'class="required"')


class InicioDadosReaisTests(TestCase):
    """Indicadores, prazos, publicações e atividade do Início vêm do banco e batem com as listas."""

    def setUp(self):
        from django.contrib.admin.models import ADDITION, LogEntry
        from django.contrib.contenttypes.models import ContentType

        from apps.legislativo.models import Sessao
        from apps.noticias.models import Noticia

        self.a = criar_camara("inicio-a.test", "Câmara Municipal A")
        self.b = criar_camara("inicio-b.test", "Câmara Municipal B")
        agora = timezone.now()
        for camara, dias in [(self.a, 1), (self.a, 10), (self.a, 45), (self.b, 2)]:
            Noticia.objects.create(camara=camara, titulo=f"N {camara.pk} {dias}", slug=f"n-{dias}", corpo="x",
                                   publicada_em=agora - timedelta(days=dias))
        Noticia.objects.create(camara=self.a, titulo="Futura", slug="futura", corpo="x",
                               publicada_em=agora + timedelta(days=3))
        Sessao.objects.create(camara=self.a, numero=7, data_hora=agora + timedelta(days=2))
        Sessao.objects.create(camara=self.b, numero=1, data_hora=agora + timedelta(hours=5))
        p = Pedido.objects.create(camara=self.a, nome="X", email="x@exemplo.com", pedido="Info")
        self.u = User.objects.create_user("editor", password="x", is_staff=True, first_name="Ana")
        self.u.user_permissions.add(*Permission.objects.filter(
            content_type__app_label__in=["esic", "noticias", "legislativo"]))
        Membro.objects.create(usuario=self.u, camara=self.a)
        colega = User.objects.create_user("colega", password="x", is_staff=True, first_name="Bruno")
        Membro.objects.create(usuario=colega, camara=self.a)
        estranho = User.objects.create_user("estranho", password="x", is_staff=True, first_name="Zé")
        Membro.objects.create(usuario=estranho, camara=self.b)
        ct = ContentType.objects.get_for_model(Pedido)
        LogEntry.objects.log_actions(colega.pk, [p], ADDITION, single_object=True)
        LogEntry.objects.create(user=estranho, content_type=ct, object_id="0", object_repr="Outro", action_flag=ADDITION)
        self.client.force_login(self.u)

    def test_indicadores_batem_com_as_listas_e_respeitam_a_camara(self):
        import time

        inicio = time.perf_counter()
        r = self.client.get("/admin/", HTTP_HOST="inicio-a.test")
        self.assertLess(time.perf_counter() - inicio, 1.0)
        html = r.content.decode()
        # Notícias: 2 nos últimos 30 dias (a de 45 dias, a futura e a da outra câmara não contam)
        self.assertIn('href="/admin/noticias/noticia/?ultimos_dias=30"', html)
        lista = self.client.get("/admin/noticias/noticia/?ultimos_dias=30")
        self.assertEqual(lista.context["cl"].result_count, 2)
        self.assertInHTML('<span class="indicador__numero">2</span>', html, count=1)
        self.assertContains(r, "1 agendada")
        # Próxima sessão é a da própria câmara (a da câmara B é mais cedo, mas não aparece)
        self.assertContains(r, "Próxima sessão")
        self.assertContains(r, "em 2 dias")
        # Prazos e pendências, publicado recentemente, atividade
        self.assertContains(r, "Prazos e pendências")
        self.assertContains(r, "Publicado recentemente")
        self.assertContains(r, "N %d 1" % self.a.pk)
        self.assertNotContains(r, "N %d 2" % self.b.pk)
        self.assertContains(r, "<strong>Bruno</strong> adicionou")
        self.assertNotContains(r, "<strong>Zé</strong>")
        # Sem lista "Adicionar/Modificar"
        self.assertNotContains(r, 'class="addlink"')
        self.assertNotContains(r, 'class="changelink"')


class MenuLateralTests(TestCase):
    def setUp(self):
        self.a = criar_camara("menu-a.test", "Câmara Municipal A")
        Pedido.objects.create(camara=self.a, nome="X", email="x@exemplo.com", pedido="Info")
        self.client.force_login(User.objects.create_superuser("adm_menu", "a@a.local", "x"))

    def test_menu_agrupado_em_todas_as_telas_com_item_atual(self):
        from django.contrib import admin

        for url in ["/admin/", "/admin/noticias/noticia/", "/admin/esic/pedido/"]:
            r = self.client.get(url, HTTP_HOST="menu-a.test")
            html = r.content.decode()
            self.assertIn('class="menu-painel"', html, url)
            for grupo in ["Início", "Conteúdo", "Legislativo", "Transparência", "Atendimento", "Configurações"]:
                self.assertIn(f"<span>{grupo}</span>", html, (url, grupo))
            # todas as áreas registradas ficam a um clique, a partir de qualquer tela
            for modelo in admin.site._registry:
                lista = f"/admin/{modelo._meta.app_label}/{modelo._meta.model_name}/"
                self.assertIn(f'href="{lista}"', html, (url, lista))
        self.assertEqual(html.count('aria-current="page"'), 1)
        self.assertRegex(html, r'href="/admin/esic/pedido/" class="is-atual" aria-current="page">\s*<span>e-SIC')
        self.assertContains(r, 'aria-label="1 em aberto"')
        inicio = self.client.get("/admin/", HTTP_HOST="menu-a.test")
        self.assertContains(inicio, 'href="/admin/" aria-current="page"', html=False)

    def test_menu_do_usuario_substitui_boas_vindas(self):
        r = self.client.get("/admin/", HTTP_HOST="menu-a.test")
        self.assertContains(r, 'class="usuario__botao"')
        self.assertContains(r, "Encerrar sessão")
        self.assertNotContains(r, "Bem-vindo(a)")
        # o botão de sair continua sendo um POST com CSRF
        self.assertContains(r, 'id="logout-form" method="post" action="/admin/logout/"')
