"""Mídias públicas (imagens e documentos que aparecem no portal).

- Cada câmara tem a sua pasta: `camara_<id>/<pasta>/<ano>/<nome>`. Isso facilita
  backup, migração ou exclusão dos arquivos de um cliente.
- Limites de tamanho e formatos aceitos ficam aqui, num só lugar.
"""

import io
import os
import uuid
from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.images import get_image_dimensions
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone
from django.utils.deconstruct import deconstructible
from django.utils.html import format_html
from django.utils.text import get_valid_filename, slugify
from PIL import Image, ImageOps

FORMATOS_IMAGEM = ["jpg", "jpeg", "png", "webp"]
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


# ---------------------------------------------------------------------------
# Imagens padronizadas: cada lugar do layout tem um tamanho fixo.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Formato:
    largura: int
    altura: int
    min_largura: int
    min_altura: int
    recortar: bool = True  # False: só reduz, mantendo a imagem inteira (ex.: brasão)
    descricao: str = ""

    def ajuda(self):
        if self.recortar:
            texto = (f"Tamanho ideal: {self.largura} × {self.altura} px ({self.descricao}). "
                     f"Mínimo: {self.min_largura} × {self.min_altura} px. "
                     "Se a proporção for diferente, a imagem é recortada pelo centro e reduzida automaticamente.")
        else:
            texto = (f"Tamanho ideal: {self.largura} × {self.altura} px ({self.descricao}). "
                     f"Mínimo: {self.min_largura} × {self.min_altura} px. Imagens maiores são reduzidas automaticamente.")
        return f"{texto} JPG, PNG ou WebP até 5 MB."


FORMATOS = {
    "banner": Formato(1600, 500, 1200, 375, descricao="horizontal, proporção 16:5"),
    "noticia": Formato(1200, 675, 800, 450, descricao="horizontal, proporção 16:9"),
    "pagina": Formato(1200, 675, 800, 450, descricao="horizontal, proporção 16:9"),
    "vereador": Formato(600, 600, 300, 300, descricao="quadrada, rosto centralizado"),
    "brasao": Formato(512, 512, 128, 128, recortar=False,
                      descricao="quadrado, PNG com fundo transparente"),
}


@deconstructible
class DimensaoMinima:
    def __init__(self, formato):
        self.formato = formato

    def __call__(self, arquivo):
        f = FORMATOS[self.formato]
        largura, altura = get_image_dimensions(arquivo)
        if largura is None:
            raise ValidationError("Não foi possível ler a imagem. Envie um arquivo JPG, PNG ou WebP válido.")
        if largura < f.min_largura or altura < f.min_altura:
            raise ValidationError(
                f"A imagem tem {largura} × {altura} px e é pequena demais para este espaço. "
                f"Envie pelo menos {f.min_largura} × {f.min_altura} px (ideal: {f.largura} × {f.altura} px)."
            )

    def __eq__(self, outro):
        return isinstance(outro, DimensaoMinima) and outro.formato == self.formato


def ajustar_imagem(arquivo, formato):
    """Recorta pelo centro e reduz para o tamanho do layout. Devolve (conteúdo, extensão)."""
    f = FORMATOS[formato]
    arquivo.seek(0)
    img = ImageOps.exif_transpose(Image.open(arquivo))  # respeita a rotação de fotos de celular
    if f.recortar:
        img = ImageOps.fit(img.convert("RGB"), (f.largura, f.altura), Image.LANCZOS, centering=(0.5, 0.4))
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=85, optimize=True, progressive=True)
        return buf.getvalue(), ".jpg"
    img = img.convert("RGBA")
    img.thumbnail((f.largura, f.altura), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue(), ".png"


class ImagemPadronizada(models.ImageField):
    """ImageField que mostra o tamanho certo no painel, recusa imagem pequena e ajusta ao layout."""

    def __init__(self, *args, formato=None, **kwargs):
        self.formato = formato
        if formato:
            kwargs.setdefault("help_text", FORMATOS[formato].ajuda())
            kwargs["validators"] = [*VALIDA_IMAGEM, DimensaoMinima(formato)]
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        nome, caminho, args, kwargs = super().deconstruct()
        kwargs["formato"] = self.formato
        kwargs.pop("validators", None)  # recriados a partir do formato
        return nome, caminho, args, kwargs

    def formfield(self, **kwargs):
        campo = super().formfield(**kwargs)
        campo.widget.attrs["accept"] = "image/jpeg,image/png,image/webp"
        return campo

    def pre_save(self, instancia, add):
        arquivo = getattr(instancia, self.attname)
        if self.formato and arquivo and not arquivo._committed:
            conteudo, ext = ajustar_imagem(arquivo, self.formato)
            base = os.path.splitext(os.path.basename(arquivo.name))[0]
            setattr(instancia, self.attname, ContentFile(conteudo, name=base + ext))
        return super().pre_save(instancia, add)
