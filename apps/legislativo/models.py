from django.db import models

from apps.camaras.models import ModeloDaCamara
from apps.camaras.midia import VALIDA_DOCUMENTO, VALIDA_IMAGEM, CaminhoMidia


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
    foto = models.ImageField(
        upload_to=CaminhoMidia("vereadores"), blank=True, validators=VALIDA_IMAGEM,
        help_text="Foto de rosto, de preferência quadrada (mínimo 400 × 400 px).",
    )
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
    arquivo = models.FileField(upload_to=CaminhoMidia("normas"), blank=True, validators=VALIDA_DOCUMENTO)
    publicada = models.BooleanField(default=True)

    class Meta:
        ordering = ["-data", "-numero"]
        indexes = [models.Index(fields=["camara", "tipo", "ano"])]

    def __str__(self):
        numero = f" nº {self.numero}" if self.numero else ""
        return f"{self.get_tipo_display()}{numero}/{self.ano}"


class Sessao(ModeloDaCamara):
    class Tipo(models.TextChoices):
        ORDINARIA = "ord", "Ordinária"
        EXTRAORDINARIA = "ext", "Extraordinária"
        SOLENE = "sol", "Solene"
        ESPECIAL = "esp", "Especial"
        AUDIENCIA = "aud", "Audiência Pública"

    tipo = models.CharField(max_length=3, choices=Tipo.choices, default=Tipo.ORDINARIA)
    numero = models.PositiveIntegerField("número")
    data_hora = models.DateTimeField("data e hora")
    legislatura = models.ForeignKey(Legislatura, on_delete=models.PROTECT, null=True, blank=True)
    descricao = models.TextField("descrição", blank=True)
    pauta = models.FileField(upload_to=CaminhoMidia("sessoes"), blank=True, validators=VALIDA_DOCUMENTO)
    ata = models.FileField(upload_to=CaminhoMidia("sessoes"), blank=True, validators=VALIDA_DOCUMENTO)
    video_url = models.URLField("vídeo (link)", blank=True, help_text="Ex.: link do YouTube.")
    presentes = models.ManyToManyField(Vereador, blank=True, related_name="presencas")
    publicada = models.BooleanField(default=True)

    class Meta:
        verbose_name = "sessão"
        verbose_name_plural = "sessões"
        ordering = ["-data_hora"]
        unique_together = [("camara", "tipo", "numero", "data_hora")]

    def __str__(self):
        return f"{self.numero}ª Sessão {self.get_tipo_display()} de {self.data_hora:%d/%m/%Y}"


class Materia(ModeloDaCamara):
    """Proposição legislativa: projetos, requerimentos, indicações, moções etc."""

    class Tipo(models.TextChoices):
        PL = "pl", "Projeto de Lei"
        PLC = "plc", "Projeto de Lei Complementar"
        PR = "pr", "Projeto de Resolução"
        PDL = "pdl", "Projeto de Decreto Legislativo"
        PELOM = "pelo", "Proposta de Emenda à Lei Orgânica"
        REQUERIMENTO = "req", "Requerimento"
        INDICACAO = "ind", "Indicação"
        MOCAO = "moc", "Moção"
        EMENDA = "eme", "Emenda"
        VETO = "vet", "Veto"

    class Situacao(models.TextChoices):
        TRAMITACAO = "tram", "Em tramitação"
        APROVADA = "aprov", "Aprovada"
        REJEITADA = "rejei", "Rejeitada"
        ARQUIVADA = "arq", "Arquivada"
        RETIRADA = "ret", "Retirada"

    tipo = models.CharField(max_length=4, choices=Tipo.choices)
    numero = models.PositiveIntegerField("número")
    ano = models.PositiveIntegerField()
    data_apresentacao = models.DateField("data de apresentação")
    ementa = models.TextField()
    texto = models.TextField(blank=True, help_text="Texto integral, usado na busca.")
    arquivo = models.FileField(upload_to=CaminhoMidia("materias"), blank=True, validators=VALIDA_DOCUMENTO)
    autores = models.ManyToManyField(Vereador, blank=True, related_name="materias")
    autor_externo = models.CharField(
        max_length=120, blank=True, help_text="Quando o autor não é vereador: Poder Executivo, Mesa Diretora, comissão…"
    )
    situacao = models.CharField("situação", max_length=5, choices=Situacao.choices, default=Situacao.TRAMITACAO)
    norma_gerada = models.ForeignKey(
        Norma, on_delete=models.SET_NULL, null=True, blank=True, related_name="materias_origem",
        help_text="Norma resultante, quando a matéria vira lei/resolução.",
    )
    publicada = models.BooleanField(default=True)

    class Meta:
        verbose_name = "matéria"
        verbose_name_plural = "matérias"
        ordering = ["-ano", "-numero"]
        unique_together = [("camara", "tipo", "numero", "ano")]
        indexes = [models.Index(fields=["camara", "tipo", "ano"])]

    def __str__(self):
        return f"{self.get_tipo_display()} nº {self.numero}/{self.ano}"

    @property
    def autoria(self):
        nomes = [v.nome_parlamentar for v in self.autores.all()]
        if self.autor_externo:
            nomes.append(self.autor_externo)
        return ", ".join(nomes)


class Tramitacao(models.Model):
    """Um passo do andamento de uma matéria (leitura, parecer, votação…)."""

    class Resultado(models.TextChoices):
        APROVADA = "aprov", "Aprovada"
        REJEITADA = "rejei", "Rejeitada"

    materia = models.ForeignKey(Materia, on_delete=models.CASCADE, related_name="tramitacoes")
    data = models.DateField()
    descricao = models.CharField("descrição", max_length=255, help_text="Ex.: Lida em plenário; Parecer favorável da CCJ.")
    sessao = models.ForeignKey(Sessao, on_delete=models.SET_NULL, null=True, blank=True, related_name="tramitacoes")
    resultado = models.CharField(max_length=5, choices=Resultado.choices, blank=True)
    votos_sim = models.PositiveSmallIntegerField(null=True, blank=True)
    votos_nao = models.PositiveSmallIntegerField("votos não", null=True, blank=True)
    abstencoes = models.PositiveSmallIntegerField("abstenções", null=True, blank=True)

    class Meta:
        verbose_name = "tramitação"
        verbose_name_plural = "tramitações"
        ordering = ["data", "id"]

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.sessao_id and self.materia_id and self.sessao.camara_id != self.materia.camara_id:
            raise ValidationError({"sessao": "A sessão pertence a outra câmara."})

    def __str__(self):
        return f"{self.data:%d/%m/%Y}: {self.descricao}"
