from django.db import models
from django.utils import timezone

from apps.camaras.models import ModeloDaCamara
from apps.camaras.midia import VALIDA_IMAGEM, CaminhoMidia


class Noticia(ModeloDaCamara):
    titulo = models.CharField("título", max_length=200)
    slug = models.SlugField(max_length=220)
    resumo = models.CharField(max_length=300, blank=True)
    corpo = models.TextField()
    imagem = models.ImageField(
        upload_to=CaminhoMidia("noticias"), blank=True, validators=VALIDA_IMAGEM,
        help_text="Recomendado: 1200 × 675 px (16:9). JPG, PNG ou WebP até 5 MB.",
    )
    texto_alternativo = models.CharField(
        "texto alternativo da imagem", max_length=200, blank=True,
        help_text="Descreva a imagem para leitores de tela (acessibilidade).",
    )
    publicada_em = models.DateTimeField("publicar em", default=timezone.now)
    publicada = models.BooleanField(default=True)

    class Meta:
        verbose_name = "notícia"
        ordering = ["-publicada_em"]
        unique_together = [("camara", "slug")]

    def __str__(self):
        return self.titulo
