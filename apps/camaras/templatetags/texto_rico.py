from django import template

from apps.camaras.texto_rico import exibir

register = template.Library()


@register.filter
def texto_rico(valor):
    """{{ noticia.corpo|texto_rico }}: HTML limpo (nh3) ou texto puro com quebras de linha."""
    return exibir(valor)
