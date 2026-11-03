"""Configuração de busca em português que ignora acentos.

Cidadãos digitam "orcamento" e esperam achar "orçamento". A configuração
`portugues` aplica `unaccent` antes do stemmer do português.
Requer a extensão `unaccent` (disponível nos Postgres gerenciados comuns).
"""

from django.contrib.postgres.operations import UnaccentExtension
from django.db import migrations

CRIAR = """
CREATE TEXT SEARCH CONFIGURATION portugues (COPY = portuguese);
ALTER TEXT SEARCH CONFIGURATION portugues
    ALTER MAPPING FOR asciiword, asciihword, hword_asciipart, word, hword, hword_part
    WITH unaccent, portuguese_stem;
"""


class Migration(migrations.Migration):
    dependencies = [("legislativo", "0001_initial")]
    operations = [
        UnaccentExtension(),
        migrations.RunSQL(CRIAR, "DROP TEXT SEARCH CONFIGURATION IF EXISTS portugues;"),
    ]
