"""Cria uma câmara fictícia com dados de exemplo para demonstração e desenvolvimento."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from django.core.management.base import BaseCommand

from apps.camaras.models import Camara, Dominio

from apps.legislativo.models import Legislatura, Materia, Norma, Sessao, Tramitacao, Vereador
from apps.noticias.models import Noticia
from apps.transparencia.models import CategoriaTransparencia, Documento


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
            self.stdout.write(f"A câmara de demonstração já existe ({', '.join(hosts)}).")
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
        Noticia.objects.create(camara=camara, titulo="Câmara aprova o orçamento de 2027", slug="orcamento-2027",
                               resumo="Projeto foi aprovado em segunda votação.",
                               corpo="A Câmara aprovou nesta terça-feira o projeto de lei orçamentária.")
        Documento.objects.create(camara=camara, categoria=CategoriaTransparencia.objects.get(slug="diarias"),
                                 titulo="Diária: viagem à capital para capacitação", data=date(2026, 9, 15),
                                 competencia="09/2026", valor="350.00", descricao="Beneficiário: Bruno Lima.")
        Documento.objects.create(camara=camara, categoria=CategoriaTransparencia.objects.get(slug="despesas"),
                                 titulo="Consulta de despesas no sistema contábil", data=date(2026, 1, 1),
                                 link_externo="https://exemplo.com/despesas")
        self.stdout.write(self.style.SUCCESS(f"Câmara de demonstração criada em: {', '.join(hosts)}"))
