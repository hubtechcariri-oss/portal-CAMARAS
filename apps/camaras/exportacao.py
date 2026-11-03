"""Dados abertos (LAI, art. 8º, § 3º, II e III): toda listagem pode ser baixada em CSV ou JSON."""

import csv
import json
from datetime import date, datetime
from decimal import Decimal

from django.http import HttpResponse, JsonResponse

FORMATOS = ("csv", "json")


def _valor(v):
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    if isinstance(v, Decimal):
        return str(v)
    return v


def formato_pedido(request):
    formato = request.GET.get("formato", "").lower()
    return formato if formato in FORMATOS else None


def exportar(formato, nome_arquivo, campos, linhas):
    """`campos` é uma lista de nomes; `linhas` é um iterável de dicts."""
    linhas = [{c: _valor(linha.get(c)) for c in campos} for linha in linhas]
    if formato == "json":
        resposta = JsonResponse(linhas, safe=False, json_dumps_params={"ensure_ascii": False})
    else:
        resposta = HttpResponse(content_type="text/csv; charset=utf-8")
        resposta.write("﻿")  # BOM para o Excel abrir acentos corretamente
        escritor = csv.DictWriter(resposta, fieldnames=campos, delimiter=";")
        escritor.writeheader()
        escritor.writerows(linhas)
    resposta["Content-Disposition"] = f'attachment; filename="{nome_arquivo}.{formato}"'
    return resposta
