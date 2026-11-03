from django.core.exceptions import ValidationError
from django.db import models

from apps.camaras.models import ModeloDaCamara


class GrupoTransparencia(models.Model):
    """Agrupamento do menu de transparência (catálogo comum a todas as câmaras)."""

    nome = models.CharField(max_length=120)
    ordem = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["ordem", "nome"]
        verbose_name = "grupo de transparência"
        verbose_name_plural = "grupos de transparência"

    def __str__(self):
        return self.nome


class CategoriaTransparencia(models.Model):
    """Item do menu de transparência (ex.: Diárias, Contratos, RGF).

    O catálogo é da plataforma, e não de cada câmara, para que todas sigam a mesma
    estrutura avaliada pelo PNTP/Tribunais de Contas. A matriz muda todo ano, por
    isso fica em dados (editáveis no admin), não em código.
    """

    grupo = models.ForeignKey(GrupoTransparencia, on_delete=models.PROTECT, related_name="categorias")
    nome = models.CharField(max_length=120)
    slug = models.SlugField(max_length=120, unique=True)
    descricao = models.TextField("descrição", blank=True)
    base_legal = models.CharField(max_length=200, blank=True)
    obrigatoria = models.BooleanField(
        "obrigatória", default=False,
        help_text="Marque conforme a matriz PNTP vigente. Alimenta o futuro painel de conformidade.",
    )
    ordem = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["grupo__ordem", "ordem", "nome"]
        verbose_name = "categoria de transparência"
        verbose_name_plural = "categorias de transparência"

    def __str__(self):
        return self.nome


class Documento(ModeloDaCamara):
    """Publicação de transparência: um arquivo, um link para sistema externo, ou ambos."""

    categoria = models.ForeignKey(CategoriaTransparencia, on_delete=models.PROTECT, related_name="documentos")
    titulo = models.CharField("título", max_length=255)
    numero = models.CharField("número", max_length=40, blank=True)
    data = models.DateField(help_text="Data do ato ou da publicação.")
    competencia = models.CharField(
        "competência", max_length=20, blank=True, help_text="Ex.: 09/2026, 2º quadrimestre/2026."
    )
    descricao = models.TextField("descrição", blank=True)
    arquivo = models.FileField(upload_to="transparencia/%Y/", blank=True)
    link_externo = models.URLField(blank=True, help_text="Ex.: consulta no sistema contábil.")
    valor = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    publicado = models.BooleanField(default=True)

    class Meta:
        ordering = ["-data", "-id"]
        indexes = [models.Index(fields=["camara", "categoria", "data"])]

    def clean(self):
        if not self.arquivo and not self.link_externo and not self.descricao:
            raise ValidationError("Informe um arquivo, um link externo ou uma descrição.")

    def __str__(self):
        return self.titulo
