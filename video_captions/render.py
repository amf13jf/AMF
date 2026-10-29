"""Queima legendas (normal + dinâmica) e o motion vinho no vídeo.

Uso:
    python -m video_captions.render entrada.mp4 saida.mp4

Fontes: coloque em video_captions/fonts os arquivos HelveticaNeue-Medium.ttf,
HelveticaNeue-Regular.ttf, Bodoni-Bold.ttf e Bodoni-Italic.ttf (não vão para
o git por licença). Sem eles, usa Helvetica Neue do macOS ou Inter, e Bodoni
Moda (incluída).
"""

import argparse
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

DYN_SIZE = 62
DYN_KEY_SIZE = 84
DYN_BASELINE = 1470
DYN_MAX_W = 1000
KEY_GAP = 18  # folga para o fundo vinho do destaque


@lru_cache(maxsize=None)
def word_sprite(word):
    if word.startswith("*"):
        return shadowed_text(word[1:], font("serif_italic", DYN_KEY_SIZE), fill=WHITE,
                             shadow=0.35, blur=6, offset=2)
    return shadowed_text(word, font("sans_med", DYN_SIZE), shadow=0.7, blur=7, offset=3)


@lru_cache(maxsize=None)
def pill(word):
    """Fundo vinho arredondado do destaque (desenhado em 4x para antialias)."""
    fnt = font("serif_italic", DYN_KEY_SIZE)
    l, t, r, b = fnt.getbbox(word[1:], anchor="ls")
    px, py = 18, 10
    w, h = int(r - l + 2 * px), int(b - t + 2 * py)
    ss = 4
    big = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    for i in range(h * ss):  # degradê vertical vinho
        k = i / (h * ss)
        c = tuple(int(WINE[j] * (1 - k) + WINE_DEEP[j] * k) for j in range(3))
        d.line([(0, i), (w * ss, i)], fill=c + (235,))
    mask = Image.new("L", big.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w * ss - 1, h * ss - 1], radius=16 * ss,
                                           fill=255)
    big.putalpha(Image.composite(big.getchannel("A"), mask, mask))
    return big.resize((w, h), Image.LANCZOS), l - px, t - py


def layout_chunk(chunk):
    """Posições (x, linha) de cada palavra, centralizadas, com quebra de linha."""
    space = font("sans_med", DYN_SIZE).getlength(" ") * 1.1
    lines, cur, cur_w = [], [], 0
    for item in chunk:
        adv = word_sprite(item[2])[3]
        if item[2].startswith("*"):
            adv += 2 * KEY_GAP
        extra = adv + (space if cur else 0)
        if cur and cur_w + extra > DYN_MAX_W:
            lines.append((cur, cur_w))
            cur, cur_w = [], 0
            extra = adv
        cur.append((item, adv))
        cur_w += extra
    lines.append((cur, cur_w))
    out = []
    for li, (items, lw) in enumerate(lines):
        x = (W - lw) / 2
        for item, adv in items:
            gap = KEY_GAP if item[2].startswith("*") else 0
            out.append((item, x + gap, li))
            x += adv + space
    return out, len(lines)


def draw_dynamic(canvas, t):
    chunks = script.DYNAMIC_CHUNKS
    m = script.MOTION
    for ci, chunk in enumerate(chunks):
        start = chunk[0][0] - 0.04
        nxt = chunks[ci + 1][0][0] - 0.04 if ci + 1 < len(chunks) else 1e9
        end = min(nxt, chunk[-1][1] + 0.45)
        if start < m["start"] < end:  # some antes do motion entrar
            end = m["start"] + 0.04
        if not (start <= t < end):
            continue
        out_a = clamp((end - t) / 0.08) if end < nxt else 1.0
        placed, n_lines = layout_chunk(chunk)
        line_h = int(DYN_KEY_SIZE * 1.1)
        top_shift = (n_lines - 1) * line_h / 2
        for (ws, we, word), x, li in placed:
            k = (t - ws + 0.04) / 0.16
            if k <= 0:
                continue
            p = ease_out_back(k)
            a = clamp(k * 1.6) * out_a
            img, ox, base, adv = word_sprite(word)
            by = DYN_BASELINE + li * line_h - top_shift
            scale = 0.82 + 0.18 * p
            if word.startswith("*"):
                pimg, pl, pt = pill(word)
                wipe = ease_out_cubic((t - ws + 0.04) / 0.22)
                cw = max(1, int(pimg.width * wipe))
                paste(canvas, with_alpha(pimg.crop((0, 0, cw, pimg.height)), out_a),
                      x + pl, by + pt)
            if scale < 0.999:
                img2 = scaled(img, scale)
                cx, cy = x + adv / 2, by - DYN_SIZE * 0.35
                dx = cx - (ox + adv / 2) * scale
                dy = cy - (base - DYN_SIZE * 0.35) * scale
                paste(canvas, with_alpha(img2, a), dx, dy)
            else:
                paste(canvas, with_alpha(img, a), x - ox, by - base)
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


def draw_motion(canvas, t):
    m = script.MOTION
    t0, t1, sw = m["start"], m["end"], m["switch"]
    if not (t0 <= t < t1):
        return
    layer = motion_background().copy()

    # círculo e objeto
    draw_dashed_circle(layer, t, ease_in_out((t - t0 - 0.15) / 0.7), 1.0)
    tooth_out = ease_in_out((t - sw) / 0.25)
    tooth_s = ease_out_back((t - t0 - 0.2) / 0.5) * (1 - 0.4 * tooth_out)
    draw_object(layer, tooth_sprite(), t, tooth_s, 1 - tooth_out)
    p1, p2 = m["phase1"], m["phase2"]
    draw_caries_spot(layer, t, p1["line"][1][0], tooth_s, 1 - tooth_out)
    drop_s = ease_out_back((t - sw - 0.1) / 0.5)
    draw_object(layer, drop_sprite(), t, drop_s, clamp((t - sw - 0.1) / 0.2))

    # textos
    a1 = 1 - ease_in_out((t - sw) / 0.2)
    if a1 > 0:
        draw_label(layer, p1["label"], t, t0 + 0.3, a1)
        draw_word_line(layer, p1["line"], t, TEXT_LINE_Y, a1)
        draw_glow_word(layer, p1["big"][0], p1["big"][1], t, TEXT_LINE_Y + 230, a1)
    if t >= sw:
        a2 = clamp((t - sw) / 0.2)
        draw_label(layer, p2["label"], t, sw + 0.1, a2)
        draw_word_line(layer, p2["line"], t, TEXT_LINE_Y, a2)
        draw_word_line(layer, p2["line2"], t, TEXT_LINE_Y + 78, a2)
        draw_glow_word(layer, p2["big"][0], p2["big"][1], t, TEXT_LINE_Y + 300, a2)

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


# ---------------------------------------------------------------- render


def render_frame(t):
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if t < script.SCENE_CUT:
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


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--preview", type=float, nargs="*",
                    help="só salva JPGs desses instantes (segundos) ao lado da saída")
    args = ap.parse_args()

    for kind in FONT_CANDIDATES:
        FONTS[kind] = resolve_font(kind)
        print(f"fonte {kind}: {FONTS[kind][0]} [{FONTS[kind][1]}]")

    if args.preview:
        base = os.path.splitext(args.output)[0]
        for t in args.preview:
            frame = subprocess.check_output([
                "ffmpeg", "-v", "error", "-ss", str(t), "-i", args.input, "-frames:v", "1",
                "-f", "rawvideo", "-pix_fmt", "rgba", "-"])
            bg = Image.frombytes("RGBA", (W, H), frame)
            bg.alpha_composite(render_frame(t))
            bg.convert("RGB").save(f"{base}_{t:05.2f}.jpg", quality=90)
        return

    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg não encontrado")
    n = probe_frames(args.input)
    cmd = [
        "ffmpeg", "-v", "error", "-y", "-i", args.input,
        "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-filter_complex", "[0:v][1:v]overlay=0:0:format=auto,format=yuv420p[v]",
        "-map", "[v]", "-map", "0:a?", "-c:v", "libx264", "-crf", "17", "-preset", "medium",
        "-c:a", "copy", "-movflags", "+faststart", args.output,
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
