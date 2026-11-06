"""Configuração de busca em português que ignora acentos.

Cidadãos digitam "orcamento" e esperam achar "orçamento". A configuração
`portugues` aplica `unaccent` antes do stemmer do português.
Requer a extensão `unaccent` (disponível nos Postgres gerenciados comuns).
"""

from django.db import migrations

CRIAR = """
CREATE TEXT SEARCH CONFIGURATION portugues (COPY = portuguese);
ALTER TEXT SEARCH CONFIGURATION portugues
    ALTER MAPPING FOR asciiword, asciihword, hword_asciipart, word, hword, hword_part
    WITH unaccent, portuguese_stem;
"""


def criar(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":  # no MySQL a busca é por trecho (ver views.busca_textual)
        schema_editor.execute("CREATE EXTENSION IF NOT EXISTS unaccent;")
        schema_editor.execute(CRIAR)


def remover(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute("DROP TEXT SEARCH CONFIGURATION IF EXISTS portugues;")


class Migration(migrations.Migration):
    dependencies = [("legislativo", "0001_initial")]
    operations = [
        migrations.RunPython(criar, remover),
    ]
