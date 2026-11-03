from django.contrib import admin, messages

from apps.camaras.admin_mixins import AdminDaCamara, FilaDeAtendimentoMixin, PrazoFilter

from .models import Pedido


@admin.register(Pedido)
class PedidoAdmin(FilaDeAtendimentoMixin, AdminDaCamara):
    list_display = ["protocolo", "nome", "criado_em", "prazo", "situacao", "selo_prazo"]
    list_filter = [PrazoFilter, "situacao"]
    search_fields = ["protocolo", "nome", "email", "pedido"]
    readonly_fields = ["protocolo", "codigo_consulta", "prazo", "criado_em", "respondido_em", "anexo"]
    actions = ["prorrogar"]

    @admin.display(boolean=True)
    def vencido(self, obj):
        return obj.vencido

    @admin.action(description="Prorrogar prazo por 10 dias")
    def prorrogar(self, request, queryset):
        for pedido in queryset:
            try:
                pedido.prorrogar()
                pedido.save()
            except ValueError as erro:
                self.message_user(request, f"{pedido}: {erro}", messages.WARNING)
