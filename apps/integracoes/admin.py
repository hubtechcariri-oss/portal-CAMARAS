from datetime import timedelta

from django.contrib import admin, messages
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.html import format_html, format_html_join

from apps.camaras.admin_mixins import AdminDaCamara, camaras_do_usuario, selo

from . import conectores
from .models import FonteDados, Importacao

SELO_IMPORTACAO = {
    Importacao.Situacao.SUCESSO: "ok",
    Importacao.Situacao.ERRO: "critico",
    Importacao.Situacao.RODANDO: "neutro",
}


def selo_importacao(importacao):
    if importacao is None:
        return selo("neutro", "Nunca importada")
    return selo(SELO_IMPORTACAO[importacao.situacao], importacao.get_situacao_display())


@admin.register(FonteDados)
class FonteDadosAdmin(AdminDaCamara):
    list_display = ["__str__", "camara", "ativa", "ultima", "ultimo_sucesso"]
    list_filter = ["tipo", "ativa"]
    fieldsets = [
        (None, {"fields": ["camara", "tipo", "ativa", "configuracao"]}),
        ("Importações", {"fields": ["ultima_execucao", "ultimo_sucesso", "historico"]}),
    ]
    readonly_fields = ["ultima_execucao", "ultimo_sucesso", "historico"]
    actions = ["importar_agora"]

    @admin.display(description="últimas importações")
    def historico(self, obj):
        if not obj.pk:
            return "—"
        linhas = [
            format_html("<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>",
                        date_format(timezone.localtime(i.iniciada_em), "d/m/Y H:i"), selo_importacao(i),
                        i.novos, i.atualizados, i.mensagem[:200])
            for i in obj.importacoes.all()[:10]
        ]
        if not linhas:
            return "Nenhuma importação ainda."
        return format_html(
            "<table><thead><tr><th>Início</th><th>Situação</th><th>Novos</th><th>Atualizados</th>"
            "<th>Mensagem</th></tr></thead><tbody>{}</tbody></table>", format_html_join("", "{}", ((l,) for l in linhas)))

    @admin.display(description="última importação")
    def ultima(self, obj):
        return selo_importacao(obj.importacoes.first())

    @admin.action(description="Importar agora as fontes selecionadas")
    def importar_agora(self, request, queryset):
        rodando = set(Importacao.objects.filter(
            fonte__in=queryset, situacao=Importacao.Situacao.RODANDO,
            iniciada_em__gte=timezone.now() - timedelta(hours=1),
        ).values_list("fonte_id", flat=True))
        fontes = [f for f in queryset if f.pk not in rodando]
        for fonte in queryset:
            if fonte.pk in rodando:
                self.message_user(request, f"{fonte}: já há uma importação em andamento.", messages.WARNING)
        if fontes:
            conectores.executar_em_segundo_plano([f.pk for f in fontes])
            nomes = ", ".join(str(f) for f in fontes)
            self.message_user(request, f"Importação iniciada: {nomes}. Pode levar alguns minutos; "
                                       "o resultado aparece em Importações.", messages.SUCCESS)


@admin.register(Importacao)
class ImportacaoAdmin(admin.ModelAdmin):
    list_display = ["iniciada_em", "fonte", "camara", "situacao_", "novos", "atualizados", "duracao"]
    list_filter = ["situacao", "fonte__tipo"]
    list_select_related = ["fonte__camara"]
    date_hierarchy = "iniciada_em"
    readonly_fields = [f.name for f in Importacao._meta.fields]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(fonte__camara__in=camaras_do_usuario(request.user))

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @admin.display(description="câmara")
    def camara(self, obj):
        return obj.fonte.camara

    @admin.display(description="situação", ordering="situacao")
    def situacao_(self, obj):
        return selo_importacao(obj)

    @admin.display(description="duração")
    def duracao(self, obj):
        fim = obj.terminada_em or timezone.now()
        segundos = int((fim - obj.iniciada_em).total_seconds())
        return f"{segundos // 60} min {segundos % 60} s" if segundos >= 60 else f"{segundos} s"
