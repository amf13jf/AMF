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
    center = getattr(script, "DYN_CENTER_Y", DYN_CENTER_Y)
    shift = center - (bases[-1] - first_cap) / 2 - bases[0]

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
    if any(n["start"] <= t < n["end"] for n in getattr(script, "NAMETAGS", [])):
        return  # a plaquinha de nome já diz o que ela está falando
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
        out.append((ws, txt, fnt, safe_length(fnt, txt)))
    return out


def safe_length(fnt, txt):
    """Largura somando letra a letra (ignora pares de kerning quebrados da Bodoni)."""
    return sum(fnt.getlength(ch) for ch in txt)


def draw_safe(d, xy, txt, fnt, fill):
    x, y = xy
    for ch in txt:
        d.text((x, y), ch, font=fnt, anchor="ls", fill=fill)
        x += fnt.getlength(ch)


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
            draw_safe(d, (x, 110 + (1 - k) * 22), txt, fnt, col + (int(255 * k * alpha),))
        x += adv + space
    paste(canvas, layer, 0, base - 110)


def draw_glow_word(canvas, ws, text, t, base, alpha, size=190, stagger=0.035, dur=0.35):
    """Palavra grande em Bodoni Bold vinho, letra por letra, com brilho."""
    fnt = font("serif_bold", size)
    # posições letra a letra sem kerning: a Bodoni enviada tem um par "te" quebrado
    adv = [0.0]
    for ch in text:
        adv.append(adv[-1] + fnt.getlength(ch))
    total = adv[-1]
    x0 = (W - total) / 2
    lh = int(size * 1.6)
    layer = Image.new("RGBA", (W, lh), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    by = int(size * 1.05)
    any_drawn = False
    for i, ch in enumerate(text):
        k = ease_out_cubic((t - ws - i * stagger) / dur)
        if k <= 0:
            continue
        any_drawn = True
        x = x0 + adv[i]
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
    total = sum(safe_length(f, txt) for txt, f in parts)
    lh = 420
    by = 300
    layer = Image.new("RGBA", (W, lh), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    x = (W - total) / 2
    for txt, f in parts:
        draw_safe(d, (x, by), txt, f, WINE + (int(255 * alpha),))
        x += safe_length(f, txt)
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


def partial(pts, frac):
    """Pedaço inicial de uma linha poligonal (para desenhar traços aos poucos)."""
    if frac >= 1:
        return pts
    lens = [math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    goal, acc, out = sum(lens) * clamp(frac), 0.0, [pts[0]]
    for i, ln in enumerate(lens):
        if acc + ln >= goal:
            k = (goal - acc) / ln if ln else 0
            out.append((pts[i][0] + (pts[i + 1][0] - pts[i][0]) * k,
                        pts[i][1] + (pts[i + 1][1] - pts[i][1]) * k))
            return out
        acc += ln
        out.append(pts[i + 1])
    return out


def draw_check(layer, cx, cy, t0, t, r=44, cross=False):
    """Círculo vinho que se desenha + check creme (ou um X cinza, para o “não”)."""
    k = ease_out_back((t - t0) / 0.35)
    if k <= 0:
        return
    pad = r + 12
    img = Image.new("RGBA", (pad * 2 * SS, pad * 2 * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c, rr = pad * SS, r * SS * min(k, 1.15)
    d.ellipse([c - rr, c - rr, c + rr, c + rr], fill=((120, 110, 112) if cross else WINE) + (255,))
    ck = ease_in_out((t - t0 - 0.15) / 0.3)
    if ck > 0 and cross:
        q = 0.36 * rr
        for (x1, y1, x2, y2), kk in (((c - q, c - q, c + q, c + q), clamp(ck * 2)),
                                     ((c + q, c - q, c - q, c + q), clamp(ck * 2 - 1))):
            if kk > 0:
                d.line([(x1, y1), (x1 + (x2 - x1) * kk, y1 + (y2 - y1) * kk)],
                       fill=CREAM + (255,), width=int(8 * SS))
    elif ck > 0:
        pts = [(c - 0.45 * rr, c + 0.02 * rr), (c - 0.12 * rr, c + 0.34 * rr),
               (c + 0.48 * rr, c - 0.30 * rr)]
        seg = partial(pts, ck)
        d.line(seg, fill=CREAM + (255,), width=int(8 * SS), joint="curve")
        for x, y in (seg[0], seg[-1]):
            d.ellipse([x - 4 * SS, y - 4 * SS, x + 4 * SS, y + 4 * SS], fill=CREAM + (255,))
    img = img.resize((pad * 2, pad * 2), Image.LANCZOS)
    paste(layer, img, cx - pad, cy - pad)


def draw_checklist(layer, m, t):
    """Título + palavra grande com brilho + itens que ganham check na hora da fala."""
    if m.get("big"):
        draw_word_line(layer, m["title"], t, 620, 1.0)
        ws, big = m["big"]
        draw_glow_word(layer, ws, big, t, 880, 1.0, size=210)
        top = 1210
    else:  # sem palavra grande: título maior e itens mais para cima
        draw_word_line(layer, m["title"], t, 720, 1.0)
        top = 1010
    marks = m.get("marks", ["check"] * len(m["items"]))
    for n, item in enumerate(m["items"]):
        t0 = item[0][0]
        y = top + n * 240
        k = ease_out_cubic((t - t0 + 0.05) / 0.35)
        if k <= 0:
            continue
        x0 = 150 + (1 - k) * 80
        draw_check(layer, x0 + 52, y - 30, t0, t, r=52, cross=marks[n] == "cross")
        row = Image.new("RGBA", (W, 200), (0, 0, 0, 0))
        d = ImageDraw.Draw(row)
        x = x0 + 136
        for _, word in item:
            key = word.startswith("*")
            fnt = font("serif_italic", 104) if key else font("sans_reg", 72)
            txt = word[1:] if key else word
            draw_safe(d, (x, 130), txt, fnt, (WINE if key else INK) + (int(255 * k),))
            x += safe_length(fnt, txt + " ")
        paste(layer, row, 0, y - 130)


# ---------------------------------------------------------------- maçã


APPLE_R = 245  # raio da maçã (px, na tela)


def _apple_outline(r, n=240):
    """Silhueta de maçã: covinha em cima, base levemente achatada."""
    pts = []
    for i in range(n):
        th = 2 * math.pi * i / n  # 0 = topo, sentido horário
        rr = 1 + 0.07 * math.cos(2 * th) + 0.05 * math.cos(th)
        rr -= 0.20 * math.exp(-((th if th < math.pi else th - 2 * math.pi) ** 2) / 0.06)
        rr -= 0.06 * math.exp(-((th - math.pi) ** 2) / 0.12)
        pts.append((r * rr * math.sin(th), -r * rr * math.cos(th)))
    return pts


def _bite_circles(r, ang, prog):
    """Mordida: círculo grande na borda + “dentes” (circulinhos) no contorno."""
    a = math.radians(ang)
    cx, cy = 1.02 * r * math.sin(a), -1.02 * r * math.cos(a)
    big = 0.30 * r * prog
    circles = [(cx, cy, big)]
    if prog > 0.3:
        for k in range(-3, 4):  # marcas dos dentes voltadas para dentro da maçã
            b = a + math.pi + math.radians(k * 24)
            circles.append((cx + big * math.sin(b), cy - big * math.cos(b), 0.075 * r * prog))
    return circles


@lru_cache(maxsize=64)
def apple_sprite(angle_q, bites_q):
    """Maçã girada em `angle_q` graus com as mordidas `bites_q` ((ângulo, progresso), ...)."""
    r = APPLE_R * SS
    size = int(r * 3.2)
    c = size / 2
    body = Image.new("L", (size, size), 0)
    ImageDraw.Draw(body).polygon([(c + x, c + y) for x, y in _apple_outline(r)], fill=255)
    bite = Image.new("L", (size, size), 0)
    flesh = Image.new("L", (size, size), 0)
    db, df = ImageDraw.Draw(bite), ImageDraw.Draw(flesh)
    for ang, prog in bites_q:
        for x, y, rr in _bite_circles(r, ang, prog):
            db.ellipse([c + x - rr, c + y - rr, c + x + rr, c + y + rr], fill=255)
            e = rr + 0.06 * r
            df.ellipse([c + x - e, c + y - e, c + x + e, c + y + e], fill=255)
    # cor: vermelho da maçã em degradê + polpa creme na borda da mordida
    red = Image.new("RGBA", (size, size))
    rd = ImageDraw.Draw(red)
    for i in range(size):
        k = i / size
        rd.line([(0, i), (size, i)], fill=(int(205 - 70 * k), int(36 - 18 * k), int(52 - 22 * k), 255))
    img = Image.composite(Image.new("RGBA", (size, size), (250, 238, 206, 255)), red,
                          ImageChops.multiply(flesh, body))
    alpha = ImageChops.subtract(body, bite)
    img.putalpha(alpha)
    # cabinho e folha (giram junto)
    d = ImageDraw.Draw(img)
    top = (c, c - r * 0.80)
    d.line([top, (c + r * 0.06, c - r * 1.12)], fill=(96, 62, 40, 255), width=int(r * 0.07))
    leaf = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(leaf).ellipse([c + r * 0.08, c - r * 1.22, c + r * 0.62, c - r * 1.0],
                                 fill=(112, 150, 74, 255))
    leaf = leaf.rotate(-28, center=(c + r * 0.08, c - r * 1.1), resample=Image.BICUBIC)
    img.alpha_composite(leaf)
    img = img.rotate(-angle_q, center=(c, c), resample=Image.BICUBIC)
    # luz fixa (não gira): volume nas bordas + brilho no alto à esquerda
    a = img.getchannel("A")
    edge = ImageChops.subtract(a, a.filter(ImageFilter.GaussianBlur(r * 0.12)))
    img = Image.composite(Image.new("RGBA", (size, size), (70, 8, 20, 255)), img,
                          edge.point(lambda v: int(v * 0.55)))
    hl = Image.new("L", (size, size), 0)
    ImageDraw.Draw(hl).ellipse([c - r * 0.62, c - r * 0.62, c - r * 0.22, c - r * 0.12], fill=170)
    hl = ImageChops.multiply(hl.filter(ImageFilter.GaussianBlur(r * 0.1)), a)
    img = Image.composite(Image.new("RGBA", (size, size), (255, 255, 255, 255)), img, hl)
    img.putalpha(a)
    # sombra
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    sh = Image.new("L", (size, size), 0)
    ImageDraw.Draw(sh).ellipse([c - r * 0.8, c + r * 0.95, c + r * 0.8, c + r * 1.15], fill=90)
    out.paste(Image.new("RGBA", (size, size), (80, 20, 36, 255)), (0, 0),
              sh.filter(ImageFilter.GaussianBlur(r * 0.12)))
    out.alpha_composite(img)
    return out.resize((size // SS, size // SS), Image.LANCZOS)


APPLE_PHOTO = os.path.join(HERE, "assets", "maca_mordida.png")


@lru_cache(maxsize=None)
def apple_photo_base():
    """Foto da maçã recortada, ampliada para o tamanho do motion."""
    img = Image.open(APPLE_PHOTO).convert("RGBA")
    h = int(APPLE_R * 2.35)
    w = int(img.width * h / img.height)
    img = img.resize((w, h), Image.LANCZOS).filter(ImageFilter.UnsharpMask(2, 60, 2))
    img.putalpha(img.getchannel("A").filter(ImageFilter.MinFilter(3)))  # tira a franja branca
    # textura da polpa, tirada da mordida que já existe na foto (lado esquerdo)
    flesh = img.crop((int(w * 0.05), int(h * 0.50), int(w * 0.16), int(h * 0.74))).convert("RGB")
    return img, flesh


@lru_cache(maxsize=64)
def apple_photo_sprite(angle_q, bites_q):
    """Foto da maçã + mordidas novas no mesmo estilo da original: um “gomo” liso
    tirado da borda, com a polpa à mostra (textura copiada da própria foto)."""
    base, flesh = apple_photo_base()
    w, h = base.size
    pad = int(w * 0.3)
    size = (w + 2 * pad, h + 2 * pad)
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    img.alpha_composite(base, (pad, pad))
    cx, cy = pad + w * 0.52, pad + h * 0.60  # centro do corpo da maçã
    r = w * 0.47
    face = Image.new("L", size, 0)   # onde aparece a polpa
    cut = Image.new("L", size, 0)    # o que sai da silhueta
    rim = Image.new("L", size, 0)    # contorno escuro entre casca e polpa
    df, dc, dr = ImageDraw.Draw(face), ImageDraw.Draw(cut), ImageDraw.Draw(rim)
    def blob(x0, y0, rad, seed):
        """Círculo com borda levemente irregular (marca natural da mordida)."""
        pts = []
        for i in range(90):
            th = 2 * math.pi * i / 90
            k = 1 + 0.045 * math.sin(5 * th + seed) + 0.03 * math.sin(11 * th + 2 * seed)
            pts.append((x0 + rad * k * math.cos(th), y0 + rad * k * math.sin(th)))
        return pts

    for n, (ang, prog) in enumerate(bites_q):
        a = math.radians(ang)
        ux, uy = math.sin(a), -math.cos(a)
        rad = 0.46 * r * ease_out_cubic(prog)
        fx, fy = cx + ux * 0.98 * r, cy + uy * 0.98 * r      # área da polpa
        gx, gy = fx + ux * 0.36 * r, fy + uy * 0.36 * r      # parte que sai da silhueta
        poly = blob(fx, fy, rad, n * 1.7)
        df.polygon(poly, fill=255)
        dr.line(poly + poly[:1], fill=255, width=max(1, int(r * 0.03)))
        dc.polygon(blob(gx, gy, rad * 1.02, n * 2.3 + 1), fill=255)
    a_ch = img.getchannel("A")
    tex = flesh.resize((int(r * 0.7), int(r * 1.1)), Image.BICUBIC)
    tile = Image.new("RGB", size)
    for yy in range(0, size[1], tex.height):
        for xx in range(0, size[0], tex.width):
            tile.paste(tex if (xx // tex.width + yy // tex.height) % 2 == 0
                       else tex.transpose(Image.FLIP_LEFT_RIGHT), (xx, yy))
    face_m = ImageChops.multiply(face.filter(ImageFilter.GaussianBlur(1.2)), a_ch)
    img = Image.composite(tile.convert("RGBA"), img, face_m)
    rim_m = ImageChops.multiply(rim.filter(ImageFilter.GaussianBlur(1.5)), a_ch)
    img = Image.composite(Image.new("RGBA", size, (150, 70, 40, 255)), img,
                          rim_m.point(lambda v: int(v * 0.6)))
    img.putalpha(ImageChops.subtract(a_ch, cut.filter(ImageFilter.GaussianBlur(0.8))))
    img = img.rotate(-angle_q, center=(cx, cy), resample=Image.BICUBIC)
    out = Image.new("RGBA", size, (0, 0, 0, 0))
    sh = Image.new("L", size, 0)
    ImageDraw.Draw(sh).ellipse([cx - r * 0.85, cy + r * 1.0, cx + r * 0.85, cy + r * 1.22], fill=80)
    out.paste(Image.new("RGBA", size, (80, 20, 36, 255)), (0, 0),
              sh.filter(ImageFilter.GaussianBlur(r * 0.12)))
    out.alpha_composite(img)
    # recentra no centro do corpo da maçã (draw_object centraliza a imagem)
    dx, dy = int(size[0] / 2 - cx), int(size[1] / 2 - cy)
    return ImageChops.offset(out, dx, dy)


def draw_apple(layer, m, t):
    """Maçã girando e ganhando mordidas na hora da fala + texto do gancho."""
    t0 = m["start"]
    angle = m.get("spin", 40) * (t - t0) - 20
    bites = []
    squash = 1.0
    for ang, bt in m["bites"]:
        p = clamp((t - bt) / 0.14)
        if p > 0:
            bites.append((ang, round(p, 2)))
        if 0 <= t - bt < 0.3:
            squash = min(squash, 1 - 0.05 * math.sin(math.pi * (t - bt) / 0.3))
    sprite = (apple_photo_sprite if m.get("photo") else apple_sprite)(round(angle, 1),
                                                                       tuple(bites))
    pop = ease_out_back((t - t0 - 0.1) / 0.5) * squash
    draw_object(layer, sprite, t, pop, clamp((t - t0) / 0.25))
    draw_word_line(layer, m["line"], t, TEXT_LINE_Y, 1.0)
    draw_word_line(layer, m["line2"], t, TEXT_LINE_Y + 78, 1.0)
    ws, big = m["big"]
    draw_glow_word(layer, ws, big, t, TEXT_LINE_Y + 300, 1.0, stagger=0.015, dur=0.2)


# ---------------------------------------------------------------- plaquinha de nome


def draw_nametags(canvas, t):
    for tag in getattr(script, "NAMETAGS", []):
        t0, t1 = tag["start"], tag["end"]
        if not (t0 <= t < t1):
            continue
        k_in = ease_out_cubic((t - t0) / 0.45)
        k_out = ease_in_out((t - (t1 - 0.3)) / 0.3)
        name_f, sub_f = font("cap_sans", 66), font("sans_med", 30)
        sub = tag["sub"].upper()
        sub_w = sum(sub_f.getlength(ch) + 5 for ch in sub)
        w = int(max(name_f.getlength(tag["name"]), sub_w) + 110)
        h = 176
        x0, y0 = 70, tag.get("y", 1560)
        box = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
        d = ImageDraw.Draw(box)
        d.rounded_rectangle([0, 0, w * SS - 1, h * SS - 1], radius=26 * SS, fill=WINE + (238,))
        d.rounded_rectangle([0, 0, 10 * SS, h * SS - 1], radius=5 * SS, fill=CREAM + (255,))
        box = box.resize((w, h), Image.LANCZOS)
        d = ImageDraw.Draw(box)
        d.text((52, 86), tag["name"], font=name_f, anchor="ls", fill=WHITE + (255,))
        x = 54
        for ch in sub:
            d.text((x, 136), ch, font=sub_f, anchor="ls", fill=CREAM + (220,))
            x += sub_f.getlength(ch) + 5
        reveal = int(w * k_in)  # entra como uma cortina da esquerda para a direita
        if reveal <= 0:
            continue
        box = box.crop((0, 0, reveal, h))
        paste(canvas, with_alpha(box, 1 - k_out), x0, y0 + k_out * 20)


def wrap_words(words, fnt, max_w):
    lines, cur = [], []
    for item in words:
        trial = " ".join(x[1] for x in cur + [item])
        if cur and fnt.getlength(trial) > max_w:
            lines.append(cur)
            cur = [item]
        else:
            cur.append(item)
    if cur:
        lines.append(cur)
    return lines


def draw_chat(canvas, m, t):
    """Janela de chat por cima do vídeo: a mensagem vai sendo digitada junto com a fala."""
    t0, t1 = m["start"], m["end"]
    k_in = ease_out_back((t - t0) / 0.45, 1.2)
    k_out = ease_in_out((t - (t1 - 0.3)) / 0.3)  # sai inteira antes do corte
    alpha = clamp((t - t0) / 0.2) * (1 - k_out)
    if alpha <= 0:
        return
    fnt = font("sans_reg", 46)
    bw = 720
    lh = 60
    shown = [(wt, wd) for wt, wd in m["message"] if t >= wt - 0.03]
    n_lines = len(wrap_words(shown, fnt, bw - 80)) if shown else 1
    cw, ch = 1000, 250 + lh * n_lines  # o cartão cresce junto com a mensagem
    card = Image.new("RGBA", (cw * SS, ch * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(card)
    d.rounded_rectangle([0, 0, cw * SS - 1, ch * SS - 1], radius=50 * SS, fill=(255, 255, 255, 240))
    # cabeçalho
    d.ellipse([40 * SS, 34 * SS, 110 * SS, 104 * SS], fill=WINE + (255,))
    sx, sy, sr = 75 * SS, 69 * SS, 22 * SS  # estrelinha de 4 pontas
    d.polygon([(sx, sy - sr), (sx + sr * 0.28, sy - sr * 0.28), (sx + sr, sy),
               (sx + sr * 0.28, sy + sr * 0.28), (sx, sy + sr), (sx - sr * 0.28, sy + sr * 0.28),
               (sx - sr, sy), (sx - sr * 0.28, sy - sr * 0.28)], fill=CREAM + (255,))
    d.text((132 * SS, 70 * SS), m.get("title", "Chat"), font=font("cap_sans", 40 * SS),
           anchor="ls", fill=INK + (255,))
    d.text((132 * SS, 104 * SS), m.get("subtitle", "online"), font=font("sans_reg", 28 * SS),
           anchor="ls", fill=(130, 120, 122, 255))
    d.line([(40 * SS, 132 * SS), ((cw - 40) * SS, 132 * SS)], fill=(225, 215, 215, 255), width=2 * SS)
    # balão (cresce junto com o texto)
    if shown:
        slines = wrap_words(shown, fnt, bw - 80)
        bh = 40 + lh * len(slines)
        width = max(fnt.getlength(" ".join(x[1] for x in ln)) for ln in slines) + 80
        x1, y1 = (cw - 40) * SS, 170 * SS
        d.rounded_rectangle([x1 - width * SS, y1, x1, y1 + bh * SS], radius=34 * SS,
                            fill=WINE + (255,))
        big = font("sans_reg", 46 * SS)
        for i, ln in enumerate(slines):
            d.text((x1 - width * SS + 40 * SS, y1 + (64 + i * lh) * SS),
                   " ".join(x[1] for x in ln), font=big, anchor="ls", fill=WHITE + (255,))
        if (t * 2) % 1 < 0.6 and len(shown) < len(m["message"]):  # cursor piscando
            last = " ".join(x[1] for x in slines[-1])
            cx = x1 - width * SS + 40 * SS + big.getlength(last + " ")
            cy = y1 + (64 + (len(slines) - 1) * lh) * SS
            d.line([(cx, cy - 40 * SS), (cx, cy + 6 * SS)], fill=CREAM + (255,), width=4 * SS)
    card = card.resize((cw, ch), Image.LANCZOS)
    sc = 0.9 + 0.1 * k_in
    card = scaled(card, sc)
    sh = Image.new("RGBA", (card.width + 80, card.height + 80), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([40, 52, 40 + card.width, 52 + card.height], radius=50,
                                         fill=(0, 0, 0, 90))
    sh = sh.filter(ImageFilter.GaussianBlur(22))
    x = (W - card.width) / 2
    y = m.get("y", 1300) + (1 - k_in) * 60 + k_out * 80
    paste(canvas, with_alpha(sh, alpha), x - 40, y - 40)
    paste(canvas, with_alpha(card, alpha), x, y)


def draw_question(canvas, m, t):
    """Cartão vinho “MITO OU VERDADE?” com a pergunta sendo escrita."""
    t0, t1 = m["start"], m["end"]
    k_in = ease_out_cubic((t - t0) / 0.4)
    k_out = ease_in_out((t - (t1 - 0.22)) / 0.22)
    alpha = clamp((t - t0) / 0.25) * (1 - k_out)
    if alpha <= 0:
        return
    fnt = font("cap_sans", 64)
    cw = 1000
    lines = wrap_words(m["words"], fnt, cw - 120)
    ch = 170 + 78 * len(lines)
    card = Image.new("RGBA", (cw * SS, ch * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(card)
    d.rounded_rectangle([0, 0, cw * SS - 1, ch * SS - 1], radius=48 * SS, fill=WINE + (240,))
    card = card.resize((cw, ch), Image.LANCZOS)
    d = ImageDraw.Draw(card)
    lab = font("sans_med", 28)
    x = 60
    for c in "MITO OU VERDADE?":
        d.text((x, 78), c, font=lab, anchor="ls", fill=CREAM + (230,))
        x += lab.getlength(c) + 6
    d.text((cw - 60, 78), m["count"], font=lab, anchor="rs", fill=CREAM + (200,))
    d.line([(60, 100), (cw - 60, 100)], fill=CREAM + (70,), width=2)
    for i, ln in enumerate(lines):
        xx = 60
        for wt, wd in ln:
            k = ease_out_cubic((t - wt + 0.04) / 0.2)
            if k > 0:
                d.text((xx, 178 + i * 78 + (1 - k) * 14), wd, font=fnt, anchor="ls",
                       fill=WHITE + (int(255 * k),))
            xx += fnt.getlength(wd + " ")
    sh = Image.new("RGBA", (cw + 80, ch + 80), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([40, 54, 40 + cw, 54 + ch], radius=48, fill=(30, 0, 8, 100))
    sh = sh.filter(ImageFilter.GaussianBlur(22))
    x0 = (W - cw) / 2
    y0 = m.get("y", 1330) + (1 - k_in) * 70 - k_out * 30
    paste(canvas, with_alpha(sh, alpha), x0 - 40, y0 - 40)
    paste(canvas, with_alpha(scaled(card, 0.96 + 0.04 * k_in), alpha), x0, y0)


def draw_verdict(canvas, m, t):
    """Carimbo MITO (✗ cinza) ou VERDADE (✓ vinho) que “bate” na tela."""
    t0, t1 = m["start"], m["end"]
    k = ease_out_back((t - t0) / 0.28, 2.2)
    k_out = ease_in_out((t - (t1 - 0.25)) / 0.25)
    alpha = clamp((t - t0) / 0.12) * (1 - k_out)
    if alpha <= 0:
        return
    true = m["verdict"] == "verdade"
    color = WINE if true else (72, 64, 68)
    word = "VERDADE" if true else "MITO"
    fnt = font("cap_sans", 150)
    tw = fnt.getlength(word)
    r = 70
    w, h = int(tw + 2 * r + 150), 250
    img = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, w * SS - 1, h * SS - 1], radius=125 * SS, fill=WHITE + (245,),
                        outline=color + (255,), width=10 * SS)
    cx, cy = (60 + r) * SS, h / 2 * SS
    d.ellipse([cx - r * SS, cy - r * SS, cx + r * SS, cy + r * SS], fill=color + (255,))
    if true:
        pts = [(cx - 0.45 * r * SS, cy + 0.02 * r * SS), (cx - 0.12 * r * SS, cy + 0.34 * r * SS),
               (cx + 0.48 * r * SS, cy - 0.30 * r * SS)]
        d.line(pts, fill=WHITE + (255,), width=14 * SS, joint="curve")
    else:
        q = 0.36 * r * SS
        d.line([(cx - q, cy - q), (cx + q, cy + q)], fill=WHITE + (255,), width=14 * SS)
        d.line([(cx + q, cy - q), (cx - q, cy + q)], fill=WHITE + (255,), width=14 * SS)
    img = img.resize((w, h), Image.LANCZOS)
    ImageDraw.Draw(img).text((60 + 2 * r + 40, h / 2 + 52), word, font=fnt, anchor="ls",
                             fill=color + (255,))
    shake = math.sin((t - t0) * 70) * 6 * clamp(1 - (t - t0) / 0.35) if t - t0 < 0.35 else 0
    img = img.rotate(-6 + shake * 0.3, resample=Image.BICUBIC, expand=True)
    img = scaled(img, (1.9 - 0.9 * min(k, 1.06)) * (1 - 0.08 * k_out))
    sh = Image.new("RGBA", (img.width + 100, img.height + 100), (0, 0, 0, 0))
    sh.paste(Image.new("RGBA", img.size, (0, 0, 0, 110)), (50, 64), img.getchannel("A"))
    sh = sh.filter(ImageFilter.GaussianBlur(20))
    x, y = (W - img.width) / 2 + shake, m.get("y", 1450) - img.height / 2
    paste(canvas, with_alpha(sh, alpha), x - 50, y - 50)
    paste(canvas, with_alpha(img, alpha), x, y)


OVERLAY_KINDS = {"chat": draw_chat, "question": draw_question, "verdict": draw_verdict}


def draw_motion(canvas, t):
    for m in motions():
        t0, t1 = m["start"], m["end"]
        if not (t0 <= t < t1):
            continue
        if m.get("kind") in OVERLAY_KINDS:  # por cima do vídeo, sem fundo
            OVERLAY_KINDS[m["kind"]](canvas, m, t)
            return
        layer = motion_background().copy()
        if m.get("kind", "signals") != "checklist":
            draw_dashed_circle(layer, t, ease_in_out((t - t0 - 0.15) / 0.7), 1.0)
        if m.get("kind", "signals") == "counter":
            draw_counter(layer, m, t)
        elif m["kind"] == "checklist":
            draw_checklist(layer, m, t)
        elif m["kind"] == "apple":
            draw_apple(layer, m, t)
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
        wipe = m.get("exit_wipe")
        if wipe:
            # sai fechando em círculo por cima da cena seguinte (o corte já aconteceu)
            k = ease_in_out((t - (t1 - wipe)) / wipe)
            if k > 0:
                mask = Image.new("L", (W, H), 0)
                r = (1 - k) * math.hypot(W, H)
                cx, cy = CIRCLE_C
                ImageDraw.Draw(mask).ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
                layer.putalpha(ImageChops.multiply(layer.getchannel("A"), mask))
            canvas.alpha_composite(layer)
            return
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
    cuts = cam["cuts"]
    # punch-in: tempo (usa punch_zoom) ou (tempo, zoom) — zoom 1.0 volta ao plano aberto
    punches = dict(p if isinstance(p, tuple) else (p, cam.get("punch_zoom", 1.14))
                   for p in cam["punch_ins"])
    marks = sorted([0.0] + cuts + list(punches) + [1e9])
    a = max(m for m in marks if m <= t)
    b = min(m for m in marks if m > t)
    zoom = punches.get(a, 1.0)
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
    for leak in cam.get("leaks", []):
        k = light_leak_strength(t - leak)
        if k > 0.01:
            out = apply_light_leak(out, k, leak)
    return out


def light_leak_strength(dt):
    """Sobe rápido até o corte e some devagar depois (como um vazamento de luz)."""
    if -0.28 <= dt < 0:
        return ease_in_out((dt + 0.28) / 0.28)
    if 0 <= dt < 0.55:
        return 1 - ease_in_out(dt / 0.55)
    return 0.0


@lru_cache(maxsize=None)
def light_leak_layer(seed):
    """Manchas quentes (laranja/creme) vindo das bordas, em baixa resolução."""
    w, h = W // 8, H // 8
    img = Image.new("RGB", (w, h), (0, 0, 0))
    d = ImageDraw.Draw(img)
    side = seed % 2
    cx = w * (0.95 if side else 0.05)
    d.ellipse([cx - w * 0.7, -h * 0.15, cx + w * 0.7, h * 0.75], fill=(255, 150, 70))
    d.ellipse([w * (0.1 if side else 0.5), h * 0.45, w * (0.6 if side else 1.0), h * 1.1],
              fill=(255, 205, 150))
    img = img.filter(ImageFilter.GaussianBlur(w * 0.18))
    return img.resize((W, H), Image.BICUBIC)


def apply_light_leak(frame, k, leak):
    rgb = frame.convert("RGB")
    glow = light_leak_layer(int(leak * 10)).point(lambda v: int(v * k))
    out = ImageChops.screen(rgb, glow)
    if k > 0.6:  # breve estouro de luz no pico
        out = Image.blend(out, Image.new("RGB", out.size, (255, 236, 214)), (k - 0.6) * 0.7)
    out = out.convert("RGBA")
    return out


# ---------------------------------------------------------------- render


def render_frame(t):
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if t < getattr(script, "SCENE_CUT", 0):
        draw_static(canvas, t)
    else:
        draw_dynamic(canvas, t)
        draw_nametags(canvas, t)
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
    size = getattr(script, "OUTPUT_SIZE", None)
    scale = f"scale={size[0]}:{size[1]}:flags=lanczos,setsar=1," if size else ""
    parts = ["[0:v][1:v]overlay=0:0:format=auto,format=yuv420p," + scale +
             f"split={n}" + "".join(f"[vs{i}]" for i in range(n)),
             f"[0:a]asplit={n}" + "".join(f"[as{i}]" for i in range(n))]
    for i, (k0, k1) in enumerate(keep):
        fade = 0.012  # evita estalo nas emendas do áudio
        parts.append(f"[vs{i}]trim={k0}:{k1},setpts=PTS-STARTPTS[v{i}]")
        parts.append(f"[as{i}]atrim={k0}:{k1},asetpts=PTS-STARTPTS,"
                     f"afade=t=in:d={fade},afade=t=out:st={k1 - k0 - fade}:d={fade}[a{i}]")
    parts.append("".join(f"[v{i}][a{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=1[v][a]")
    return ";".join(parts)


def out_scale():
    """Escala final opcional (ex.: 1080x1920, o 9:16 exato do Reels)."""
    size = getattr(script, "OUTPUT_SIZE", None)
    return ["-vf", f"scale={size[0]}:{size[1]}:flags=lanczos,setsar=1"] if size else []


def render_with_camera(src, dst, n):
    """Quadros do vídeo passam pela câmera em Python antes de receber a legenda."""
    if getattr(script, "CUTS", None):
        sys.exit("CUTS com CAMERA ainda não é suportado")
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", src, "-f", "rawvideo",
                            "-pix_fmt", "rgba", "-"], stdout=subprocess.PIPE)
    enc = subprocess.Popen([
        "ffmpeg", "-v", "error", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-i", src, "-map", "0:v", "-map", "1:a?", *out_scale(), "-c:v", "libx264", "-crf", "17",
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
