"""Protocolos sequenciais por câmara e por ano (ex.: 202600001), usados pelo e-SIC e pela Ouvidoria."""

import secrets

from django.db import transaction
from django.utils import timezone


def codigo_consulta():
    """Código secreto entregue ao cidadão para acompanhar a solicitação."""
    return secrets.token_hex(4).upper()


def salvar_com_protocolo(instancia, salvar):
    """Gera `instancia.protocolo` com trava na câmara (evita colisão) e chama `salvar()`."""
    from apps.camaras.models import Camara

    ano = str(timezone.localdate().year)
    modelo = type(instancia)
    with transaction.atomic():
        Camara.objects.select_for_update().get(pk=instancia.camara_id)
        ultimo = (
            modelo.objects.filter(camara_id=instancia.camara_id, protocolo__startswith=ano)
            .order_by("-protocolo")
            .values_list("protocolo", flat=True)
            .first()
        )
        seq = int(ultimo[4:]) + 1 if ultimo else 1
        instancia.protocolo = f"{ano}{seq:05d}"
        return salvar()
