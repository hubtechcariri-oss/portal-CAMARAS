"""Anexos privados (e-SIC e Ouvidoria).

- Ficam em ANEXOS_ROOT, fora da pasta pública de mídia.
- O caminho começa por `camara_<id>/`, o que permite checar a câmara no download.
- O nome do arquivo ganha um prefixo aleatório, para não ser adivinhado.
- Download só por views que checam permissão (equipe da câmara ou cidadão com protocolo + código).
"""

import mimetypes
import os
import re
import uuid

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import ValidationError
from django.core.files.storage import FileSystemStorage
from django.core.validators import FileExtensionValidator
from django.http import FileResponse, Http404
from django.utils.deconstruct import deconstructible
from django.utils.text import get_valid_filename

from .admin_mixins import camaras_do_usuario


class ArmazenamentoPrivado(FileSystemStorage):
    def __init__(self, **kwargs):
        super().__init__(location=settings.ANEXOS_ROOT, base_url="/anexos/", **kwargs)


armazenamento_privado = ArmazenamentoPrivado()


def obter_armazenamento():
    """Usado como `storage=` dos FileFields (callable, para a migração não gravar o caminho do disco)."""
    return armazenamento_privado


@deconstructible
class CaminhoAnexo:
    """upload_to: camara_<id>/<pasta>/<ano>/<aleatório>_<nome original>."""

    def __init__(self, pasta):
        self.pasta = pasta

    def __call__(self, instancia, nome):
        from django.utils import timezone

        nome = get_valid_filename(os.path.basename(nome))[-80:]
        return f"camara_{instancia.camara_id}/{self.pasta}/{timezone.now().year}/{uuid.uuid4().hex[:12]}_{nome}"

    def __eq__(self, outro):
        return isinstance(outro, CaminhoAnexo) and outro.pasta == self.pasta


def validar_tamanho(arquivo):
    limite = settings.ANEXOS_TAMANHO_MAXIMO_MB * 1024 * 1024
    if arquivo.size > limite:
        raise ValidationError(f"O arquivo passa de {settings.ANEXOS_TAMANHO_MAXIMO_MB} MB.")


VALIDADORES = [FileExtensionValidator(allowed_extensions=settings.ANEXOS_EXTENSOES), validar_tamanho]
DICA = (
    f"Opcional. Até {settings.ANEXOS_TAMANHO_MAXIMO_MB} MB. "
    f"Formatos: {', '.join(e.upper() for e in settings.ANEXOS_EXTENSOES)}."
)


def resposta_arquivo(campo_arquivo):
    """Entrega o arquivo como download, sem que o navegador tente executá-lo."""
    if not campo_arquivo or not campo_arquivo.storage.exists(campo_arquivo.name):
        raise Http404("Anexo não encontrado.")
    tipo = mimetypes.guess_type(campo_arquivo.name)[0] or "application/octet-stream"
    nome = os.path.basename(campo_arquivo.name).split("_", 1)[-1]
    resposta = FileResponse(campo_arquivo.open("rb"), as_attachment=True, filename=nome, content_type=tipo)
    resposta["X-Content-Type-Options"] = "nosniff"
    return resposta


CAMINHO_VALIDO = re.compile(r"^camara_(\d+)/[\w\-./]+$")


@staff_member_required
def baixar_anexo_equipe(request, caminho):
    """Download pelo painel: só para a equipe da câmara dona do anexo."""
    m = CAMINHO_VALIDO.match(caminho)
    if not m or ".." in caminho:
        raise Http404
    if not camaras_do_usuario(request.user).filter(pk=int(m.group(1))).exists():
        raise Http404
    return resposta_arquivo(_Arquivo(caminho))


class _Arquivo:
    """Adaptador mínimo para reutilizar resposta_arquivo com um caminho."""

    def __init__(self, nome):
        self.name = nome
        self.storage = armazenamento_privado

    def __bool__(self):
        return True

    def open(self, modo="rb"):
        return self.storage.open(self.name, modo)
