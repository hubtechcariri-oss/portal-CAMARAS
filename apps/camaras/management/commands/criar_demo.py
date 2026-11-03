"""Cria uma câmara fictícia com dados de exemplo para demonstração e desenvolvimento."""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.camaras.models import Camara, Dominio
from apps.conteudo.models import Banner, Pagina

from apps.legislativo.models import Legislatura, Materia, Norma, Sessao, Tramitacao, Vereador
from apps.noticias.models import Noticia
from apps.transparencia.models import CategoriaTransparencia, Documento

from . import _imagens_demo as img

PAGINAS = [
    ("sobre-a-camara", "Sobre a Câmara", "institucional", 0,
     "Conheça a história e as atribuições do Poder Legislativo municipal.",
     "A Câmara Municipal é o órgão do Poder Legislativo do município. Ela é composta por vereadores "
     "eleitos pelo voto direto para mandatos de quatro anos.\n\n"
     "Cabe à Câmara elaborar as leis municipais, fiscalizar o Poder Executivo, julgar as contas do prefeito "
     "e representar a população nas decisões sobre os rumos da cidade.\n\n"
     "Este texto é um exemplo. Cada câmara edita o seu no painel, em Conteúdo › Páginas."),
    ("papel-do-vereador", "Papel do vereador", "institucional", 1,
     "O que faz um vereador e como acompanhar o trabalho do seu representante.",
     "O vereador apresenta projetos de lei, requerimentos, indicações e moções, participa das sessões "
     "e das comissões e fiscaliza a aplicação dos recursos públicos.\n\n"
     "Você pode acompanhar a produção de cada vereador na página de matérias legislativas, filtrando pelo autor."),
    ("comissoes-permanentes", "Comissões permanentes", "legislativo", 0,
     "Colegiados que analisam as matérias antes da votação em plenário.",
     "Comissão de Constituição, Justiça e Redação.\n\nComissão de Finanças e Orçamento.\n\n"
     "Comissão de Educação, Saúde e Assistência Social.\n\n"
     "Texto de exemplo: edite a composição de cada comissão no painel."),
]

BANNERS = [
    ("Acompanhe as sessões ao vivo", "As sessões ordinárias acontecem às terças-feiras, às 9h, com transmissão pela internet.",
     "/sessoes/", "Ver sessões", (11, 79, 138), (20, 32, 46),
     "Ilustração da fachada de um prédio legislativo com colunas, em tons de azul."),
    ("Transparência ao alcance de todos", "Receitas, despesas, licitações, contratos e diárias em um só lugar.",
     "/transparencia/", "Acessar a transparência", (31, 122, 76), (16, 60, 52),
     "Ilustração abstrata em tons de verde com a fachada de um prédio público."),
    ("Sua opinião faz diferença", "Registre reclamações, denúncias, sugestões e elogios na Ouvidoria.",
     "/ouvidoria/", "Falar com a Ouvidoria", (142, 68, 173), (44, 30, 80),
     "Ilustração abstrata em tons de roxo com a fachada de um prédio público."),
]

NOTICIAS = [
    ("Câmara aprova o orçamento de 2027", "orcamento-2027", "Projeto foi aprovado em segunda votação.",
     "A Câmara aprovou nesta terça-feira o projeto de lei orçamentária.", (11, 79, 138), (20, 32, 46)),
    ("Escolas municipais terão coleta seletiva", "coleta-seletiva-escolas",
     "Projeto de lei aprovado por unanimidade cria programa nas escolas da rede municipal.",
     "O plenário aprovou o projeto que institui a coleta seletiva nas escolas municipais.", (31, 122, 76), (16, 60, 52)),
    ("Audiência pública debate o transporte escolar", "audiencia-transporte-escolar",
     "Pais, estudantes e a Secretaria de Educação participaram do encontro.",
     "A audiência pública reuniu a comunidade para discutir rotas e horários do transporte escolar.",
     (211, 84, 0), (90, 36, 20)),
]


class Command(BaseCommand):
    help = "Cria a Câmara Municipal de Demonstração respondendo no domínio informado."

    def add_arguments(self, parser):
        parser.add_argument(
            "--host", action="append", dest="hosts",
            help="Domínio da câmara de demonstração. Pode repetir. Padrão: localhost.",
        )

    def handle(self, *args, hosts, **opcoes):
        hosts = [h.strip().lower() for h in (hosts or ["localhost"]) if h and h.strip()]
        existente = Dominio.objects.filter(host__in=hosts).select_related("camara").first()
        if existente:
            # Garante que todos os domínios pedidos apontem para a câmara já criada.
            for h in hosts:
                Dominio.objects.get_or_create(host=h, defaults={"camara": existente.camara})
            self.garantir_visual(existente.camara)
            self.garantir_atendimento(existente.camara)
            self.garantir_transparencia(existente.camara)
            self.stdout.write(f"A câmara de demonstração já existe ({', '.join(hosts)}). Visual conferido.")
            return
        host = hosts[0]
        camara = Camara.objects.create(
            nome="Câmara Municipal de Demonstração", municipio="Demonstração", uf="CE",
            cnpj="00.000.000/0001-00", endereco="Rua Principal, 100, Centro",
            telefone="(88) 0000-0000", email="contato@exemplo.leg.br",
            horario_atendimento="segunda a sexta, das 8h às 14h",
            encarregado_lgpd="Encarregado de Dados, encarregado@exemplo.leg.br",
        )
        for i, h in enumerate(hosts):
            Dominio.objects.create(camara=camara, host=h, principal=(i == 0))
        vereadores = []
        leg = Legislatura.objects.create(camara=camara, numero=20, inicio=date(2025, 1, 1), fim=date(2028, 12, 31))
        for nome, partido, cargo in [
            ("Ana Souza", "Partido A", "Presidente"), ("Bruno Lima", "Partido B", "Vice-Presidente"),
            ("Carla Dias", "Partido C", "1ª Secretária"), ("Diego Alves", "Partido A", ""),
            ("Elisa Rocha", "Partido D", ""),
        ]:
            v = Vereador.objects.create(camara=camara, nome_parlamentar=nome, partido=partido, cargo_mesa=cargo)
            v.legislaturas.add(leg)
            vereadores.append(v)
        sessao = Sessao.objects.create(camara=camara, numero=32, legislatura=leg,
                                       data_hora=datetime(2026, 10, 7, 9, tzinfo=ZoneInfo("America/Sao_Paulo")),
                                       video_url="https://www.youtube.com/")
        sessao.presentes.set(vereadores[:4])
        pl = Materia.objects.create(camara=camara, tipo="pl", numero=45, ano=2026, data_apresentacao=date(2026, 9, 1),
                                    ementa="Institui o programa de coleta seletiva nas escolas municipais.",
                                    situacao=Materia.Situacao.APROVADA)
        pl.autores.set(vereadores[2:4])
        Tramitacao.objects.create(materia=pl, data=date(2026, 9, 2), descricao="Lida em plenário e encaminhada à CCJ")
        Tramitacao.objects.create(materia=pl, data=date(2026, 10, 7), descricao="Votação em turno único",
                                  sessao=sessao, resultado="aprov", votos_sim=4, votos_nao=0, abstencoes=0)
        Materia.objects.create(camara=camara, tipo="req", numero=12, ano=2026, data_apresentacao=date(2026, 10, 1),
                               ementa="Requer ao Poder Executivo informações sobre o transporte escolar.",
                               autor_externo="Mesa Diretora")
        Norma.objects.create(camara=camara, tipo="lei", numero="1.234", ano=2026, data=date(2026, 3, 10),
                             ementa="Dispõe sobre a denominação de logradouros públicos no bairro Centro.")
        Norma.objects.create(camara=camara, tipo="res", numero="15", ano=2026, data=date(2026, 6, 2),
                             ementa="Altera o Regimento Interno quanto às sessões ordinárias.")
        Documento.objects.create(camara=camara, categoria=CategoriaTransparencia.objects.get(slug="diarias"),
                                 titulo="Diária: viagem à capital para capacitação", data=date(2026, 9, 15),
                                 competencia="09/2026", valor="350.00", descricao="Beneficiário: Bruno Lima.")
        Documento.objects.create(camara=camara, categoria=CategoriaTransparencia.objects.get(slug="despesas"),
                                 titulo="Consulta de despesas no sistema contábil", data=date(2026, 1, 1),
                                 link_externo="https://exemplo.com/despesas")
        self.garantir_visual(camara)
        self.garantir_atendimento(camara)
        self.garantir_transparencia(camara)
        self.stdout.write(self.style.SUCCESS(f"Câmara de demonstração criada em: {', '.join(hosts)}"))

    def garantir_visual(self, camara):
        """Completa brasão, redes, banners, páginas, fotos e notícias que estiverem faltando.

        Idempotente: só preenche o que está vazio, sem sobrescrever o que a câmara já editou.
        """
        if not camara.brasao:
            camara.brasao.save("brasao.png", img.brasao(), save=False)
        for campo, url in [("facebook", "https://www.facebook.com/"), ("instagram", "https://www.instagram.com/"),
                           ("youtube", "https://www.youtube.com/")]:
            if not getattr(camara, campo):
                setattr(camara, campo, url)
        camara.save()

        if not Banner.objects.da_camara(camara).exists():
            for ordem, (titulo, sub, link, rotulo, c1, c2, alt) in enumerate(BANNERS):
                b = Banner(camara=camara, titulo=titulo, subtitulo=sub, link=link, rotulo_link=rotulo,
                           ordem=ordem, texto_alternativo=alt)
                b.imagem.save(f"banner-{ordem + 1}.jpg", img.banner(ordem, c1, c2, f"banner-{ordem + 1}.jpg"), save=False)
                b.save()

        for slug, titulo, menu, ordem, resumo, corpo in PAGINAS:
            Pagina.objects.get_or_create(camara=camara, slug=slug, defaults={
                "titulo": titulo, "menu": menu, "ordem": ordem, "resumo": resumo, "corpo": corpo})

        for i, v in enumerate(Vereador.objects.da_camara(camara).order_by("pk")):
            if not v.foto:
                v.foto.save(f"vereador-{v.pk}.jpg", img.foto_vereador(i, f"vereador-{v.pk}.jpg"))

        for i, (titulo, slug, resumo, corpo, c1, c2) in enumerate(NOTICIAS):
            n, _ = Noticia.objects.get_or_create(camara=camara, slug=slug, defaults={
                "titulo": titulo, "resumo": resumo, "corpo": corpo,
                "publicada_em": timezone.now() - timedelta(days=i * 3)})
            if not n.imagem:
                n.texto_alternativo = n.texto_alternativo or "Ilustração abstrata com gráfico de barras."
                n.imagem.save(f"{slug}.jpg", img.imagem_noticia(i, c1, c2, f"{slug}.jpg"))


    def garantir_atendimento(self, camara):
        """Pedidos e manifestações de exemplo, para o painel mostrar pendências e prazos."""
        from apps.esic.models import Pedido
        from apps.ouvidoria.models import Manifestacao

        hoje = timezone.localdate()
        if not Pedido.objects.da_camara(camara).exists():
            for texto, dias_restantes in [
                ("Solicito a relação de contratos de locação de veículos vigentes em 2026.", -2),
                ("Peço cópia da ata da 30ª sessão ordinária.", 3),
                ("Quais foram as despesas com diárias no primeiro semestre?", 15),
            ]:
                p = Pedido.objects.create(camara=camara, nome="Cidadão de exemplo", email="cidadao@exemplo.com",
                                          pedido=texto)
                Pedido.objects.filter(pk=p.pk).update(prazo=hoje + timedelta(days=dias_restantes))
        if not Manifestacao.objects.da_camara(camara).exists():
            for tipo, assunto, dias_restantes in [
                ("reclamacao", "Iluminação da praça em frente à Câmara", 20),
                ("sugestao", "Transmitir as sessões também pelo rádio", 4),
            ]:
                m = Manifestacao.objects.create(camara=camara, tipo=tipo, assunto=assunto,
                                                descricao="Manifestação de exemplo.", anonima=True)
                Manifestacao.objects.filter(pk=m.pk).update(prazo=hoje + timedelta(days=dias_restantes))
        self.garantir_historico_atendimento(camara)

    def garantir_historico_atendimento(self, camara):
        """Pedidos e manifestações já respondidos nos últimos meses, para o dashboard ter histórico."""
        import random

        from apps.esic.models import Pedido
        from apps.ouvidoria.models import Manifestacao

        sorteio = random.Random(camara.pk)  # sempre os mesmos números para a mesma câmara
        agora = timezone.now()
        filas = [
            (Pedido, "respondido_em", Pedido.Situacao.RESPONDIDO, 20,
             lambda: {"nome": "Cidadão de exemplo", "email": "cidadao@exemplo.com",
                      "pedido": "Pedido de exemplo já respondido."}),
            (Manifestacao, "respondida_em", Manifestacao.Situacao.RESPONDIDA, 30,
             lambda: {"tipo": "solicitacao", "assunto": "Manifestação de exemplo já respondida",
                      "descricao": "Manifestação de exemplo.", "anonima": True}),
        ]
        for modelo, campo, respondida, prazo_dias, dados in filas:
            if modelo.objects.da_camara(camara).filter(**{f"{campo}__isnull": False}).exists():
                continue
            for meses_atras in range(11, 0, -1):
                for _ in range(sorteio.randint(1, 5)):
                    criado = agora - timedelta(days=meses_atras * 30 + sorteio.randint(0, 25))
                    demora = sorteio.choice([3, 5, 8, 10, 12, 15, 18, prazo_dias + 4])  # às vezes atrasa
                    obj = modelo.objects.create(camara=camara, **dados())
                    modelo.objects.filter(pk=obj.pk).update(
                        criado_em=criado, prazo=(criado + timedelta(days=prazo_dias)).date(),
                        situacao=respondida, **{campo: criado + timedelta(days=demora)})

    def garantir_transparencia(self, camara):
        """Publicações de exemplo para o bloco de transparência do Início ter itens em dia e pendentes.

        Se ninguém marcou as categorias obrigatórias, marca as que têm base legal no catálogo
        (só para a demonstração; em produção quem marca é a equipe, conforme a matriz PNTP).
        """
        if not CategoriaTransparencia.objects.filter(obrigatoria=True).exists():
            CategoriaTransparencia.objects.exclude(base_legal="").update(obrigatoria=True)
        hoje = timezone.localdate()
        exemplos = [
            ("carta-de-servicos-ao-usuario", "Carta de Serviços ao Usuário 2026", 120),
            ("receitas", "Receitas: consulta no sistema contábil", 20),
            ("relatorio-de-gestao-fiscal-rgf", "RGF do 2º quadrimestre de 2026", 40),
            ("contratos", "Contrato nº 12/2026: manutenção predial", 60),
            ("licitacoes", "Pregão eletrônico nº 3/2026", 90),
            ("quadro-de-pessoal-e-remuneracao", "Folha de pagamento de setembro de 2026", 35),
            ("estrutura-organizacional-e-competencias", "Organograma e competências", 500),  # desatualizado
        ]
        for slug, titulo, dias in exemplos:
            categoria = CategoriaTransparencia.objects.filter(slug=slug).first()
            if categoria and not Documento.objects.da_camara(camara).filter(categoria=categoria).exists():
                Documento.objects.create(camara=camara, categoria=categoria, titulo=titulo,
                                         data=hoje - timedelta(days=dias), descricao="Documento de exemplo.")
