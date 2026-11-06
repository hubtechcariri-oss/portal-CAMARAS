"""Fontes de dados externas de cada câmara e o registro de cada importação."""

from datetime import timedelta

from django.db import models
from django.utils import timezone

from apps.camaras.models import ModeloDaCamara

DIAS_SEM_ATUALIZAR = 3  # passou disso sem sucesso, o Início avisa


class FonteDados(ModeloDaCamara):
    """Uma fonte que a câmara usa (ex.: PNCP). O tipo escolhe o conector."""

    class Tipo(models.TextChoices):
        PNCP = "pncp", "PNCP: licitações e contratos"
        TCE_CE = "tce-ce", "TCE-CE (SIM): despesas, receitas, licitações e contratos"

    tipo = models.CharField(max_length=30, choices=Tipo.choices)
    ativa = models.BooleanField(
        default=True, help_text="Fontes ativas são importadas toda noite.",
    )
    configuracao = models.JSONField(
        "configuração", default=dict, blank=True,
        help_text="Ajustes do conector. O PNCP usa o CNPJ cadastrado na câmara e não precisa de nada aqui. "
                  "O TCE-CE aceita {\"codigo_municipio\": \"017\"} e, se preciso, {\"codigo_orgao\": \"11\"}.",
    )
    ultima_execucao = models.DateTimeField("última execução", null=True, blank=True, editable=False)
    ultimo_sucesso = models.DateTimeField("último sucesso", null=True, blank=True, editable=False)

    class Meta:
        verbose_name = "fonte de dados"
        verbose_name_plural = "fontes de dados"
        ordering = ["camara", "tipo"]
        unique_together = [("camara", "tipo")]

    def __str__(self):
        return self.get_tipo_display()

    @property
    def atrasada(self):
        """Ativa e sem importação bem-sucedida há mais de DIAS_SEM_ATUALIZAR dias."""
        if not self.ativa:
            return False
        return not self.ultimo_sucesso or self.ultimo_sucesso < timezone.now() - timedelta(days=DIAS_SEM_ATUALIZAR)


class Importacao(models.Model):
    """Uma execução de um conector: quando rodou, o que trouxe e o erro, se houve."""

    class Situacao(models.TextChoices):
        RODANDO = "rodando", "Em andamento"
        SUCESSO = "sucesso", "Concluída"
        ERRO = "erro", "Com erro"

    fonte = models.ForeignKey(FonteDados, on_delete=models.CASCADE, related_name="importacoes")
    iniciada_em = models.DateTimeField(default=timezone.now)
    terminada_em = models.DateTimeField(null=True, blank=True)
    situacao = models.CharField("situação", max_length=10, choices=Situacao.choices, default=Situacao.RODANDO)
    desde = models.DateField(null=True, blank=True, help_text="Início do período consultado na origem.")
    novos = models.PositiveIntegerField(default=0)
    atualizados = models.PositiveIntegerField(default=0)
    mensagem = models.TextField(blank=True)

    class Meta:
        verbose_name = "importação"
        verbose_name_plural = "importações"
        ordering = ["-iniciada_em"]

    def __str__(self):
        return f"{self.fonte} em {timezone.localtime(self.iniciada_em):%d/%m/%Y %H:%M}"
