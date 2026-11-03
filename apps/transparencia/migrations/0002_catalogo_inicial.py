"""Catálogo inicial do menu de transparência.

Estrutura baseada nos itens que portais de câmaras costumam publicar (LAI, LRF,
Lei 14.133). O campo `obrigatoria` fica desligado de propósito: marque-o no
admin conforme a matriz PNTP vigente e as exigências do Tribunal de Contas do
estado. A matriz muda todo ano.
"""

from django.db import migrations
from django.utils.text import slugify

CATALOGO = [
    ("Atendimento ao cidadão", [
        ("Carta de Serviços ao Usuário", "Lei 13.460/2017, art. 7º"),
        ("Perguntas frequentes", "Lei 12.527/2011, art. 8º, § 1º, VI"),
        ("Relatório estatístico do e-SIC", "Lei 12.527/2011, art. 30, III"),
    ]),
    ("Institucional", [
        ("Estrutura organizacional e competências", "Lei 12.527/2011, art. 8º, § 1º, I"),
        ("Regulamentação da LAI", ""),
        ("Regulamentação da LGPD", "Lei 13.709/2018"),
        ("Plano estratégico", ""),
    ]),
    ("Execução orçamentária e financeira", [
        ("Receitas", "LC 101/2000, art. 48-A, II"),
        ("Despesas", "LC 101/2000, art. 48-A, I"),
        ("Ordem cronológica de pagamentos", "Lei 14.133/2021, art. 141"),
        ("Repasses do duodécimo", ""),
    ]),
    ("Gestão fiscal e prestação de contas", [
        ("Relatório de Gestão Fiscal (RGF)", "LC 101/2000, arts. 48, 54 e 55"),
        ("Prestação de Contas de Gestão", ""),
        ("Pareceres e julgamentos do Tribunal de Contas", ""),
    ]),
    ("Pessoal", [
        ("Quadro de pessoal e remuneração", "Lei 12.527/2011, art. 8º"),
        ("Terceirizados", ""),
        ("Estagiários", ""),
        ("Concursos e seleções", ""),
        ("Diárias", ""),
        ("Tabela de valores de diárias", ""),
        ("Cotas para exercício da atividade parlamentar", ""),
    ]),
    ("Licitações e contratos", [
        ("Plano de Contratações Anual (PCA)", "Lei 14.133/2021, art. 12, VII"),
        ("Licitações", "Lei 14.133/2021, art. 174"),
        ("Dispensas e inexigibilidades", "Lei 14.133/2021, art. 72"),
        ("Contratos", "Lei 14.133/2021, art. 94"),
        ("Atas de registro de preços", ""),
        ("Convênios e acordos", ""),
        ("Obras", ""),
        ("Veículos", ""),
    ]),
    ("Atos administrativos", [
        ("Portarias", ""),
        ("Atos da Mesa", ""),
        ("Publicações oficiais", ""),
    ]),
]


def criar(apps, schema_editor):
    Grupo = apps.get_model("transparencia", "GrupoTransparencia")
    Categoria = apps.get_model("transparencia", "CategoriaTransparencia")
    for ordem_grupo, (nome_grupo, categorias) in enumerate(CATALOGO):
        grupo = Grupo.objects.create(nome=nome_grupo, ordem=ordem_grupo)
        for ordem, (nome, base_legal) in enumerate(categorias):
            Categoria.objects.create(
                grupo=grupo, nome=nome, slug=slugify(nome)[:120], base_legal=base_legal, ordem=ordem
            )


def remover(apps, schema_editor):
    apps.get_model("transparencia", "CategoriaTransparencia").objects.all().delete()
    apps.get_model("transparencia", "GrupoTransparencia").objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [("transparencia", "0001_initial")]
    operations = [migrations.RunPython(criar, remover)]
