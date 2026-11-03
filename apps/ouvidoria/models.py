from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.camaras.models import ModeloDaCamara
from apps.camaras.anexos import DICA, VALIDADORES, CaminhoAnexo, obter_armazenamento
from apps.camaras.protocolo import codigo_consulta, salvar_com_protocolo


class Manifestacao(ModeloDaCamara):
    """Manifestação de ouvidoria (Lei 13.460/2017)."""

    class Tipo(models.TextChoices):
        RECLAMACAO = "reclamacao", "Reclamação"
        DENUNCIA = "denuncia", "Denúncia"
        SUGESTAO = "sugestao", "Sugestão"
        ELOGIO = "elogio", "Elogio"
        SOLICITACAO = "solicitacao", "Solicitação"

    class Situacao(models.TextChoices):
        RECEBIDA = "recebida", "Recebida"
        EM_ANALISE = "analise", "Em análise"
        PRORROGADA = "prorrogada", "Prorrogada"
        RESPONDIDA = "respondida", "Respondida"
        ARQUIVADA = "arquivada", "Arquivada"

    ABERTAS = (Situacao.RECEBIDA, Situacao.EM_ANALISE, Situacao.PRORROGADA)

    protocolo = models.CharField(max_length=20, editable=False)
    codigo_consulta = models.CharField("código de consulta", max_length=16, editable=False)
    tipo = models.CharField(max_length=12, choices=Tipo.choices)
    assunto = models.CharField(max_length=200)
    descricao = models.TextField("descrição")
    anexo = models.FileField(
        "anexo do manifestante", upload_to=CaminhoAnexo("ouvidoria"), storage=obter_armazenamento,
        validators=VALIDADORES, blank=True, help_text=DICA,
    )
    anonima = models.BooleanField(
        "anônima", default=False,
        help_text="Sem identificação. O acompanhamento é só pelo protocolo e código.",
    )
    sigilo = models.BooleanField(
        "pedir sigilo da identidade", default=False,
        help_text="A identidade é preservada (Lei 13.460/2017, art. 10, § 7º).",
    )
    nome = models.CharField(max_length=200, blank=True)
    email = models.EmailField("e-mail", blank=True)
    telefone = models.CharField(max_length=30, blank=True)
    situacao = models.CharField("situação", max_length=12, choices=Situacao.choices, default=Situacao.RECEBIDA)
    prazo = models.DateField(editable=False)
    prorrogada = models.BooleanField(default=False, editable=False)
    resposta = models.TextField(blank=True, help_text="Resposta conclusiva, visível ao cidadão na consulta.")
    anexo_resposta = models.FileField(
        "anexo da resposta", upload_to=CaminhoAnexo("ouvidoria"), storage=obter_armazenamento,
        validators=VALIDADORES, blank=True, help_text=DICA,
    )
    respondida_em = models.DateTimeField(null=True, blank=True, editable=False)

    class Meta:
        verbose_name = "manifestação"
        verbose_name_plural = "manifestações"
        ordering = ["-criado_em"]
        unique_together = [("camara", "protocolo")]

    def __str__(self):
        return f"{self.get_tipo_display()} {self.protocolo}"

    def clean(self):
        if not self.anonima and not (self.nome and self.email):
            raise ValidationError("Informe nome e e-mail, ou marque a manifestação como anônima.")

    @property
    def vencida(self):
        return self.situacao in self.ABERTAS and timezone.localdate() > self.prazo

    def prorrogar(self):
        """Prorrogação única de 30 dias, com justificativa (art. 16)."""
        if self.prorrogada:
            raise ValueError("A manifestação já foi prorrogada.")
        self.prazo += timedelta(days=settings.OUVIDORIA_PRORROGACAO_DIAS)
        self.prorrogada = True
        self.situacao = self.Situacao.PRORROGADA

    def save(self, *args, **kwargs):
        if self.anonima:
            # LGPD: se é anônima, não guardamos nenhum dado pessoal.
            self.nome = self.email = self.telefone = ""
            self.sigilo = False
        if self.situacao == self.Situacao.RESPONDIDA and not self.respondida_em:
            self.respondida_em = timezone.now()
        if self.pk:
            return super().save(*args, **kwargs)
        self.prazo = timezone.localdate() + timedelta(days=settings.OUVIDORIA_PRAZO_DIAS)
        self.codigo_consulta = codigo_consulta()
        return salvar_com_protocolo(self, lambda: super(Manifestacao, self).save(*args, **kwargs))
