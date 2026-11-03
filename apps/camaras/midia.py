"""Mídias públicas (imagens e documentos que aparecem no portal).

- Cada câmara tem a sua pasta: `camara_<id>/<pasta>/<ano>/<nome>`. Isso facilita
  backup, migração ou exclusão dos arquivos de um cliente.
- Limites de tamanho e formatos aceitos ficam aqui, num só lugar.
"""

import os
import uuid

from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.utils import timezone
from django.utils.deconstruct import deconstructible
from django.utils.html import format_html
from django.utils.text import get_valid_filename, slugify

FORMATOS_IMAGEM = ["jpg", "jpeg", "png", "webp", "gif"]
FORMATOS_DOCUMENTO = ["pdf", "doc", "docx", "odt", "xls", "xlsx", "ods", "csv", "txt", "zip"]


@deconstructible
class CaminhoMidia:
    def __init__(self, pasta):
        self.pasta = pasta

    def __call__(self, instancia, nome):
        camara_id = getattr(instancia, "camara_id", None)
        if camara_id is None and instancia._meta.model_name in ("camara", "identidadeportal"):
            camara_id = instancia.pk
        base, ext = os.path.splitext(nome)
        nome = f"{slugify(base)[:60] or 'arquivo'}-{uuid.uuid4().hex[:6]}{ext.lower()}"
        return f"camara_{camara_id or 'nova'}/{self.pasta}/{timezone.now():%Y}/{get_valid_filename(nome)}"

    def __eq__(self, outro):
        return isinstance(outro, CaminhoMidia) and outro.pasta == self.pasta


@deconstructible
class TamanhoMaximo:
    def __init__(self, mb):
        self.mb = mb

    def __call__(self, arquivo):
        if arquivo.size > self.mb * 1024 * 1024:
            raise ValidationError(f"O arquivo tem {arquivo.size / 1024 / 1024:.1f} MB. O máximo é {self.mb} MB.")

    def __eq__(self, outro):
        return isinstance(outro, TamanhoMaximo) and outro.mb == self.mb


VALIDA_IMAGEM = [FileExtensionValidator(FORMATOS_IMAGEM), TamanhoMaximo(5)]
VALIDA_DOCUMENTO = [FileExtensionValidator(FORMATOS_DOCUMENTO), TamanhoMaximo(30)]


def previa(arquivo, altura=48, redonda=False):
    """HTML de miniatura para o painel."""
    if not arquivo:
        return "—"
    raio = "50%" if redonda else "4px"
    return format_html(
        '<a href="{0}" target="_blank" rel="noopener"><img src="{0}" alt="" '
        'style="height:{1}px;max-width:{2}px;object-fit:cover;border-radius:{3};background:#eee"></a>',
        arquivo.url, altura, altura * 4, raio,
    )
