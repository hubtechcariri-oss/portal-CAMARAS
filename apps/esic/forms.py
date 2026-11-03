from django import forms

from .models import Pedido


class PedidoForm(forms.ModelForm):
    ciente_privacidade = forms.BooleanField(
        label="Li o aviso de privacidade e entendo que meus dados serão usados apenas para responder a este pedido.",
    )
    # Armadilha simples para robôs: campo invisível que humanos não preenchem.
    site = forms.CharField(required=False, widget=forms.TextInput(attrs={"tabindex": "-1", "autocomplete": "off"}))

    class Meta:
        model = Pedido
        fields = ["nome", "email", "pedido"]
        widgets = {"pedido": forms.Textarea(attrs={"rows": 6})}
        labels = {"pedido": "Descreva a informação solicitada"}

    def clean_site(self):
        if self.cleaned_data.get("site"):
            raise forms.ValidationError("Envio inválido.")
        return ""


class ConsultaForm(forms.Form):
    protocolo = forms.CharField(max_length=20)
    codigo = forms.CharField(label="Código de consulta", max_length=16)
