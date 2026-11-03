from django import forms

from .models import Manifestacao


class ManifestacaoForm(forms.ModelForm):
    ciente_privacidade = forms.BooleanField(
        label="Li o aviso de privacidade e entendo que meus dados serão usados apenas para tratar esta manifestação.",
    )
    tipo = forms.ChoiceField(label="Tipo de manifestação", choices=Manifestacao.Tipo.choices, widget=forms.RadioSelect)
    site = forms.CharField(required=False, widget=forms.TextInput(attrs={"tabindex": "-1", "autocomplete": "off"}))

    class Meta:
        model = Manifestacao
        fields = ["tipo", "assunto", "descricao", "anonima", "nome", "email", "telefone", "sigilo"]
        widgets = {
            "descricao": forms.Textarea(attrs={"rows": 6}),
        }
        labels = {
            "descricao": "Descreva sua manifestação",
            "anonima": "Quero me manifestar sem me identificar",
            "telefone": "Telefone (opcional)",
        }

    def clean_site(self):
        if self.cleaned_data.get("site"):
            raise forms.ValidationError("Envio inválido.")
        return ""


class ConsultaForm(forms.Form):
    protocolo = forms.CharField(max_length=20)
    codigo = forms.CharField(label="Código de consulta", max_length=16)
