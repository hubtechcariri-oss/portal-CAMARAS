"""Cria o grupo "Comunicação": quem cuida das imagens e textos do portal.

Basta pôr o usuário da câmara nesse grupo (e como membro da câmara) para ele trocar
brasão, cor, redes sociais, banners, páginas, notícias e fotos dos vereadores.
"""

from django.contrib.auth.management import create_permissions
from django.db import migrations

PERMISSOES = {
    ("conteudo", "banner"): ["view", "add", "change", "delete"],
    ("conteudo", "pagina"): ["view", "add", "change", "delete"],
    ("noticias", "noticia"): ["view", "add", "change", "delete"],
    ("legislativo", "vereador"): ["view", "change"],
    ("camaras", "identidadeportal"): ["view", "change"],
}


def criar(apps, schema_editor):
    # As permissões normalmente só nascem depois do migrate; aqui garantimos que já existam.
    for config in apps.get_app_configs():
        config.models_module = True
        create_permissions(config, verbosity=0)
        config.models_module = None
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    grupo, _ = Group.objects.get_or_create(name="Comunicação")
    for (app, modelo), acoes in PERMISSOES.items():
        codigos = [f"{a}_{modelo}" for a in acoes]
        grupo.permissions.add(*Permission.objects.filter(content_type__app_label=app, codename__in=codigos))


def remover(apps, schema_editor):
    apps.get_model("auth", "Group").objects.filter(name="Comunicação").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("conteudo", "0002_alter_banner_imagem_alter_pagina_imagem"),
        ("camaras", "0003_identidadeportal_alter_camara_brasao"),
        ("legislativo", "0004_alter_materia_arquivo_alter_norma_arquivo_and_more"),
        ("noticias", "0002_alter_noticia_imagem"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]
    operations = [migrations.RunPython(criar, remover)]
