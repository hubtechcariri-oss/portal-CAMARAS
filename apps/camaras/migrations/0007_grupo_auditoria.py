"""Cria o grupo "Auditoria": quem pode consultar a trilha de auditoria da câmara.

Indicado para a presidência e o controle interno. Basta pôr o usuário nesse grupo (e como membro da câmara).
"""

from django.contrib.auth.management import create_permissions
from django.db import migrations


def criar(apps, schema_editor):
    for config in apps.get_app_configs():
        config.models_module = True
        create_permissions(config, verbosity=0)
        config.models_module = None
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    grupo, _ = Group.objects.get_or_create(name="Auditoria")
    grupo.permissions.add(*Permission.objects.filter(content_type__app_label="camaras",
                                                     codename="view_registroauditoria"))


def remover(apps, schema_editor):
    apps.get_model("auth", "Group").objects.filter(name="Auditoria").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("camaras", "0006_trilha_auditoria"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [migrations.RunPython(criar, remover)]
