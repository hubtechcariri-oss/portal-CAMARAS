from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.camaras.models import ModeloDaCamara
from apps.camaras.anexos import DICA, VALIDADORES, CaminhoAnexo, obter_armazenamento
from apps.camaras.protocolo import codigo_consulta, salvar_com_protocolo


class Pedido(ModeloDaCamara):
    """Pedido de acesso à informação (LAI, arts. 10 a 16)."""

    class Situacao(models.TextChoices):
        RECEBIDO = "recebido", "Recebido"
        EM_ANALISE = "analise", "Em análise"
        PRORROGADO = "prorrogado", "Prorrogado"
        RESPONDIDO = "respondido", "Respondido"
        NEGADO = "negado", "Negado"

    protocolo = models.CharField(max_length=20, editable=False)
    codigo_consulta = models.CharField(
        max_length=16, editable=False,
        help_text="Código secreto entregue ao cidadão para acompanhar o pedido.",
    )
    # LGPD: coletamos só o necessário para identificar e responder (LAI, art. 10).
    nome = models.CharField(max_length=200)
    email = models.EmailField("e-mail")
    pedido = models.TextField()
    anexo = models.FileField(
        "anexo do solicitante", upload_to=CaminhoAnexo("esic"), storage=obter_armazenamento,
        validators=VALIDADORES, blank=True, help_text=DICA,
    )
    situacao = models.CharField("situação", max_length=12, choices=Situacao.choices, default=Situacao.RECEBIDO)
    prazo = models.DateField(editable=False)
    resposta = models.TextField(blank=True)
    anexo_resposta = models.FileField(
        "anexo da resposta", upload_to=CaminhoAnexo("esic"), storage=obter_armazenamento,
        validators=VALIDADORES, blank=True, help_text=DICA,
    )
    respondido_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-criado_em"]
        unique_together = [("camara", "protocolo")]

    def __str__(self):
        return f"Pedido {self.protocolo}"

    @property
    def vencido(self):
        abertos = {self.Situacao.RECEBIDO, self.Situacao.EM_ANALISE, self.Situacao.PRORROGADO}
        return self.situacao in abertos and timezone.localdate() > self.prazo

    def prorrogar(self):
        """Prorrogação única de 10 dias (LAI, art. 11, § 2º)."""
        if self.situacao == self.Situacao.PRORROGADO:
            raise ValueError("O pedido já foi prorrogado.")
        self.prazo += timedelta(days=settings.ESIC_PRORROGACAO_DIAS)
        self.situacao = self.Situacao.PRORROGADO

    def save(self, *args, **kwargs):
        if self.situacao in (self.Situacao.RESPONDIDO, self.Situacao.NEGADO) and not self.respondido_em:
            self.respondido_em = timezone.now()
        if self.pk:
            return super().save(*args, **kwargs)
        # Prazo em dias corridos. Confirmar a regra de contagem na regulamentação local da LAI.
        self.prazo = timezone.localdate() + timedelta(days=settings.ESIC_PRAZO_DIAS)
        self.codigo_consulta = codigo_consulta()
        return salvar_com_protocolo(self, lambda: super(Pedido, self).save(*args, **kwargs))
