from django.contrib import admin
from django.shortcuts import redirect
from django.urls import NoReverseMatch, reverse
from django.utils import timezone
from django.utils.html import format_html, format_html_join

from .admin_mixins import camaras_do_usuario, selo
from .exportacao import exportar
from .midia import previa
from .models import Camara, Dominio, IdentidadePortal, Membro, RegistroAuditoria


class DominioInline(admin.TabularInline):
    model = Dominio
    extra = 1


class MembroInline(admin.TabularInline):
    model = Membro
    extra = 1
    autocomplete_fields = ["usuario"]


@admin.register(Camara)
class CamaraAdmin(admin.ModelAdmin):
    list_display = ["nome", "municipio", "uf", "ativa"]
    list_filter = ["uf", "ativa"]
    search_fields = ["nome", "municipio"]
    inlines = [DominioInline, MembroInline]

    def has_module_permission(self, request):
        # Só a equipe da plataforma (superusuários) gerencia câmaras e domínios.
        return request.user.is_superuser


@admin.register(IdentidadePortal)
class IdentidadePortalAdmin(admin.ModelAdmin):
    """Onde a equipe da câmara troca brasão, cor, redes sociais e dados de contato.

    Não cria nem apaga câmaras e não mexe em domínios: isso fica com a plataforma.
    """

    list_display = ["miniatura", "nome", "municipio", "uf"]
    list_display_links = ["miniatura", "nome"]
    readonly_fields = ["previa_brasao"]
    fieldsets = [
        ("Identidade visual", {"fields": ["previa_brasao", "brasao", "cor_primaria"]}),
        ("Redes sociais", {"fields": ["facebook", "instagram", "youtube"]}),
        ("Contato e atendimento", {"fields": ["endereco", "telefone", "email", "horario_atendimento",
                                               "encarregado_lgpd", "cnpj"]}),
    ]

    def get_queryset(self, request):
        return super().get_queryset(request).filter(pk__in=camaras_do_usuario(request.user))

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        # Quem cuida de uma câmara só vai direto para o formulário dela.
        camaras = list(self.get_queryset(request)[:2])
        if len(camaras) == 1:
            return redirect(reverse("admin:camaras_identidadeportal_change", args=[camaras[0].pk]))
        return super().changelist_view(request, extra_context)

    @admin.display(description="brasão")
    def miniatura(self, obj):
        return previa(obj.brasao, 32)

    @admin.display(description="brasão atual")
    def previa_brasao(self, obj):
        return previa(obj.brasao, 96)


ESTADO_DA_ACAO = {"criou": "ok", "alterou": "atencao", "excluiu": "critico", "entrou": "neutro", "saiu": "neutro",
                  "falhou": "critico"}


@admin.register(RegistroAuditoria)
class RegistroAuditoriaAdmin(admin.ModelAdmin):
    """Trilha de auditoria: só leitura, para todos (nem o superusuário edita ou apaga um registro).

    Quem é da câmara vê os registros dela; para isso precisa do grupo "Auditoria" (ou da permissão de ver).
    """

    list_display = ["momento", "usuario_nome", "acao_selo", "tipo", "registro", "ip"]
    list_display_links = ["momento"]
    list_filter = ["acao", "tipo"]
    search_fields = ["usuario_nome", "objeto", "ip"]
    date_hierarchy = "momento"
    list_per_page = 50
    actions = ["exportar_csv"]
    fieldsets = [
        (None, {"fields": ["momento", "usuario_nome", "acao_selo", "tipo", "registro", "ip"]}),
        ("O que mudou", {"fields": ["mudancas"]}),
    ]
    readonly_fields = ["momento", "usuario_nome", "acao_selo", "tipo", "registro", "ip", "mudancas"]
    empty_value_display = "—"

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related("content_type")
        if request.user.is_superuser:
            return qs
        return qs.filter(camara__in=camaras_do_usuario(request.user))

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="ação", ordering="acao")
    def acao_selo(self, obj):
        return selo(ESTADO_DA_ACAO.get(obj.acao, "neutro"), obj.get_acao_display())

    @admin.display(description="registro", ordering="objeto")
    def registro(self, obj):
        if obj.acao != "excluiu" and obj.content_type_id and obj.object_id:
            try:
                url = reverse(f"admin:{obj.content_type.app_label}_{obj.content_type.model}_change",
                              args=[obj.object_id])
                return format_html('<a href="{}">{}</a>', url, obj.objeto)
            except NoReverseMatch:
                pass
        return obj.objeto or "—"

    @staticmethod
    def _em_ordem(obj):
        """Os campos na ordem do formulário (o banco guarda o JSON em outra ordem)."""
        modelo = obj.content_type.model_class() if obj.content_type_id else None
        ordem = [str(c.verbose_name) for c in modelo._meta.get_fields() if hasattr(c, "verbose_name")] if modelo else []
        return sorted(obj.detalhes.items(), key=lambda par: ordem.index(par[0]) if par[0] in ordem else len(ordem))

    @admin.display(description="detalhes")
    def mudancas(self, obj):
        if not obj.detalhes:
            return "—"
        itens = self._em_ordem(obj)
        if obj.acao == "alterou":
            linhas = format_html_join("", "<tr><th scope=\"row\">{}</th><td>{}</td><td>{}</td></tr>",
                                      ((campo, v.get("antes") or "—", v.get("depois") or "—")
                                       for campo, v in itens))
            return format_html('<table class="auditoria-mudancas auditoria-mudancas--diff"><thead><tr><th scope="col">Campo</th>'
                               '<th scope="col">Antes</th><th scope="col">Depois</th></tr></thead>'
                               '<tbody>{}</tbody></table>', linhas)
        linhas = format_html_join("", "<tr><th scope=\"row\">{}</th><td>{}</td></tr>", itens)
        titulo = "Como estava ao ser excluído" if obj.acao == "excluiu" else ""
        return format_html('<p>{}</p><table class="auditoria-mudancas"><tbody>{}</tbody></table>', titulo, linhas)

    @admin.action(description="Exportar os selecionados em CSV")
    def exportar_csv(self, request, queryset):
        campos = ["quando", "quem", "acao", "tipo", "registro", "ip", "detalhes"]
        linhas = ({"quando": timezone.localtime(r.momento).strftime("%d/%m/%Y %H:%M:%S"), "quem": r.usuario_nome,
                   "acao": r.get_acao_display(), "tipo": r.tipo, "registro": r.objeto, "ip": r.ip or "",
                   "detalhes": "; ".join(f"{c}: {v.get('antes', '')} → {v.get('depois', '')}"
                                         if isinstance(v, dict) else f"{c}: {v}" for c, v in r.detalhes.items())}
                  for r in queryset)
        return exportar("csv", "trilha-de-auditoria", campos, linhas)
