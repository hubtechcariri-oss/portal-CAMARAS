from django import forms
from django.forms import Script

from .texto_rico import para_editor

TRIX = "vendor/trix-2.1.19/"


class EditorTexto(forms.Widget):
    """Editor Trix com barra reduzida: subtítulo, negrito, itálico, listas, link e citação."""

    template_name = "camaras/widgets/editor_texto.html"  # em templates do app: o renderizador de formulários não lê DIRS

    class Media:
        css = {"all": [TRIX + "trix.css"]}
        # defer: o Trix só pode montar depois que a barra própria (no HTML) foi lida;
        # carregado no <head> sem defer, ele encontra a <trix-toolbar> vazia e injeta a barra padrão.
        js = ["js/editor-texto.js", Script(TRIX + "trix.umd.min.js", defer=True)]

    def format_value(self, value):
        return para_editor(value or "")
