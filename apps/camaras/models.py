from django.conf import settings
from django.db import models


class Camara(models.Model):
    """Um cliente do SaaS: uma câmara municipal (o "tenant")."""

    nome = models.CharField(max_length=200, help_text="Ex.: Câmara Municipal de Exemplo")
    municipio = models.CharField(max_length=120)
    uf = models.CharField("UF", max_length=2)
    cnpj = models.CharField("CNPJ", max_length=18, blank=True)
    endereco = models.CharField("endereço", max_length=255, blank=True)
    telefone = models.CharField(max_length=40, blank=True)
    email = models.EmailField("e-mail", blank=True)
    horario_atendimento = models.CharField("horário de atendimento", max_length=120, blank=True)
    encarregado_lgpd = models.CharField(
        "encarregado (LGPD)", max_length=200, blank=True,
        help_text="Nome e contato do encarregado pelo tratamento de dados (LGPD, art. 41).",
    )
    cor_primaria = models.CharField(max_length=7, default="#0b4f8a", help_text="Cor em hexadecimal.")
    ativa = models.BooleanField(default=True)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "câmara"
        verbose_name_plural = "câmaras"
        ordering = ["uf", "municipio"]

    def __str__(self):
        return self.nome


class Dominio(models.Model):
    """Domínios que respondem por uma câmara (ex.: camaraexemplo.ce.leg.br)."""

    camara = models.ForeignKey(Camara, on_delete=models.CASCADE, related_name="dominios")
    host = models.CharField(max_length=253, unique=True, help_text="Sem http:// e sem porta.")
    principal = models.BooleanField(default=False)

    class Meta:
        verbose_name = "domínio"

    def save(self, *args, **kwargs):
        self.host = self.host.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.host


class Membro(models.Model):
    """Vincula um usuário do painel a uma câmara. Um usuário só administra as câmaras às quais pertence."""

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="membros")
    camara = models.ForeignKey(Camara, on_delete=models.CASCADE, related_name="membros")

    class Meta:
        unique_together = [("usuario", "camara")]
        verbose_name = "membro da equipe"
        verbose_name_plural = "membros da equipe"

    def __str__(self):
        return f"{self.usuario} @ {self.camara}"


class DaCamaraQuerySet(models.QuerySet):
    def da_camara(self, camara):
        return self.filter(camara=camara)


class ModeloDaCamara(models.Model):
    """Base de todo conteúdo que pertence a uma câmara.

    O isolamento é explícito: as views públicas sempre consultam
    `Modelo.objects.da_camara(request.camara)`, e o admin filtra pelas
    câmaras do usuário (ver admin_mixins.AdminDaCamara).
    """

    camara = models.ForeignKey(Camara, on_delete=models.CASCADE, related_name="+")
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    objects = DaCamaraQuerySet.as_manager()

    class Meta:
        abstract = True
