from django.contrib import admin, messages

from apps.camaras.admin_mixins import AdminDaCamara

from .models import Pedido


@admin.register(Pedido)
class PedidoAdmin(AdminDaCamara):
    list_display = ["protocolo", "nome", "criado_em", "prazo", "situacao", "vencido"]
    list_filter = ["situacao"]
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
