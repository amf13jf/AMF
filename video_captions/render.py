"""Queima legendas (normal + dinâmica) e o motion vinho no vídeo.

Uso:
    python -m video_captions.render entrada.mp4 saida.mp4

As fontes são procuradas primeiro no macOS (Helvetica Neue e Bodoni 72);
se não existirem, usa Inter (sans) e Bodoni Moda (serif, incluída em
video_captions/fonts). Dá para forçar com --sans / --serif.
"""

import argparse
import math
import os
import shutil
import subprocess
import sys
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from . import aura_reels4 as script

HERE = os.path.dirname(os.path.abspath(__file__))

W, H, FPS = 1216, 2160, 30

WINE = (122, 28, 50)
WINE_DEEP = (70, 12, 28)
WINE_LIGHT = (176, 70, 92)
CREAM = (248, 238, 230)
WHITE = (255, 255, 255)

# ---------------------------------------------------------------- fontes

SANS_CANDIDATES = [
    "/System/Library/Fonts/HelveticaNeue.ttc",
    "/Library/Fonts/HelveticaNeue.ttc",
    "/usr/share/fonts/opentype/inter/Inter-Medium.otf",
]
SANS_BOLD_CANDIDATES = [
    "/System/Library/Fonts/HelveticaNeue.ttc",
    "/Library/Fonts/HelveticaNeue.ttc",
    "/usr/share/fonts/opentype/inter/Inter-Bold.otf",
]
SERIF_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Bodoni 72.ttc",
    "/Library/Fonts/Bodoni 72.ttc",
    os.path.join(HERE, "fonts", "bodoni-moda-latin-400-italic.woff"),
]


def _pick_face(path, want_style):
    """Em .ttc escolhe o índice cujo estilo bate com want_style."""
    if not path.lower().endswith(".ttc"):
        return path, 0
    best = None
    for i in range(32):
        try:
            f = ImageFont.truetype(path, 20, index=i)
        except OSError:
            break
        style = f.getname()[1].lower()
        if style == want_style:
            return path, i
        if best is None and want_style in style:
            best = i
    return path, best or 0


def resolve_font(candidates, want_style, override=None):
    for p in ([override] if override else []) + candidates:
        if p and os.path.exists(p):
            return _pick_face(p, want_style)
    sys.exit(f"Nenhuma fonte encontrada entre: {candidates}")


FONTS = {}


@lru_cache(maxsize=None)
def font(kind, size):
    path, index = FONTS[kind]
    return ImageFont.truetype(path, int(size), index=index)


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


def shadowed_text(text, fnt, fill=WHITE, shadow=0.6, blur=7, offset=3, pad=24):
    """Sprite de texto com sombra suave. Retorna (img, baseline_y, avanço)."""
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


def wrap(text, fnt, max_w):
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if cur and fnt.getlength(trial) > max_w:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    lines.append(cur)
    return lines


# ---------------------------------------------------------------- legenda normal

STATIC_SIZE = 64
STATIC_CENTER_Y = 835  # parede acima das duas pessoas


@lru_cache(maxsize=None)
def static_sprite(text):
    fnt = font("sans_bold", STATIC_SIZE)
    lines = wrap(text, fnt, 960)
    if len(lines) > 1:  # equilibra as linhas
        lines = wrap(text, fnt, fnt.getlength(text) / len(lines) + 60)
    line_h = int(STATIC_SIZE * 1.22)
    sprites = [shadowed_text(ln, fnt, shadow=0.75, blur=8, offset=3) for ln in lines]
    w = max(s[0].width for s in sprites)
    h = sprites[0][0].height + line_h * (len(lines) - 1)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    for i, (sp, ox, base, adv) in enumerate(sprites):
        img.alpha_composite(sp, dest=((w - sp.width) // 2, i * line_h))
    return img


def draw_static(canvas, t):
    for start, end, text in script.STATIC_SUBS:
        if start - 0.06 <= t < end:
            a = min(clamp((t - start + 0.06) / 0.12), clamp((end - t) / 0.08))
            img = static_sprite(text)
            dy = (1 - ease_out_cubic((t - start + 0.06) / 0.2)) * 10
            paste(canvas, with_alpha(img, a), (W - img.width) / 2,
                  STATIC_CENTER_Y - img.height / 2 + dy)
            return


# ---------------------------------------------------------------- legenda dinâmica

DYN_SIZE = 80
DYN_KEY_SIZE = 108
DYN_BASELINE = 1470
DYN_MAX_W = 1060
KEY_GAP = 24  # folga para o fundo vinho do destaque


@lru_cache(maxsize=None)
def word_sprite(word):
    if word.startswith("*"):
        return shadowed_text(word[1:], font("serif_italic", DYN_KEY_SIZE), fill=WHITE,
                             shadow=0.35, blur=6, offset=2)
    return shadowed_text(word, font("sans_bold", DYN_SIZE), shadow=0.7, blur=8, offset=3)


@lru_cache(maxsize=None)
def pill(word):
    """Fundo vinho arredondado do destaque (desenhado em 4x para antialias)."""
    fnt = font("serif_italic", DYN_KEY_SIZE)
    l, t, r, b = fnt.getbbox(word[1:], anchor="ls")
    px, py = 22, 14
    w, h = int(r - l + 2 * px), int(b - t + 2 * py)
    ss = 4
    big = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    for i in range(h * ss):  # degradê vertical vinho
        k = i / (h * ss)
        c = tuple(int(WINE[j] * (1 - k) + WINE_DEEP[j] * k) for j in range(3))
        d.line([(0, i), (w * ss, i)], fill=c + (235,))
    mask = Image.new("L", big.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w * ss - 1, h * ss - 1], radius=20 * ss,
                                           fill=255)
    big.putalpha(Image.composite(big.getchannel("A"), mask, mask))
    return big.resize((w, h), Image.LANCZOS), l - px, t - py


def layout_chunk(chunk):
    """Posições (x, linha) de cada palavra, centralizadas, com quebra de linha."""
    space = font("sans_bold", DYN_SIZE).getlength(" ") * 1.1
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
    for ci, chunk in enumerate(chunks):
        start = chunk[0][0] - 0.04
        nxt = chunks[ci + 1][0][0] - 0.04 if ci + 1 < len(chunks) else 1e9
        end = min(nxt, chunk[-1][1] + 0.45)
        m = script.MOTION
        if start < m["start"] < end:  # some antes do card do motion entrar
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
                sw, sh = max(1, int(img.width * scale)), max(1, int(img.height * scale))
                img2 = img.resize((sw, sh), Image.BILINEAR)
                cx, cy = x + adv / 2, by - DYN_SIZE * 0.35
                dx = cx - (ox + adv / 2) * scale
                dy = cy - (base - DYN_SIZE * 0.35) * scale
                paste(canvas, with_alpha(img2, a), dx, dy)
            else:
                paste(canvas, with_alpha(img, a), x - ox, by - base)
        return


# ---------------------------------------------------------------- motion vinho

CARD_X, CARD_Y, CARD_W, CARD_H = 64, 1270, 1088, 640
SS = 2  # supersampling do card


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


def partial(pts, frac):
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


def draw_stroke(d, pts, cx, cy, size, frac, width, color):
    seg = [(cx + (x - 0.5) * size, cy + (y - 0.5) * size) for x, y in partial(pts, frac)]
    if len(seg) > 1:
        d.line(seg, fill=color, width=width, joint="curve")
        r = width / 2
        for x, y in (seg[0], seg[-1]):
            d.ellipse([x - r, y - r, x + r, y + r], fill=color)
    return seg


@lru_cache(maxsize=None)
def card_base():
    """Fundo do card (degradê vinho + filete creme), em supersampling."""
    w, h = CARD_W * SS, CARD_H * SS
    grad = Image.new("RGBA", (w, h))
    d = ImageDraw.Draw(grad)
    for i in range(h):
        k = i / h
        c = tuple(int(WINE[j] * (1 - k) + WINE_DEEP[j] * k) for j in range(3))
        d.line([(0, i), (w, i)], fill=c + (240,))
    # brilho diagonal sutil no canto superior esquerdo
    glow = Image.new("L", (w, h), 0)
    ImageDraw.Draw(glow).ellipse([-w * 0.3, -h * 0.9, w * 0.55, h * 0.55], fill=38)
    glow = glow.filter(ImageFilter.GaussianBlur(120))
    grad = Image.composite(Image.new("RGBA", (w, h), WINE_LIGHT + (240,)), grad, glow)
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], radius=46 * SS, fill=255)
    grad.putalpha(Image.composite(grad.getchannel("A"), mask, mask))
    ImageDraw.Draw(grad).rounded_rectangle(
        [16 * SS, 16 * SS, w - 16 * SS, h - 16 * SS], radius=34 * SS,
        outline=CREAM + (60,), width=2 * SS)
    return grad


@lru_cache(maxsize=None)
def card_shadow():
    pad = 60
    img = Image.new("RGBA", (CARD_W + 2 * pad, CARD_H + 2 * pad), (0, 0, 0, 0))
    ImageDraw.Draw(img).rounded_rectangle([pad, pad + 14, pad + CARD_W, pad + CARD_H + 14],
                                          radius=46, fill=(20, 0, 6, 120))
    return img.filter(ImageFilter.GaussianBlur(26)), pad


def draw_line_words(d, items, t, x0, base, size, key_size, color):
    """Linha de palavras que entram uma a uma (subindo + fade)."""
    sans = font("sans_med", size * SS)
    serif = font("serif_italic", key_size * SS)
    space = sans.getlength(" ")
    x = x0 * SS
    for ws, word in items:
        is_key = word.startswith("*")
        fnt = serif if is_key else sans
        txt = word[1:] if is_key else word
        k = ease_out_cubic((t - ws + 0.05) / 0.3)
        if k > 0:
            dy = (1 - k) * 26 * SS
            d.text((x, base * SS + dy), txt, font=fnt, anchor="ls",
                   fill=color + (int(255 * k),))
        x += fnt.getlength(txt) + space * (1.25 if is_key else 1)
    return x / SS


def draw_big_word(d, ws, text, t, x0, base, size, color):
    """Palavra grande em Bodoni itálico, letra por letra."""
    fnt = font("serif_italic", size * SS)
    for i, ch in enumerate(text):
        k = ease_out_cubic((t - ws - i * 0.035) / 0.35)
        if k <= 0:
            continue
        x = x0 * SS + fnt.getlength(text[:i])
        dy = (1 - k) * 46 * SS
        d.text((x, base * SS + dy), ch, font=fnt, anchor="ls", fill=color + (int(255 * k),))
    return x0 + fnt.getlength(text) / SS


def draw_phase(layer, t, phase, num, t_in, offset_x, alpha):
    if alpha <= 0:
        return
    content = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(content)
    lx = 70
    # rótulo + linha que cresce
    lbl = font("sans_bold", 28 * SS)
    k = ease_out_cubic((t - t_in) / 0.4)
    label = phase["label"]
    spacing = 7 * SS
    x = lx * SS
    for ch in label:
        d.text((x, 92 * SS), ch, font=lbl, anchor="ls", fill=CREAM + (int(220 * k),))
        x += lbl.getlength(ch) + spacing
    line_x0 = x + 18 * SS
    line_x1 = line_x0 + (560 * SS - line_x0 + lx * SS) * ease_in_out((t - t_in - 0.1) / 0.6)
    if line_x1 > line_x0:
        d.line([(line_x0, 83 * SS), (line_x1, 83 * SS)], fill=CREAM + (110,), width=2 * SS)

    # ícone: dente (cárie) ou gota (gengiva)
    icx, icy, isz = 940 * SS, 132 * SS, 150 * SS
    draw_k = ease_in_out((t - t_in - 0.05) / 1.0)
    ring = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    rd = ImageDraw.Draw(ring)
    rr = 100 * SS
    rd.ellipse([icx - rr, icy - rr, icx + rr, icy + rr], outline=CREAM + (int(45 * k),),
               width=2 * SS)
    content.alpha_composite(ring)
    if num == 1:
        draw_stroke(d, TOOTH, icx, icy, isz, draw_k, 7 * SS, CREAM + (255,))
        # ponto da cárie pulsando
        pk = clamp((t - t_in - 0.9) / 0.3)
        if pk > 0:
            px, py = icx + 0.10 * isz, icy - 0.24 * isz
            r = 11 * SS * ease_out_back(pk)
            d.ellipse([px - r, py - r, px + r, py + r], fill=WINE_LIGHT + (255,),
                      outline=CREAM + (255,), width=3 * SS)
            pulse = ((t - t_in - 0.9) % 0.9) / 0.9
            pr = r + pulse * 34 * SS
            d.ellipse([px - pr, py - pr, px + pr, py + pr],
                      outline=CREAM + (int(170 * (1 - pulse) * pk),), width=2 * SS)
    else:
        fill_k = clamp((t - t_in - 0.85) / 0.35)
        if fill_k > 0:
            seg = [(icx + (x - 0.5) * isz * 0.82, icy + (y - 0.5) * isz * 0.82) for x, y in DROP]
            d.polygon(seg, fill=WINE_LIGHT + (int(255 * fill_k),))
        draw_stroke(d, DROP, icx, icy, isz * 0.82, draw_k, 7 * SS, CREAM + (255,))
        if fill_k > 0:  # brilho da gota
            hx, hy = icx - 0.13 * isz, icy + 0.12 * isz
            d.arc([hx - 22 * SS, hy - 30 * SS, hx + 22 * SS, hy + 30 * SS], 110, 200,
                  fill=CREAM + (int(220 * fill_k),), width=5 * SS)

    # textos
    if num == 1:
        draw_line_words(d, phase["line"], t, lx, 300, 58, 74, CREAM)
        ws, big = phase["big"]
        draw_big_word(d, ws, big, t, lx - 6, 480, 158, CREAM)
    else:
        draw_line_words(d, phase["line"], t, lx, 290, 58, 74, CREAM)
        draw_line_words(d, phase["line2"], t, lx, 372, 58, 74, CREAM)
        ws, big = phase["big"]
        draw_big_word(d, ws, big, t, lx - 6, 525, 158, CREAM)

    content = with_alpha(content, alpha)
    paste(layer, content, offset_x * SS, 0)


def draw_motion(canvas, t):
    m = script.MOTION
    if not (m["start"] <= t < m["end"]):
        return
    p_in = ease_out_cubic((t - m["start"]) / 0.5)
    p_out = ease_in_out((t - (m["end"] - 0.35)) / 0.35)
    alpha = clamp((t - m["start"]) / 0.3) * (1 - p_out)
    dy = (1 - p_in) * 140 + p_out * 70
    scale = 0.94 + 0.06 * ease_out_back((t - m["start"]) / 0.55, 1.2)

    layer = card_base().copy()
    # contadores e barra de progresso
    d = ImageDraw.Draw(layer)
    bar_y = (CARD_H - 62) * SS
    bx0, bx1 = 70 * SS, (CARD_W - 150) * SS
    d.line([(bx0, bar_y), (bx1, bar_y)], fill=CREAM + (60,), width=4 * SS)
    prog = clamp((t - m["start"]) / (m["end"] - 0.35 - m["start"]))
    d.line([(bx0, bar_y), (bx0 + (bx1 - bx0) * prog, bar_y)], fill=CREAM + (235,),
           width=4 * SS)
    cnt = "01 / 02" if t < m["switch"] + 0.15 else "02 / 02"
    d.text(((CARD_W - 70) * SS, bar_y + 9 * SS), cnt, font=font("sans_bold", 24 * SS),
           anchor="rs", fill=CREAM + (200,))

    sw = m["switch"]
    out1 = ease_in_out((t - sw) / 0.3)
    in2 = ease_out_cubic((t - sw - 0.12) / 0.4)
    draw_phase(layer, t, m["phase1"], 1, m["start"] + 0.1, -out1 * 120, 1 - out1)
    if t >= sw:
        draw_phase(layer, t, m["phase2"], 2, sw + 0.12, (1 - in2) * 140, in2)

    card = layer.resize((CARD_W, CARD_H), Image.LANCZOS)
    if scale < 0.999:
        card = card.resize((int(CARD_W * scale), int(CARD_H * scale)), Image.LANCZOS)
    card = with_alpha(card, alpha)
    sh, pad = card_shadow()
    cx = CARD_X + (CARD_W - card.width) / 2
    cy = CARD_Y + (CARD_H - card.height) / 2 + dy
    paste(canvas, with_alpha(sh, alpha * 0.9), CARD_X - pad, CARD_Y - pad + dy)
    paste(canvas, card, cx, cy)


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
    ap.add_argument("--sans", help="fonte sans (Helvetica Neue) — .ttf/.otf/.ttc")
    ap.add_argument("--serif", help="fonte serif (Bodoni 72) — .ttf/.otf/.ttc/.woff")
    ap.add_argument("--preview", type=float, nargs="*",
                    help="só salva PNGs desses instantes (segundos) ao lado da saída")
    args = ap.parse_args()

    FONTS["sans_med"] = resolve_font(SANS_CANDIDATES, "medium", args.sans)
    FONTS["sans_bold"] = resolve_font(SANS_BOLD_CANDIDATES, "bold", args.sans)
    FONTS["serif_italic"] = resolve_font(SERIF_CANDIDATES, "book italic", args.serif)
    for k, v in FONTS.items():
        print(f"fonte {k}: {v[0]} [{v[1]}]")

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
