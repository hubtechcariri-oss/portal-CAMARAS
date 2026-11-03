"""Texto rico das notícias: editor Trix no painel, HTML limpo (nh3) no banco e no portal.

Só passam subtítulo, negrito, itálico, listas, link e citação. Todo o resto (scripts,
estilos, imagens coladas, atributos) é removido, tanto ao salvar quanto ao exibir.
"""

import re

import nh3
from django.utils.html import linebreaks, strip_tags
from django.utils.safestring import mark_safe

TAGS_PERMITIDAS = {"h2", "h3", "p", "div", "br", "strong", "em", "ul", "ol", "li", "a", "blockquote"}
ATRIBUTOS_PERMITIDOS = {"a": {"href"}}
ESQUEMAS_DE_LINK = {"http", "https", "mailto"}

_HTML = re.compile(r"<\s*/?\s*(p|div|h[1-6]|ul|ol|li|blockquote|br|strong|em|b|i|a)\b", re.IGNORECASE)
# Trix grava o subtítulo como <h1>; na página da notícia o <h1> é o título, então vira <h2>.
_H1 = re.compile(r"<(/?)h1\b", re.IGNORECASE)
_B = re.compile(r"<(/?)b\b", re.IGNORECASE)
_I = re.compile(r"<(/?)i\b", re.IGNORECASE)


def eh_html(texto):
    return bool(_HTML.search(texto or ""))


def limpar_html(html):
    html = _H1.sub(r"<\1h2", html or "")
    html = _B.sub(r"<\1strong", html)
    html = _I.sub(r"<\1em", html)
    return nh3.clean(
        html,
        tags=TAGS_PERMITIDAS,
        attributes=ATRIBUTOS_PERMITIDOS,
        url_schemes=ESQUEMAS_DE_LINK,
        link_rel="noopener noreferrer",
    ).strip()


def para_editor(texto):
    """Conteúdo para abrir no editor: notícias antigas em texto puro viram parágrafos."""
    return texto if eh_html(texto) else linebreaks(texto or "", autoescape=True)


def tem_texto(html):
    return bool(strip_tags(html or "").replace("&nbsp;", "").strip())


def exibir(texto):
    """HTML seguro para o portal (texto antigo em texto puro continua com quebras de linha)."""
    if eh_html(texto):
        return mark_safe(limpar_html(texto))
    return linebreaks(texto or "", autoescape=True)
