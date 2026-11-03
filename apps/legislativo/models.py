from django.db import models

from apps.camaras.models import ModeloDaCamara


class Legislatura(ModeloDaCamara):
    numero = models.PositiveIntegerField("número")
    inicio = models.DateField("início")
    fim = models.DateField()

    class Meta:
        ordering = ["-inicio"]
        unique_together = [("camara", "numero")]

    def __str__(self):
        return f"{self.numero}ª Legislatura ({self.inicio.year}–{self.fim.year})"


class Vereador(ModeloDaCamara):
    nome_parlamentar = models.CharField(max_length=120)
    nome_civil = models.CharField(max_length=200, blank=True)
    partido = models.CharField(max_length=30, blank=True)
    foto = models.ImageField(upload_to="vereadores/", blank=True)
    biografia = models.TextField(blank=True)
    email = models.EmailField("e-mail", blank=True)
    legislaturas = models.ManyToManyField(Legislatura, blank=True, related_name="vereadores")
    cargo_mesa = models.CharField(
        "cargo na Mesa Diretora", max_length=60, blank=True, help_text="Ex.: Presidente, 1º Secretário."
    )
    em_exercicio = models.BooleanField("em exercício", default=True)

    class Meta:
        verbose_name_plural = "vereadores"
        ordering = ["nome_parlamentar"]

    def __str__(self):
        return self.nome_parlamentar


class Norma(ModeloDaCamara):
    """Leis, resoluções, decretos legislativos, Lei Orgânica, Regimento etc."""

    class Tipo(models.TextChoices):
        LEI_ORDINARIA = "lei", "Lei Ordinária"
        LEI_COMPLEMENTAR = "lc", "Lei Complementar"
        RESOLUCAO = "res", "Resolução"
        DECRETO_LEGISLATIVO = "dl", "Decreto Legislativo"
        PORTARIA = "port", "Portaria"
        LEI_ORGANICA = "lom", "Lei Orgânica"
        REGIMENTO = "ri", "Regimento Interno"
        EMENDA_LOM = "elom", "Emenda à Lei Orgânica"

    tipo = models.CharField(max_length=5, choices=Tipo.choices)
    numero = models.CharField("número", max_length=20, blank=True)
    ano = models.PositiveIntegerField()
    data = models.DateField()
    ementa = models.TextField()
    texto = models.TextField(blank=True, help_text="Texto integral, usado na busca.")
    arquivo = models.FileField(upload_to="normas/%Y/", blank=True)
    publicada = models.BooleanField(default=True)

    class Meta:
        ordering = ["-data", "-numero"]
        indexes = [models.Index(fields=["camara", "tipo", "ano"])]

    def __str__(self):
        numero = f" nº {self.numero}" if self.numero else ""
        return f"{self.get_tipo_display()}{numero}/{self.ano}"
