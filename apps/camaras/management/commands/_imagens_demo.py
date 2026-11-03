"""Imagens ilustrativas geradas por código para a câmara de demonstração.

São desenhos abstratos e originais: servem só para mostrar onde entram brasão,
banners, fotos e imagens de notícias. Cada câmara cliente troca pelas suas no painel.
"""

import io
import math
import random

from django.core.files.base import ContentFile
from PIL import Image, ImageDraw, ImageFilter, ImageFont

AZUL = (11, 79, 138)
NOITE = (20, 32, 46)
OURO = (224, 165, 38)


def _png(img, nome):
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return ContentFile(buf.getvalue(), name=nome)


def _jpg(img, nome):
    buf = io.BytesIO()
    img.convert("RGB").save(buf, "JPEG", quality=84, optimize=True, progressive=True)
    return ContentFile(buf.getvalue(), name=nome)


def _gradiente(w, h, c1, c2, diagonal=True):
    img = Image.new("RGB", (w, h), c1)
    px = img.load()
    for x in range(w):
        for y in range(0, h, 1):
            t = ((x / w) * 0.7 + (y / h) * 0.3) if diagonal else y / h
            px[x, y] = tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))
    return img


def _gradiente_rapido(w, h, c1, c2):
    """Gradiente diagonal gerado em baixa resolução e ampliado (rápido e suave)."""
    return _gradiente(64, 20, c1, c2).resize((w, h), Image.BICUBIC)


def brasao(sigla="CMD"):
    """Escudo estilizado com estrela, faixa e sigla. 512 × 512, fundo transparente."""
    s = 512
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    escudo = [(96, 70), (416, 70), (416, 270), (392, 350), (330, 420), (256, 462), (182, 420), (120, 350), (96, 270)]
    d.polygon([(x, y + 6) for x, y in escudo], fill=(0, 0, 0, 70))
    d.polygon(escudo, fill=OURO)
    interno = [(118, 92), (394, 92), (394, 268), (372, 340), (318, 402), (256, 438), (194, 402), (140, 340), (118, 268)]
    d.polygon(interno, fill=AZUL)
    # Metade inferior em verde, como campo.
    d.polygon([(118, 268), (394, 268), (372, 340), (318, 402), (256, 438), (194, 402), (140, 340)], fill=(31, 122, 76))
    # Sol nascente.
    d.pieslice([196, 208, 316, 328], 180, 360, fill=OURO)
    for i in range(9):
        a = math.pi + i * math.pi / 8
        d.line([(256 + 70 * math.cos(a), 268 + 70 * math.sin(a)), (256 + 100 * math.cos(a), 268 + 100 * math.sin(a))],
               fill=OURO, width=8)
    # Estrela.
    pts = []
    for i in range(10):
        r = 34 if i % 2 == 0 else 14
        a = -math.pi / 2 + i * math.pi / 5
        pts.append((256 + r * math.cos(a), 142 + r * math.sin(a)))
    d.polygon(pts, fill=(255, 255, 255))
    # Faixa com a sigla.
    d.rounded_rectangle([70, 300, 442, 352], radius=10, fill=(255, 255, 255), outline=OURO, width=5)
    fonte = ImageFont.load_default(size=36)
    d.text((256, 327), sigla, fill=NOITE, font=fonte, anchor="mm")
    return _png(img.resize((256, 256), Image.LANCZOS), "brasao.png")


def banner(semente, c1, c2, nome):
    """Composição abstrata 1600 × 500: colunas de um prédio público, sol e formas geométricas."""
    rnd = random.Random(semente)
    w, h = 1600, 500
    img = _gradiente_rapido(w, h, c1, c2).convert("RGBA")
    camada = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(camada)
    for _ in range(14):
        r = rnd.randint(40, 220)
        x, y = rnd.randint(0, w), rnd.randint(-60, h)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, rnd.randint(8, 22)))
    # Fachada de prédio legislativo à direita.
    base_x, base_y = 980, 470
    d.polygon([(base_x - 20, 190), (base_x + 290, 110), (base_x + 600, 190)], fill=(255, 255, 255, 60))
    d.rectangle([base_x - 10, 190, base_x + 590, 214], fill=(255, 255, 255, 70))
    for i in range(7):
        x = base_x + 20 + i * 88
        d.rectangle([x, 226, x + 34, base_y - 30], fill=(255, 255, 255, 55))
    d.rectangle([base_x - 30, base_y - 30, base_x + 610, base_y], fill=(255, 255, 255, 70))
    d.ellipse([base_x + 230, 20, base_x + 350, 140], fill=OURO + (120,))
    camada = camada.filter(ImageFilter.GaussianBlur(1.2))
    img.alpha_composite(camada)
    return _jpg(img, nome)


def foto_vereador(semente, nome):
    """Ilustração de busto (silhueta) sobre fundo colorido, 400 × 400. Não é foto de pessoa real."""
    rnd = random.Random(semente)
    paleta = [(11, 79, 138), (31, 122, 76), (142, 68, 173), (192, 57, 43), (211, 84, 0), (22, 160, 133)]
    fundo = paleta[semente % len(paleta)]
    claro = tuple(min(255, c + 70) for c in fundo)
    s = 400
    img = _gradiente(40, 40, claro, fundo).resize((s, s), Image.BICUBIC)
    d = ImageDraw.Draw(img)
    pele = rnd.choice([(241, 200, 160), (224, 172, 125), (198, 134, 90), (141, 85, 54), (110, 66, 40)])
    roupa = rnd.choice([(40, 44, 52), (60, 72, 88), (245, 245, 245), (30, 58, 95)])
    d.ellipse([70, 270, 330, 520], fill=roupa)
    d.rectangle([178, 230, 222, 290], fill=pele)
    d.polygon([(170, 280), (200, 330), (230, 280)], fill=(255, 255, 255))
    d.ellipse([130, 90, 270, 250], fill=pele)
    cabelo = rnd.choice([(30, 22, 18), (70, 45, 30), (120, 90, 60), (160, 160, 160)])
    if semente % 2:
        d.chord([124, 78, 276, 210], 180, 360, fill=cabelo)
        d.rectangle([124, 140, 146, 260], fill=cabelo)
        d.rectangle([254, 140, 276, 260], fill=cabelo)
    else:
        d.chord([126, 80, 274, 190], 180, 360, fill=cabelo)
    return _jpg(img, nome)


def imagem_noticia(semente, c1, c2, nome):
    """Ilustração 1200 × 675 para cartões de notícia."""
    rnd = random.Random(semente)
    w, h = 1200, 675
    img = _gradiente_rapido(w, h, c1, c2).convert("RGBA")
    camada = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(camada)
    for _ in range(9):
        x0, y0 = rnd.randint(-100, w), rnd.randint(-100, h)
        lado = rnd.randint(120, 380)
        d.rounded_rectangle([x0, y0, x0 + lado, y0 + lado], radius=lado // 6,
                            fill=(255, 255, 255, rnd.randint(10, 30)))
    for i in range(5):
        x = 380 + i * 110
        alt = rnd.randint(140, 360)
        d.rounded_rectangle([x, h - 80 - alt, x + 70, h - 80], radius=8, fill=OURO + (150,) if i == 3 else (255, 255, 255, 110))
    d.line([(340, h - 80), (980, h - 80)], fill=(255, 255, 255, 160), width=4)
    img.alpha_composite(camada)
    return _jpg(img, nome)
