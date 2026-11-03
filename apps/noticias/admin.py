from django import forms
from django.contrib import admin
from django.utils.html import format_html

from apps.camaras.admin_mixins import AdminDaCamara, FormDaCamara, SituacaoPublicacaoFilter, selo_publicacao
from apps.camaras.midia import previa
from apps.camaras.texto_rico import limpar_html, tem_texto
from apps.camaras.widgets import EditorTexto

from .models import Noticia


def _booleano(valor):
    return valor in (True, "True", "true", "1")


class NoticiaForm(FormDaCamara):
    publicada = forms.TypedChoiceField(
        label="Situação",
        choices=[(True, "Publicada"), (False, "Rascunho")],
        coerce=_booleano,
        widget=forms.RadioSelect,
        initial=True,
        help_text="Com “publicar em” no futuro, a notícia fica agendada e só aparece no portal nessa data.",
    )

    class Meta:
        model = Noticia
        fields = "__all__"
        widgets = {
            "titulo": forms.TextInput(attrs={"class": "campo-largo"}),
            "resumo": forms.Textarea(attrs={"rows": 3, "class": "campo-largo", "data-contador": "300"}),
            "texto_alternativo": forms.TextInput(attrs={"class": "campo-largo"}),
            "corpo": EditorTexto(attrs={"aria_label": "Texto da notícia"}),
        }

    def clean_corpo(self):
        corpo = limpar_html(self.cleaned_data.get("corpo", ""))
        if not tem_texto(corpo):
            raise forms.ValidationError("Escreva o texto da notícia.")
        return corpo

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "resumo" in self.fields:
            self.fields["resumo"].help_text = "Aparece na lista de notícias e no compartilhamento. Até 300 caracteres."
        if "slug" in self.fields:
            atual = self.instance.slug or "endereco-da-noticia"
            self.fields["slug"].help_text = format_html(
                'Endereço no portal: <code class="previa-slug">/noticias/<span data-previa-slug>{}</span>/</code>',
                atual,
            )


@admin.register(Noticia)
class NoticiaAdmin(AdminDaCamara):
    form = NoticiaForm
    list_display = ["miniatura", "titulo", "publicada_em", "situacao"]
    list_display_links = ["miniatura", "titulo"]
    readonly_fields = ["imagem_atual"]
    list_filter = [SituacaoPublicacaoFilter]
    search_fields = ["titulo", "corpo"]
    prepopulated_fields = {"slug": ["titulo"]}
    date_hierarchy = "publicada_em"
    save_on_top = True
    # O último grupo vira o cartão "Publicação" na coluna lateral (templates/admin/noticias/noticia/change_form.html).
    fieldsets = [
        ("Conteúdo", {"fields": ["titulo", "resumo", "corpo", "imagem", "imagem_atual", "texto_alternativo"]}),
        ("Publicação", {"fields": ["publicada", "publicada_em", "camara", "slug"]}),
    ]

    class Media:
        js = ["js/painel.js"]

    @admin.display(description="imagem")
    def miniatura(self, obj):
        return previa(obj.imagem, 45)

    @admin.display(description="situação", ordering="publicada")
    def situacao(self, obj):
        return selo_publicacao(obj.publicada, obj.publicada_em)

    @admin.display(description="imagem atual")
    def imagem_atual(self, obj):
        return previa(obj.imagem, 160)
