from django.db import models
from django.utils import timezone

from apps.camaras.models import ModeloDaCamara


class Banner(ModeloDaCamara):
    """Destaque rotativo da página inicial."""

    titulo = models.CharField("título", max_length=120)
    subtitulo = models.CharField("subtítulo", max_length=200, blank=True)
    imagem = models.ImageField(upload_to="banners/", help_text="Recomendado: 1600 × 500 px.")
    texto_alternativo = models.CharField(
        "texto alternativo", max_length=200, blank=True,
        help_text="Descreva a imagem para leitores de tela. Deixe em branco se for só decorativa.",
    )
    link = models.CharField(max_length=300, blank=True, help_text="Endereço aberto ao clicar (ex.: /transparencia/).")
    rotulo_link = models.CharField("texto do botão", max_length=40, blank=True, default="Saiba mais")
    ordem = models.PositiveIntegerField(default=0)
    inicio = models.DateTimeField("exibir a partir de", default=timezone.now)
    fim = models.DateTimeField("exibir até", null=True, blank=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["ordem", "-inicio"]

    def __str__(self):
        return self.titulo

    @classmethod
    def vigentes(cls, camara):
        agora = timezone.now()
        return (
            cls.objects.da_camara(camara)
            .filter(ativo=True, inicio__lte=agora)
            .filter(models.Q(fim__isnull=True) | models.Q(fim__gt=agora))
        )


class Pagina(ModeloDaCamara):
    """Página de conteúdo livre (Sobre a Câmara, Papel do Vereador, Carta de Serviços…)."""

    class Menu(models.TextChoices):
        INSTITUCIONAL = "institucional", "Institucional"
        LEGISLATIVO = "legislativo", "Legislativo"
        TRANSPARENCIA = "transparencia", "Transparência"
        NENHUM = "", "Não aparece no menu"

    titulo = models.CharField("título", max_length=150)
    slug = models.SlugField(max_length=160)
    resumo = models.CharField(max_length=300, blank=True)
    corpo = models.TextField(help_text="Texto da página. Parágrafos separados por linha em branco.")
    imagem = models.ImageField(upload_to="paginas/", blank=True)
    texto_alternativo = models.CharField("texto alternativo da imagem", max_length=200, blank=True)
    menu = models.CharField(max_length=15, choices=Menu.choices, blank=True, default=Menu.INSTITUCIONAL)
    ordem = models.PositiveIntegerField(default=0)
    publicada = models.BooleanField(default=True)

    class Meta:
        verbose_name = "página"
        ordering = ["menu", "ordem", "titulo"]
        unique_together = [("camara", "slug")]

    def __str__(self):
        return self.titulo
