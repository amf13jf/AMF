"""Queima legendas (normal + dinâmica) e o motion vinho no vídeo.

Uso:
    python -m video_captions.render entrada.mp4 saida.mp4

Fontes: coloque em video_captions/fonts os arquivos HelveticaNeue-Medium.ttf,
HelveticaNeue-Regular.ttf, Bodoni-Bold.ttf e Bodoni-Italic.ttf (não vão para
o git por licença). Sem eles, usa Helvetica Neue do macOS ou Inter, e Bodoni
Moda (incluída).
"""

import argparse
import importlib
import math
import os
import shutil
import subprocess
import sys
from functools import lru_cache

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

from . import aura_reels4 as script

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, "fonts")

W, H, FPS = 1216, 2160, 30

WINE = (122, 28, 50)
WINE_DEEP = (70, 12, 28)
WINE_LIGHT = (176, 70, 92)
CREAM = (248, 242, 236)
INK = (74, 34, 44)  # texto secundário do motion (vinho bem escuro)
WHITE = (255, 255, 255)

# ---------------------------------------------------------------- fontes

FONT_CANDIDATES = {
    "sans_med": [
        (os.path.join(FONT_DIR, "HelveticaNeue-Medium.ttf"), None),
        ("/System/Library/Fonts/HelveticaNeue.ttc", "medium"),
        ("/usr/share/fonts/opentype/inter/Inter-Medium.otf", None),
    ],
    "sans_reg": [
        (os.path.join(FONT_DIR, "HelveticaNeue-Regular.ttf"), None),
        ("/System/Library/Fonts/HelveticaNeue.ttc", "regular"),
        ("/usr/share/fonts/opentype/inter/Inter-Regular.otf", None),
    ],
    "serif_italic": [
        (os.path.join(FONT_DIR, "Bodoni-Italic.ttf"), None),
        ("/System/Library/Fonts/Supplemental/Bodoni 72.ttc", "book italic"),
        (os.path.join(FONT_DIR, "bodoni-moda-latin-400-italic.woff"), None),
    ],
    "cap_sans": [(os.path.join(FONT_DIR, "Outfit-Bold.woff"), None)],
    "serif_bold": [
        (os.path.join(FONT_DIR, "Bodoni-Bold.ttf"), None),
        ("/System/Library/Fonts/Supplemental/Bodoni 72.ttc", "bold"),
        (os.path.join(FONT_DIR, "bodoni-moda-latin-500-normal.woff"), None),
    ],
}


def _pick_face(path, want_style):
    """Em .ttc escolhe o índice cujo estilo bate com want_style."""
    if not want_style:
        return 0
    best = None
    for i in range(32):
        try:
            f = ImageFont.truetype(path, 20, index=i)
        except OSError:
            break
        style = f.getname()[1].lower()
        if style == want_style:
            return i
        if best is None and want_style in style:
            best = i
    return best or 0


def resolve_font(kind):
    for path, style in FONT_CANDIDATES[kind]:
        if os.path.exists(path):
            return path, _pick_face(path, style)
    sys.exit(f"Nenhuma fonte encontrada para {kind}")


FONTS = {}


@lru_cache(maxsize=None)
def font(kind, size):
    path, index = FONTS[kind]
    # layout BASIC: as fontes Bodoni enviadas quebram no layout complexo (raqm)
    return ImageFont.truetype(path, int(size), index=index,
                              layout_engine=ImageFont.Layout.BASIC)


# ---------------------------------------------------------------- utilidades


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease_out_cubic(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ease_in_out(x):
    x = clamp(x)
    return 3 * x * x - 2 * x * x * x


def ease_out_back(x, s=1.7):
    x = clamp(x)
    return 1 + (s + 1) * (x - 1) ** 3 + s * (x - 1) ** 2


def with_alpha(img, a):
    if a >= 0.999:
        return img
    img = img.copy()
    img.putalpha(img.getchannel("A").point(lambda v: int(v * a)))
    return img


def paste(canvas, img, x, y):
    """alpha_composite que aceita posições parcialmente fora do quadro."""
    x, y = int(round(x)), int(round(y))
    l, t = max(0, -x), max(0, -y)
    r = min(img.width, canvas.width - x)
    b = min(img.height, canvas.height - y)
    if r <= l or b <= t:
        return
    canvas.alpha_composite(img.crop((l, t, r, b)), dest=(x + l, y + t))


def scaled(img, s):
    if abs(s - 1) < 0.002:
        return img
    return img.resize((max(1, int(img.width * s)), max(1, int(img.height * s))),
                      Image.BILINEAR)


def shadowed_text(text, fnt, fill=WHITE, shadow=0.6, blur=7, offset=3, pad=24):
    """Sprite de texto com sombra suave. Retorna (img, x_origem, baseline_y, avanço)."""
    asc, desc = fnt.getmetrics()
    adv = fnt.getlength(text)
    l, t, r, b = fnt.getbbox(text, anchor="ls")
    w = int(max(adv, r) - min(0, l)) + 2 * pad
    h = asc + desc + 2 * pad
    ox, base = pad - min(0, l), pad + asc
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    if shadow:
        sh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(sh).text((ox, base + offset), text, font=fnt, anchor="ls",
                                fill=(0, 0, 0, int(255 * shadow)))
        img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(blur)))
    ImageDraw.Draw(img).text((ox, base), text, font=fnt, anchor="ls", fill=fill)
    return img, ox, base, adv


# ---------------------------------------------------------------- legenda normal

STATIC_SIZE = 48
STATIC_MAX_W = 1080
STATIC_CENTER_Y = 835  # parede acima das duas pessoas


@lru_cache(maxsize=None)
def static_sprite(text):
    """Sempre uma linha só: reduz a fonte se a frase não couber."""
    size = STATIC_SIZE
    while font("sans_med", size).getlength(text) > STATIC_MAX_W:
        size -= 2
    return shadowed_text(text, font("sans_med", size), shadow=0.75, blur=7, offset=3)[0]


def draw_static(canvas, t):
    for start, end, text in script.STATIC_SUBS:
        if start - 0.06 <= t < end:
            a = min(clamp((t - start + 0.06) / 0.12), clamp((end - t) / 0.08))
            img = static_sprite(text)
            dy = (1 - ease_out_cubic((t - start + 0.06) / 0.2)) * 8
            paste(canvas, with_alpha(img, a), (W - img.width) / 2,
                  STATIC_CENTER_Y - img.height / 2 + dy)
            return


# ---------------------------------------------------------------- legenda dinâmica
#
# Estilo da referência: Outfit Bold branca, letras juntas, 1-3 palavras por vez
# em corte seco; frases de impacto viram blocos empilhados (pequena + grande).

DYN_CENTER_Y = 1450
DYN_ROLES = {  # papel: (fonte, tamanho, tracking)
    "n": ("cap_sans", 72, -2.5),
    "s": ("cap_sans", 56, -2.0),
    "b": ("cap_sans", 128, -5.0),
}


def role(name):
    """(fonte, tamanho, tracking) do papel, com os tamanhos do roteiro se houver."""
    kind, size, track = DYN_ROLES[name]
    new = getattr(script, "DYN_ROLE_SIZES", {}).get(name, size)
    return kind, new, track * new / size


def tracked_length(text, fnt, track):
    return sum(fnt.getlength(c) for c in text) + track * (len(text) - 1)


def draw_tracked(d, x, base, text, fnt, track, fill):
    if not track:
        d.text((x, base), text, font=fnt, anchor="ls", fill=fill)
        return
    for c in text:
        d.text((x, base), c, font=fnt, anchor="ls", fill=fill)
        x += fnt.getlength(c) + track


@lru_cache(maxsize=None)
def chunk_layout(ci):
    """Posição de cada palavra do bloco: lista de (linha, tempo, palavra, x, baseline)."""
    lines = script.DYNAMIC_CHUNKS[ci]
    widths, words_x = [], []
    for role_name, align, words in lines:
        kind, size, track = role(role_name)
        fnt = font(kind, size)
        space = fnt.getlength(" ") * 0.8
        xs, x = [], 0
        for _, w in words:
            xs.append(x)
            x += tracked_length(w, fnt, track) + space
        widths.append(x - space)
        words_x.append(xs)
    block_w = max(widths)
    left = (W - block_w) / 2

    bases, y = [], 0
    for i, (name, _, _) in enumerate(lines):
        size = role(name)[1]
        if i:
            y += size * 0.78 + role(lines[i - 1][0])[1] * 0.12
        bases.append(y)
    first_cap = role(lines[0][0])[1] * 0.72
    shift = DYN_CENTER_Y - (bases[-1] - first_cap) / 2 - bases[0]

    out = []
    for li, (name, align, words) in enumerate(lines):
        if align == "l":
            x0 = left
        elif align == "r":
            x0 = left + block_w - widths[li]
        else:
            x0 = (W - widths[li]) / 2
        for (t, w), wx in zip(words, words_x[li]):
            out.append((name, t, w, x0 + wx, bases[li] + shift))
    return out


def draw_dynamic(canvas, t):
    if any(m["start"] <= t < m["end"] for m in motions()):
        return  # nada de legenda por baixo do motion (nem no fade de saída)
    chunks = script.DYNAMIC_CHUNKS
    for ci, chunk in enumerate(chunks):
        start = chunk[0][2][0][0] - 0.03
        nxt = chunks[ci + 1][0][2][0][0] - 0.03 if ci + 1 < len(chunks) else 1e9
        for m in motions():
            if start < m["start"] < nxt:  # some antes do motion entrar
                nxt = m["start"] + 0.04
        for cut in getattr(script, "CAMERA", {}).get("cuts", []):
            if start < cut < nxt:  # não atravessa o corte para o próximo plano
                nxt = cut
        if not (start <= t < nxt):
            continue
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        placed = chunk_layout(ci)
        for name, ws, word, x, base in placed:
            if t < ws - 0.03:
                continue
            kind, size, track = role(name)
            draw_tracked(d, x, base, word, font(kind, size), track, WHITE + (255,))
        # sombra suave só onde há texto
        bbox = layer.getbbox()
        if not bbox:
            return
        pad = 30
        box = (max(0, bbox[0] - pad), max(0, bbox[1] - pad), min(W, bbox[2] + pad),
               min(H, bbox[3] + pad))
        crop = layer.crop(box)
        sh = Image.new("RGBA", crop.size, (0, 0, 0, 0))
        sh.putalpha(crop.getchannel("A").filter(ImageFilter.GaussianBlur(9)).point(
            lambda v: int(v * 0.55)))
        paste(canvas, sh, box[0], box[1] + 3)
        paste(canvas, crop, box[0], box[1])
        return


# ---------------------------------------------------------------- motion vinho
#
# Estilo da referência: fundo claro quadriculado, objeto central dentro de um
# círculo tracejado e texto grande com brilho — aqui em branco/creme e vinho.

CIRCLE_C = (W // 2, 790)
CIRCLE_R = 330
TEXT_LINE_Y = 1290  # baseline da primeira linha de texto
SS = 2


def bezier_path(segments, steps=40):
    """segments: ponto inicial seguido de tuplas (c1, c2, p) de cúbicas."""
    pts = [segments[0]]
    p0 = segments[0]
    for c1, c2, p in segments[1:]:
        for i in range(1, steps + 1):
            s = i / steps
            u = 1 - s
            pts.append((
                u ** 3 * p0[0] + 3 * u * u * s * c1[0] + 3 * u * s * s * c2[0] + s ** 3 * p[0],
                u ** 3 * p0[1] + 3 * u * u * s * c1[1] + 3 * u * s * s * c2[1] + s ** 3 * p[1],
            ))
        p0 = p
    return pts


TOOTH = bezier_path([
    (0.20, 0.10),
    ((0.32, 0.02), (0.42, 0.10), (0.50, 0.12)),
    ((0.58, 0.10), (0.68, 0.02), (0.80, 0.10)),
    ((0.95, 0.20), (0.92, 0.45), (0.84, 0.58)),
    ((0.80, 0.68), (0.80, 0.80), (0.76, 0.92)),
    ((0.73, 1.00), (0.65, 0.98), (0.63, 0.90)),
    ((0.60, 0.78), (0.57, 0.66), (0.50, 0.66)),
    ((0.43, 0.66), (0.40, 0.78), (0.37, 0.90)),
    ((0.35, 0.98), (0.27, 1.00), (0.24, 0.92)),
    ((0.20, 0.80), (0.20, 0.68), (0.16, 0.58)),
    ((0.08, 0.45), (0.05, 0.20), (0.20, 0.10)),
])

DROP = bezier_path([
    (0.50, 0.02),
    ((0.50, 0.02), (0.84, 0.42), (0.84, 0.63)),
    ((0.84, 0.84), (0.69, 1.00), (0.50, 1.00)),
    ((0.31, 1.00), (0.16, 0.84), (0.16, 0.63)),
    ((0.16, 0.42), (0.50, 0.02), (0.50, 0.02)),
])


@lru_cache(maxsize=None)
def motion_background():
    """Fundo creme com quadriculado fino e vinheta suave."""
    bg = Image.new("RGBA", (W, H), CREAM + (255,))
    d = ImageDraw.Draw(bg)
    step = 56
    x0 = (W // 2) % step
    for x in range(x0, W, step):
        d.line([(x, 0), (x, H)], fill=(196, 178, 180, 255), width=1)
    for y in range(0, H, step):
        d.line([(0, y), (W, y)], fill=(196, 178, 180, 255), width=1)
    bg = Image.blend(Image.new("RGBA", (W, H), CREAM + (255,)), bg, 0.45)
    # brilho branco no centro, bordas levemente mais quentes
    light = Image.new("L", (W, H), 0)
    ImageDraw.Draw(light).ellipse([-200, 250, W + 200, 1900], fill=255)
    light = light.filter(ImageFilter.GaussianBlur(260))
    bg = Image.composite(Image.blend(bg, Image.new("RGBA", (W, H), WHITE + (255,)), 0.55),
                         Image.blend(bg, Image.new("RGBA", (W, H), (236, 224, 218, 255)), 0.5),
                         light)
    return bg


def _shape_mask(pts, size):
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).polygon([(x * size, y * size) for x, y in pts], fill=255)
    return m


def _object_sprite(pts, size, top, bottom, rim, highlight_box):
    """Objeto “3D” simples: degradê, sombreado nas bordas, brilho e sombra."""
    ss = 3
    n = size * ss
    pad = 60 * ss
    mask = _shape_mask(pts, n)
    grad = Image.new("RGBA", (n, n))
    gd = ImageDraw.Draw(grad)
    for i in range(n):
        k = i / n
        gd.line([(0, i), (n, i)], fill=tuple(int(top[j] * (1 - k) + bottom[j] * k)
                                              for j in range(3)) + (255,))
    # sombreado nas bordas (volume)
    inner = mask.filter(ImageFilter.GaussianBlur(14 * ss))
    edge = ImageChops.subtract(mask, inner)
    grad = Image.composite(Image.new("RGBA", (n, n), rim + (255,)), grad,
                           edge.point(lambda v: int(v * 0.9)))
    # brilho
    hl = Image.new("L", (n, n), 0)
    x0, y0, x1, y1 = highlight_box
    ImageDraw.Draw(hl).ellipse([x0 * n, y0 * n, x1 * n, y1 * n], fill=200)
    hl = ImageChops.multiply(hl.filter(ImageFilter.GaussianBlur(10 * ss)), mask)
    grad = Image.composite(Image.new("RGBA", (n, n), WHITE + (255,)), grad, hl)
    grad.putalpha(mask)

    out = Image.new("RGBA", (n + 2 * pad, n + 2 * pad), (0, 0, 0, 0))
    shadow = Image.new("L", out.size, 0)
    shadow.paste(mask, (pad, pad + 22 * ss))
    shadow = shadow.filter(ImageFilter.GaussianBlur(22 * ss)).point(lambda v: int(v * 0.35))
    out.paste(Image.new("RGBA", out.size, (80, 20, 36, 255)), (0, 0), shadow)
    out.alpha_composite(grad, (pad, pad))
    return out.resize((out.width // ss, out.height // ss), Image.LANCZOS)


@lru_cache(maxsize=None)
def tooth_sprite():
    return _object_sprite(TOOTH, 380, (255, 253, 250), (236, 226, 220), (205, 188, 184),
                          (0.22, 0.12, 0.45, 0.32))


@lru_cache(maxsize=None)
def drop_sprite():
    return _object_sprite(DROP, 330, (186, 60, 84), (96, 14, 34), (70, 8, 24),
                          (0.30, 0.42, 0.42, 0.70))


def draw_dashed_circle(canvas, t, progress, alpha):
    """Círculo tracejado que se desenha e gira devagar."""
    pad = 10
    size = (CIRCLE_R + pad) * 2
    img = Image.new("RGBA", (size * SS, size * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r = CIRCLE_R * SS
    c = size * SS / 2
    n = 72
    rot = t * 9
    for i in range(int(n * progress)):
        a0 = rot + i * 360 / n
        d.arc([c - r, c - r, c + r, c + r], a0, a0 + 2.6, fill=WINE_DEEP + (int(220 * alpha),),
              width=3 * SS)
    img = img.resize((size, size), Image.LANCZOS)
    paste(canvas, img, CIRCLE_C[0] - size / 2, CIRCLE_C[1] - size / 2)


def draw_object(canvas, sprite, t, scale, alpha):
    if alpha <= 0 or scale <= 0.01:
        return
    img = with_alpha(scaled(sprite, scale), alpha)
    bob = math.sin(t * 2.4) * 8
    paste(canvas, img, CIRCLE_C[0] - img.width / 2, CIRCLE_C[1] - img.height / 2 + bob)


def draw_caries_spot(canvas, t, t0, scale, alpha):
    k = clamp((t - t0) / 0.3)
    if k <= 0 or alpha <= 0:
        return
    bob = math.sin(t * 2.4) * 8
    px = CIRCLE_C[0] + 0.14 * 380 * scale
    py = CIRCLE_C[1] - 0.27 * 380 * scale + bob
    pad = 70
    layer = Image.new("RGBA", (pad * 2 * SS, pad * 2 * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    c = pad * SS
    r = 15 * SS * ease_out_back(k)
    d.ellipse([c - r, c - r * 0.8, c + r, c + r * 0.8], fill=WINE_DEEP + (int(235 * alpha),))
    pulse = ((t - t0) % 1.0) / 1.0
    pr = r + pulse * 46 * SS
    d.ellipse([c - pr, c - pr, c + pr, c + pr],
              outline=WINE + (int(200 * (1 - pulse) * alpha * k),), width=3 * SS)
    layer = layer.resize((pad * 2, pad * 2), Image.LANCZOS)
    paste(canvas, layer, px - pad, py - pad)


def text_words(items):
    """(tempo, palavra) -> lista de (tempo, texto, fonte, avanço)."""
    out = []
    for ws, word in items:
        if word.startswith("*"):
            fnt, txt = font("serif_italic", 66), word[1:]
        else:
            fnt, txt = font("sans_reg", 50), word
        out.append((ws, txt, fnt, fnt.getlength(txt)))
    return out


def draw_word_line(canvas, items, t, base, alpha, color=INK):
    words = text_words(items)
    space = font("sans_reg", 50).getlength(" ")
    total = sum(w[3] for w in words) + space * (len(words) - 1)
    x = (W - total) / 2
    layer = Image.new("RGBA", (W, 160), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for ws, txt, fnt, adv in words:
        k = ease_out_cubic((t - ws + 0.05) / 0.3)
        if k > 0:
            col = WINE if fnt is font("serif_italic", 66) else color
            d.text((x, 110 + (1 - k) * 22), txt, font=fnt, anchor="ls",
                   fill=col + (int(255 * k * alpha),))
        x += adv + space
    paste(canvas, layer, 0, base - 110)


def draw_glow_word(canvas, ws, text, t, base, alpha, size=190):
    """Palavra grande em Bodoni Bold vinho, letra por letra, com brilho."""
    fnt = font("serif_bold", size)
    total = fnt.getlength(text)
    x0 = (W - total) / 2
    lh = int(size * 1.6)
    layer = Image.new("RGBA", (W, lh), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    by = int(size * 1.05)
    any_drawn = False
    for i, ch in enumerate(text):
        k = ease_out_cubic((t - ws - i * 0.035) / 0.35)
        if k <= 0:
            continue
        any_drawn = True
        x = x0 + fnt.getlength(text[:i])
        d.text((x, by + (1 - k) * 40), ch, font=fnt, anchor="ls",
               fill=WINE + (int(255 * k * alpha),))
    if not any_drawn:
        return
    glow = layer.getchannel("A").filter(ImageFilter.GaussianBlur(26)).point(
        lambda v: int(min(255, v * 1.4)))
    halo = Image.new("RGBA", layer.size, WINE_LIGHT + (0,))
    halo.putalpha(glow.point(lambda v: int(v * 0.55)))
    paste(canvas, halo, 0, base - by)
    paste(canvas, layer, 0, base - by)


def draw_label(canvas, text, t, t0, alpha):
    k = ease_out_cubic((t - t0) / 0.4) * alpha
    if k <= 0:
        return
    fnt = font("sans_med", 26)
    spacing = 8
    total = sum(fnt.getlength(c) for c in text) + spacing * (len(text) - 1)
    layer = Image.new("RGBA", (W, 60), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    x = (W - total) / 2
    for ch in text:
        d.text((x, 40), ch, font=fnt, anchor="ls", fill=WINE + (int(210 * k),))
        x += fnt.getlength(ch) + spacing
    paste(canvas, layer, 0, CIRCLE_C[1] - CIRCLE_R - 110)


def motions():
    return getattr(script, "MOTIONS", [])


@lru_cache(maxsize=None)
def implant_sprite():
    """Implante: coroa (parte de cima do dente) sobre um parafuso metálico."""
    size, pad = 380, 60
    crown = [(x, y) for x, y in TOOTH if y <= 0.56]
    screw = [(0.36, 0.50), (0.64, 0.50), (0.61, 0.93), (0.50, 1.02), (0.39, 0.93)]
    img = _object_sprite(screw, size, (232, 232, 236), (136, 138, 148), (104, 106, 116),
                         (0.40, 0.55, 0.47, 0.90))
    img.alpha_composite(_object_sprite(crown, size, (255, 253, 250), (236, 226, 220),
                                       (205, 188, 184), (0.22, 0.12, 0.45, 0.32)))
    d = ImageDraw.Draw(img)
    for i in range(7):  # roscas
        y = 0.60 + i * 0.055
        half = 0.14 - (y - 0.55) * 0.12
        d.line([(pad + (0.5 - half) * size, pad + y * size),
                (pad + (0.5 + half) * size, pad + (y + 0.02) * size)],
               fill=(96, 98, 108, 200), width=4)
    return img


@lru_cache(maxsize=None)
def tooth_outline():
    """Contorno tracejado do dente (para o “dente perdido”)."""
    size, pad, ss = 380, 60, 2
    n = (size + 2 * pad) * ss
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pts = [((pad + x * size) * ss, (pad + y * size) * ss) for x, y in TOOTH]
    for i in range(0, len(pts) - 1):
        if (i // 6) % 2 == 0:
            d.line([pts[i], pts[i + 1]], fill=WINE_DEEP + (220,), width=4 * ss)
    return img.resize((n // ss, n // ss), Image.LANCZOS)


def draw_icon(layer, phase, t, t_in, t_out):
    """Ícone da fase: entra com “pop” em t_in e sai em t_out."""
    out = ease_in_out((t - t_out) / 0.25) if t_out else 0.0
    s = ease_out_back((t - t_in) / 0.5) * (1 - 0.4 * out)
    a = clamp((t - t_in) / 0.2) * (1 - out)
    icon = phase.get("icon", "tooth")
    if icon == "lost":  # dente que some e vira só o contorno tracejado
        k = ease_in_out((t - phase["lose"]) / 0.45)
        draw_object(layer, tooth_outline(), t, s, a * k)
        draw_object(layer, tooth_sprite(), t, s, a * (1 - 0.85 * k))
    else:
        sprite = {"tooth": tooth_sprite, "drop": drop_sprite, "implant": implant_sprite}[icon]
        draw_object(layer, sprite(), t, s, a)
    if "spot" in phase:
        draw_caries_spot(layer, t, phase["spot"], s, a)


def draw_signals(layer, m, t):
    """Duas fases (ícone + linha + palavra grande com brilho)."""
    t0, sw = m["start"], m["switch"]
    p1, p2 = m["phase1"], m["phase2"]
    draw_icon(layer, p1, t, t0 + 0.2, sw)
    if t >= sw:
        draw_icon(layer, p2, t, sw + 0.1, None)
    for phase, t_in, a in ((p1, t0 + 0.3, 1 - ease_in_out((t - sw) / 0.2)),
                           (p2, sw + 0.1, clamp((t - sw) / 0.2) if t >= sw else 0.0)):
        if a <= 0:
            continue
        draw_label(layer, phase["label"], t, t_in, a)
        draw_word_line(layer, phase["line"], t, TEXT_LINE_Y, a)
        big_y = TEXT_LINE_Y + 230
        if "line2" in phase:
            draw_word_line(layer, phase["line2"], t, TEXT_LINE_Y + 78, a)
            big_y = TEXT_LINE_Y + 300
        draw_glow_word(layer, phase["big"][0], phase["big"][1], t, big_y, a)


def draw_glow_text(canvas, parts, base, alpha):
    """Texto centralizado em vinho com brilho. parts: [(texto, fonte), ...]."""
    total = sum(f.getlength(txt) for txt, f in parts)
    lh = 420
    by = 300
    layer = Image.new("RGBA", (W, lh), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    x = (W - total) / 2
    for txt, f in parts:
        d.text((x, by), txt, font=f, anchor="ls", fill=WINE + (int(255 * alpha),))
        x += f.getlength(txt)
    glow = layer.getchannel("A").filter(ImageFilter.GaussianBlur(26)).point(
        lambda v: int(min(255, v * 1.4)))
    halo = Image.new("RGBA", layer.size, WINE_LIGHT + (0,))
    halo.putalpha(glow.point(lambda v: int(v * 0.55)))
    paste(canvas, halo, 0, base - by)
    paste(canvas, layer, 0, base - by)


def draw_counter(layer, m, t):
    """Número que conta até o valor (estilo da referência) + linhas de texto."""
    t0 = m["start"]
    draw_icon(layer, {"icon": m.get("icon", "tooth")}, t, t0 + 0.2, None)
    draw_label(layer, m["label"], t, m.get("label_at", t0 + 0.2), 1.0)
    nt, value = m["number"]
    k = clamp((t - nt + 0.05) / 0.7)
    if k > 0:
        n = round(value * ease_out_cubic(k))
        parts = [(str(n), font("serif_bold", 300))]
        ut, unit = m["unit"]
        ku = clamp((t - ut + 0.05) / 0.25)
        if ku > 0:
            parts.append((" " + unit, font("serif_italic", 130)))
        rise = (1 - ease_out_cubic(k * 2)) * 40
        draw_glow_text(layer, parts, TEXT_LINE_Y + 60 + rise, clamp(k * 3))
    draw_word_line(layer, m["line"], t, TEXT_LINE_Y + 200, 1.0)
    if "line2" in m:
        draw_word_line(layer, m["line2"], t, TEXT_LINE_Y + 278, 1.0)


def draw_motion(canvas, t):
    for m in motions():
        t0, t1 = m["start"], m["end"]
        if not (t0 <= t < t1):
            continue
        layer = motion_background().copy()
        draw_dashed_circle(layer, t, ease_in_out((t - t0 - 0.15) / 0.7), 1.0)
        if m.get("kind", "signals") == "counter":
            draw_counter(layer, m, t)
        else:
            draw_signals(layer, m, t)

        # entrada: revela em círculo a partir do centro; saída: fade
        k_in = ease_in_out((t - t0) / 0.4)
        if k_in < 1:
            mask = Image.new("L", (W, H), 0)
            r = k_in * math.hypot(W, H)
            cx, cy = CIRCLE_C
            ImageDraw.Draw(mask).ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
            layer.putalpha(ImageChops.multiply(layer.getchannel("A"), mask))
        a_out = 1 - ease_in_out((t - (t1 - 0.3)) / 0.3)
        canvas.alpha_composite(with_alpha(layer, a_out))
        return


# ---------------------------------------------------------------- câmera
#
# Zoom lento dentro de cada trecho, "punch-in" seco (outro ângulo) nas trocas
# de frase e, nos cortes de cena, uma entrada leve com zoom e desfoque.


def camera(frame, t):
    cam = getattr(script, "CAMERA", None)
    if not cam:
        return frame
    cuts, punches = cam["cuts"], cam["punch_ins"]
    marks = sorted([0.0] + cuts + punches + [1e9])
    a = max(m for m in marks if m <= t)
    b = min(m for m in marks if m > t)
    zoom = cam["punch_zoom"] if a in punches else 1.0
    if b < 1e8:
        zoom *= 1 + cam["drift"] * (t - a) / (b - a)
    blur = 0.0
    if a in cuts and t - a < 0.3:
        k = ease_out_cubic((t - a) / 0.3)
        zoom *= 1 + cam.get("cut_zoom", 0.09) * (1 - k)
        blur = cam.get("cut_blur", 7) * (1 - k)
    ax, ay = [p for t0, p in cam["anchor"] if t0 <= t][-1]
    cw, ch = W / zoom, H / zoom
    x0, y0 = ax * (W - cw), ay * (H - ch)
    out = frame.resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch))
    if blur > 0.4:
        out = out.filter(ImageFilter.GaussianBlur(blur))
    return out


# ---------------------------------------------------------------- render


def render_frame(t):
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if t < getattr(script, "SCENE_CUT", 0):
        draw_static(canvas, t)
    else:
        draw_dynamic(canvas, t)
        draw_motion(canvas, t)
    return canvas


def probe_frames(path):
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets",
        "-show_entries", "stream=nb_read_packets", "-of", "csv=p=0", path])
    return int(out.strip())


def cut_filter(duration):
    """Overlay das legendas + remoção dos trechos em script.CUTS (vídeo e áudio)."""
    keep, pos = [], 0.0
    for c0, c1 in sorted(getattr(script, "CUTS", [])):
        keep.append((pos, c0))
        pos = c1
    keep.append((pos, duration))
    n = len(keep)
    parts = ["[0:v][1:v]overlay=0:0:format=auto,format=yuv420p,"
             f"split={n}" + "".join(f"[vs{i}]" for i in range(n)),
             f"[0:a]asplit={n}" + "".join(f"[as{i}]" for i in range(n))]
    for i, (k0, k1) in enumerate(keep):
        fade = 0.012  # evita estalo nas emendas do áudio
        parts.append(f"[vs{i}]trim={k0}:{k1},setpts=PTS-STARTPTS[v{i}]")
        parts.append(f"[as{i}]atrim={k0}:{k1},asetpts=PTS-STARTPTS,"
                     f"afade=t=in:d={fade},afade=t=out:st={k1 - k0 - fade}:d={fade}[a{i}]")
    parts.append("".join(f"[v{i}][a{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=1[v][a]")
    return ";".join(parts)


def render_with_camera(src, dst, n):
    """Quadros do vídeo passam pela câmera em Python antes de receber a legenda."""
    if getattr(script, "CUTS", None):
        sys.exit("CUTS com CAMERA ainda não é suportado")
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", src, "-f", "rawvideo",
                            "-pix_fmt", "rgba", "-"], stdout=subprocess.PIPE)
    enc = subprocess.Popen([
        "ffmpeg", "-v", "error", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-i", src, "-map", "0:v", "-map", "1:a?", "-c:v", "libx264", "-crf", "17",
        "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-movflags", "+faststart", dst], stdin=subprocess.PIPE)
    size = W * H * 4
    for i in range(n):
        buf = dec.stdout.read(size)
        if len(buf) < size:
            break
        t = i / FPS
        frame = camera(Image.frombytes("RGBA", (W, H), buf), t)
        frame.alpha_composite(render_frame(t))
        enc.stdin.write(frame.tobytes())
        if i % 60 == 0:
            print(f"\r{i}/{n}", end="", flush=True)
    enc.stdin.close()
    enc.wait()
    dec.wait()
    print(f"\rpronto: {dst}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--script", default="aura_reels4",
                    help="roteiro em video_captions/ (ex.: aura_implante)")
    ap.add_argument("--preview", type=float, nargs="*",
                    help="só salva JPGs desses instantes (segundos) ao lado da saída")
    args = ap.parse_args()

    global script
    script = importlib.import_module(f"{__package__}.{args.script}")

    for kind in FONT_CANDIDATES:
        FONTS[kind] = resolve_font(kind)
        print(f"fonte {kind}: {FONTS[kind][0]} [{FONTS[kind][1]}]")

    if args.preview:
        base = os.path.splitext(args.output)[0]
        for t in args.preview:
            frame = subprocess.check_output([
                "ffmpeg", "-v", "error", "-ss", str(t), "-i", args.input, "-frames:v", "1",
                "-f", "rawvideo", "-pix_fmt", "rgba", "-"])
            bg = camera(Image.frombytes("RGBA", (W, H), frame), t)
            bg.alpha_composite(render_frame(t))
            bg.convert("RGB").save(f"{base}_{t:05.2f}.jpg", quality=90)
        return

    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg não encontrado")
    n = probe_frames(args.input)
    if getattr(script, "CAMERA", None):
        render_with_camera(args.input, args.output, n)
        return
    cmd = [
        "ffmpeg", "-v", "error", "-y", "-i", args.input,
        "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-filter_complex", cut_filter(n / FPS),
        "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-crf", "17", "-preset", "medium",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", args.output,
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(n):
        proc.stdin.write(render_frame(i / FPS).tobytes())
        if i % 60 == 0:
            print(f"\r{i}/{n}", end="", flush=True)
    proc.stdin.close()
    proc.wait()
    print(f"\rpronto: {args.output}")


if __name__ == "__main__":
    main()
