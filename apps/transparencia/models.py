from django.core.exceptions import ValidationError
from django.db import models

from apps.camaras.models import ModeloDaCamara
from apps.camaras.midia import VALIDA_DOCUMENTO, CaminhoMidia


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
    arquivo = models.FileField(upload_to=CaminhoMidia("transparencia"), blank=True, validators=VALIDA_DOCUMENTO)
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


def documento_publico(documento):
    """CNPJ inteiro; CPF com os dígitos do meio escondidos, como recomenda a LGPD."""
    d = "".join(c for c in (documento or "") if c.isdigit())
    if len(d) == 14:
        return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"
    if len(d) == 11:
        return f"***.{d[3:6]}.{d[6:9]}-**"
    return documento or ""


class Licitacao(ModeloDaCamara):
    """Contratação (licitação, dispensa, inexigibilidade…) importada de uma fonte externa, como o PNCP."""

    origem = models.CharField(max_length=20, default="pncp", editable=False)
    id_origem = models.CharField(
        "identificador na origem", max_length=60, editable=False,
        help_text="No PNCP, o número de controle (ex.: 00000000000100-1-000001/2026).",
    )
    numero = models.CharField("número", max_length=40, blank=True)
    ano = models.PositiveIntegerField()
    processo = models.CharField(max_length=60, blank=True)
    modalidade = models.CharField(max_length=60)
    situacao = models.CharField("situação", max_length=60, blank=True)
    objeto = models.TextField()
    valor_estimado = models.DecimalField("valor estimado", max_digits=16, decimal_places=2, null=True, blank=True)
    valor_homologado = models.DecimalField("valor homologado", max_digits=16, decimal_places=2, null=True, blank=True)
    abertura_propostas = models.DateTimeField("abertura das propostas", null=True, blank=True)
    publicada_em = models.DateTimeField("publicada na origem em")
    link_origem = models.URLField("link na origem", max_length=500, blank=True)
    link_sistema = models.URLField("link no sistema de compras", max_length=500, blank=True)

    class Meta:
        verbose_name = "licitação"
        verbose_name_plural = "licitações"
        ordering = ["-publicada_em"]
        unique_together = [("camara", "origem", "id_origem")]
        indexes = [models.Index(fields=["camara", "ano", "modalidade"])]

    def __str__(self):
        if not self.numero:
            return f"{self.modalidade} {self.ano}"
        numero = self.numero if "/" in self.numero else f"{self.numero}/{self.ano}"  # o PNCP às vezes já traz o ano
        return f"{self.modalidade} nº {numero}"


class Contrato(ModeloDaCamara):
    """Contrato ou empenho com força de contrato, importado de uma fonte externa, como o PNCP."""

    origem = models.CharField(max_length=20, default="pncp", editable=False)
    id_origem = models.CharField("identificador na origem", max_length=60, editable=False)
    licitacao = models.ForeignKey(
        Licitacao, verbose_name="licitação", on_delete=models.SET_NULL, null=True, blank=True, related_name="contratos",
    )
    numero = models.CharField("número", max_length=60, blank=True)
    ano = models.PositiveIntegerField()
    processo = models.CharField(max_length=60, blank=True)
    tipo = models.CharField(max_length=60, blank=True)
    objeto = models.TextField()
    fornecedor = models.CharField(max_length=255)
    fornecedor_documento = models.CharField(
        "CPF/CNPJ do fornecedor", max_length=20, blank=True,
        help_text="CPF aparece mascarado no portal (LGPD).",
    )
    valor_inicial = models.DecimalField("valor inicial", max_digits=16, decimal_places=2, null=True, blank=True)
    valor_global = models.DecimalField("valor global", max_digits=16, decimal_places=2, null=True, blank=True)
    assinatura = models.DateField(null=True, blank=True)
    vigencia_inicio = models.DateField("início da vigência", null=True, blank=True)
    vigencia_fim = models.DateField("fim da vigência", null=True, blank=True)
    publicado_em = models.DateTimeField("publicado na origem em")
    link_origem = models.URLField("link na origem", max_length=500, blank=True)

    class Meta:
        ordering = ["-assinatura", "-publicado_em"]
        unique_together = [("camara", "origem", "id_origem")]
        indexes = [models.Index(fields=["camara", "ano"])]

    def __str__(self):
        return f"Contrato nº {self.numero}" if self.numero else f"Contrato {self.ano}"

    @property
    def fornecedor_documento_publico(self):
        return documento_publico(self.fornecedor_documento)


# Elemento de despesa (Portaria Interministerial 163/2001): os dígitos 5 e 6 do código (3.3.90.XX).
ELEMENTOS_DESPESA = {
    "01": "Aposentadorias e reformas", "03": "Pensões", "04": "Contratação por tempo determinado",
    "08": "Outros benefícios assistenciais", "11": "Vencimentos e vantagens fixas", "13": "Obrigações patronais",
    "14": "Diárias", "16": "Outras despesas variáveis de pessoal", "30": "Material de consumo",
    "31": "Premiações", "32": "Material de distribuição gratuita", "33": "Passagens e locomoção",
    "35": "Serviços de consultoria", "36": "Serviços de terceiros (pessoa física)",
    "37": "Locação de mão de obra", "39": "Serviços de terceiros (pessoa jurídica)",
    "40": "Serviços de tecnologia da informação", "41": "Contribuições", "46": "Auxílio-alimentação",
    "47": "Obrigações tributárias e contributivas", "48": "Auxílio financeiro a pessoa física",
    "49": "Auxílio-transporte", "51": "Obras e instalações", "52": "Equipamentos e material permanente",
    "91": "Sentenças judiciais", "92": "Despesas de exercícios anteriores", "93": "Indenizações e restituições",
}
ELEMENTOS_DIARIAS = {"14", "15"}


class Despesa(ModeloDaCamara):
    """Empenho da câmara, com o que já foi liquidado e pago. Importado do SIM/TCE-CE."""

    origem = models.CharField(max_length=20, default="tce-ce", editable=False)
    id_origem = models.CharField("identificador na origem", max_length=80, editable=False)
    ano = models.PositiveIntegerField("exercício")
    numero_empenho = models.CharField("empenho", max_length=20)
    data_empenho = models.DateField("data do empenho")
    unidade_orcamentaria = models.CharField("unidade orçamentária", max_length=10, blank=True)
    funcao = models.CharField("função", max_length=4, blank=True)
    elemento = models.CharField("elemento de despesa", max_length=10, blank=True, help_text="Ex.: 33903500.")
    modalidade_empenho = models.CharField(max_length=20, blank=True)
    historico = models.TextField("histórico")
    fornecedor = models.CharField("credor", max_length=255, blank=True)
    fornecedor_documento = models.CharField("CPF/CNPJ do credor", max_length=20, blank=True)
    numero_contrato = models.CharField("contrato", max_length=40, blank=True)
    numero_licitacao = models.CharField("licitação", max_length=40, blank=True)
    valor_empenhado = models.DecimalField("empenhado", max_digits=16, decimal_places=2, default=0)
    valor_liquidado = models.DecimalField("liquidado", max_digits=16, decimal_places=2, default=0)
    valor_pago = models.DecimalField("pago", max_digits=16, decimal_places=2, default=0)

    class Meta:
        ordering = ["-data_empenho", "-numero_empenho"]
        unique_together = [("camara", "origem", "id_origem")]
        indexes = [models.Index(fields=["camara", "ano", "elemento"])]

    def __str__(self):
        return f"Empenho {self.numero_empenho}/{self.ano}"

    @property
    def codigo_elemento(self):
        return self.elemento[4:6] if len(self.elemento) >= 6 else ""

    @property
    def nome_elemento(self):
        return ELEMENTOS_DESPESA.get(self.codigo_elemento, self.elemento)

    @property
    def eh_diaria(self):
        return self.codigo_elemento in ELEMENTOS_DIARIAS

    @property
    def fornecedor_documento_publico(self):
        return documento_publico(self.fornecedor_documento)

    def recalcular(self):
        """Soma liquidações e pagamentos não estornados."""
        totais = {tipo: models.Sum("valor", filter=models.Q(tipo=tipo, estornado=False)) for tipo in "LP"}
        somas = self.movimentos.aggregate(**totais)
        self.valor_liquidado = somas["L"] or 0
        self.valor_pago = somas["P"] or 0


class MovimentoDespesa(models.Model):
    """Liquidação ou pagamento de um empenho."""

    class Tipo(models.TextChoices):
        LIQUIDACAO = "L", "Liquidação"
        PAGAMENTO = "P", "Pagamento"

    despesa = models.ForeignKey(Despesa, on_delete=models.CASCADE, related_name="movimentos")
    tipo = models.CharField(max_length=1, choices=Tipo.choices)
    numero = models.CharField("número", max_length=30)
    data = models.DateField()
    valor = models.DecimalField(max_digits=16, decimal_places=2)
    estornado = models.BooleanField(default=False)

    class Meta:
        verbose_name = "liquidação ou pagamento"
        verbose_name_plural = "liquidações e pagamentos"
        ordering = ["data"]
        unique_together = [("despesa", "tipo", "numero")]

    def __str__(self):
        return f"{self.get_tipo_display()} {self.numero}"
