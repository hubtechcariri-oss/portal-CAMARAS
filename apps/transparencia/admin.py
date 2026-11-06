from django.contrib import admin
from django.utils.html import format_html
from django.utils.text import Truncator

from apps.camaras.admin_mixins import AdminDaCamara, selo_publicacao

from .models import (CategoriaTransparencia, Contrato, Despesa, Documento, GrupoTransparencia, Licitacao, MovimentoDespesa,
                     Receita)


class SoPlataforma:
    """O catálogo é mantido pela equipe da plataforma; as câmaras só leem."""

    def has_module_permission(self, request):
        return request.user.is_superuser


class CategoriaInline(admin.TabularInline):
    model = CategoriaTransparencia
    extra = 0
    prepopulated_fields = {"slug": ["nome"]}


@admin.register(GrupoTransparencia)
class GrupoAdmin(SoPlataforma, admin.ModelAdmin):
    list_display = ["nome", "ordem"]
    inlines = [CategoriaInline]


@admin.register(CategoriaTransparencia)
class CategoriaAdmin(SoPlataforma, admin.ModelAdmin):
    list_display = ["nome", "grupo", "obrigatoria", "ordem"]
    list_filter = ["grupo", "obrigatoria"]
    search_fields = ["nome"]


@admin.register(Documento)
class DocumentoAdmin(AdminDaCamara):
    list_display = ["titulo", "categoria", "data", "competencia", "situacao"]
    list_filter = ["categoria__grupo", "categoria", "publicado"]
    search_fields = ["titulo", "numero", "descricao"]
    date_hierarchy = "data"
    autocomplete_fields = ["categoria"]

    @admin.display(description="situação", ordering="publicado")
    def situacao(self, obj):
        return selo_publicacao(obj.publicado)


class SoLeitura:
    """Dados importados (PNCP etc.): a correção é feita na origem e chega na próxima importação."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @admin.display(description="origem")
    def link(self, obj):
        if not obj.link_origem:
            return "—"
        return format_html('<a href="{}" target="_blank" rel="noopener">ver no PNCP</a>', obj.link_origem)


@admin.register(Licitacao)
class LicitacaoAdmin(SoLeitura, AdminDaCamara):
    list_display = ["__str__", "objeto_curto", "situacao", "valor_estimado", "publicada_em", "link"]
    list_filter = ["ano", "modalidade", "situacao", "origem"]
    search_fields = ["numero", "processo", "objeto", "id_origem"]
    date_hierarchy = "publicada_em"
    readonly_fields = ["id_origem", "link"]
    fieldsets = [
        (None, {"fields": ["camara", "modalidade", "numero", "ano", "processo", "situacao", "objeto"]}),
        ("Valores e datas", {"fields": ["valor_estimado", "valor_homologado", "abertura_propostas", "publicada_em"]}),
        ("Origem", {"fields": ["id_origem", "link", "link_sistema"]}),
    ]

    @admin.display(description="objeto")
    def objeto_curto(self, obj):
        return Truncator(obj.objeto).chars(90)


@admin.register(Contrato)
class ContratoAdmin(SoLeitura, AdminDaCamara):
    list_display = ["__str__", "fornecedor", "objeto_curto", "valor_global", "vigencia_fim", "link"]
    list_filter = ["ano", "tipo", "origem"]
    search_fields = ["numero", "processo", "objeto", "fornecedor", "fornecedor_documento", "id_origem"]
    date_hierarchy = "assinatura"
    readonly_fields = ["id_origem", "link"]
    fieldsets = [
        (None, {"fields": ["camara", "tipo", "numero", "ano", "processo", "licitacao", "objeto"]}),
        ("Fornecedor", {"fields": ["fornecedor", "fornecedor_documento"]}),
        ("Valores e datas", {"fields": ["valor_inicial", "valor_global", "assinatura", "vigencia_inicio",
                                        "vigencia_fim", "publicado_em"]}),
        ("Origem", {"fields": ["id_origem", "link"]}),
    ]

    @admin.display(description="objeto")
    def objeto_curto(self, obj):
        return Truncator(obj.objeto).chars(90)


class MovimentoInline(admin.TabularInline):
    model = MovimentoDespesa
    extra = 0
    can_delete = False
    readonly_fields = ["tipo", "numero", "data", "valor", "estornado"]

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Despesa)
class DespesaAdmin(AdminDaCamara):
    """Despesas do SIM/TCE-CE: só leitura (a correção é feita no sistema contábil e reenviada ao TCE)."""

    list_display = ["__str__", "data_empenho", "fornecedor", "historico_curto", "valor_empenhado", "valor_pago"]
    list_filter = ["ano"]
    search_fields = ["numero_empenho", "historico", "fornecedor", "fornecedor_documento"]
    date_hierarchy = "data_empenho"
    inlines = [MovimentoInline]
    fieldsets = [
        (None, {"fields": ["camara", "ano", "numero_empenho", "data_empenho", "historico"]}),
        ("Classificação", {"fields": ["unidade_orcamentaria", "funcao", "elemento", "modalidade_empenho",
                                      "numero_contrato", "numero_licitacao"]}),
        ("Credor e valores", {"fields": ["fornecedor", "fornecedor_documento", "valor_empenhado",
                                         "valor_liquidado", "valor_pago"]}),
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @admin.display(description="histórico")
    def historico_curto(self, obj):
        return Truncator(obj.historico).chars(90)


@admin.register(Receita)
class ReceitaAdmin(SoLeitura, AdminDaCamara):
    """Receitas do SIM/TCE-CE (repasse do duodécimo): só leitura."""

    list_display = ["competencia", "descricao", "valor_mes", "valor_acumulado"]
    list_filter = ["ano"]
    date_hierarchy = "competencia"
    fields = ["camara", "ano", "competencia", "descricao", "conta", "valor_mes", "valor_acumulado", "id_origem"]
    readonly_fields = ["id_origem"]
