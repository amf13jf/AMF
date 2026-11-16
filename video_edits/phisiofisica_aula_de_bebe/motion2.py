"""Halftone / protest-placard motion (style of the reference) for the baby-class video.
usage: python3 motion2.py opening|m1|m2 out.mp4
"""
import sys, math, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
U = "/root/.claude/uploads/00a1eb58-2f10-553f-a2af-6cc22a747030/"
MAIN = U + "835b26af-Phisiofisica_-_aula_de_bebe.mp4"
ANTON = "/root/.fonts/Anton-400.ttf"
MONT = "/root/.fonts/Montserrat-700.ttf"
NAVY = (30, 38, 104)
rng = np.random.default_rng(11)

def frames(path, start, dur, speed=1.0, crop=None):
    pre = f"crop=iw*{crop[2]}:ih*{crop[3]}:iw*{crop[0]}:ih*{crop[1]}," if crop else ""
    vf = pre + f"setpts=PTS/{speed},fps=30,scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}"
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(start), "-t", str(dur * speed + 0.1), "-i", path,
                          "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    n = len(raw) // (W * H * 3)
    return np.frombuffer(raw, np.uint8).reshape(n, H, W, 3)

# ---------- halftone (rotated 45deg dot screen) ----------
CELL = 9
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
ang = math.radians(45)
u = (xx * math.cos(ang) + yy * math.sin(ang)) / CELL
v = (-xx * math.sin(ang) + yy * math.cos(ang)) / CELL
du = (u - np.floor(u) - 0.5); dv = (v - np.floor(v) - 0.5)
DIST = np.sqrt(du * du + dv * dv)                       # distance to dot centre (in cells)
# paper tint: cream with a warm (yellow) cast top-left like the reference
PAPER = np.stack([np.full((H, W), 228.0), np.full((H, W), 232.0), np.full((H, W), 236.0)], -1)
warm = np.clip(1 - ((xx / W) ** 2 + (yy / H / 0.6) ** 2), 0, 1)[..., None]
PAPER = PAPER * (1 - 0.25 * warm) + np.array([240, 226, 170]) * 0.25 * warm
INK = np.array(NAVY, np.float32)
VIG = (1 - 0.35 * (((xx / W - 0.5) ** 2 + (yy / H - 0.5) ** 2) * 2.2))[..., None]

def halftone(rgb):
    f = rgb.astype(np.float32) / 255
    lum = 0.3 * f[..., 0] + 0.59 * f[..., 1] + 0.11 * f[..., 2]
    lum = np.clip((lum - 0.12) / 0.8, 0, 1)                 # contrast
    dark = 1 - Image.fromarray((lum * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(CELL * 0.35))
    dark = np.asarray(dark if isinstance(dark, Image.Image) else dark, np.float32)
    return dark

def halftone_frame(rgb):
    f = rgb.astype(np.float32) / 255
    lum = 0.3 * f[..., 0] + 0.59 * f[..., 1] + 0.11 * f[..., 2]
    lum = np.clip((lum - 0.06) / 0.76, 0, 1) ** 0.95
    lum_s = np.asarray(Image.fromarray((lum * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(CELL * 0.3)), np.float32) / 255
    dark = 1 - lum_s
    r = 0.68 * np.sqrt(dark)                                 # dot radius in cells
    dots = np.clip((r - DIST) * CELL * 0.9 + 0.5, 0, 1)      # anti-aliased dots
    tone = dark * 0.55                                       # continuous duotone underlay keeps detail
    k = np.clip(dots * 0.85 + tone * 0.40, 0, 1)[..., None]
    out = PAPER * (1 - k) + INK * k
    out += rng.normal(0, 7, (H, W, 1))                       # grain
    out *= VIG
    return np.clip(out, 0, 255).astype(np.uint8)

# ---------- placard ----------
def placard(lines, size=150, pad=46, border=16, width=None):
    f = ImageFont.truetype(ANTON, size)
    bbs = [f.getbbox(l) for l in lines]
    tw = max(b[2] - b[0] for b in bbs); lh = int(size * 1.22)
    w = (width or tw + 2 * pad + 2 * border + 30); h = lh * len(lines) + 2 * pad + 2 * border
    card = Image.new("RGBA", (w + 60, h + 60), (0, 0, 0, 0))
    d = ImageDraw.Draw(card)
    ox, oy = 30, 30
    d.rectangle([ox, oy, ox + w, oy + h], fill=(246, 246, 243, 255))
    d.rectangle([ox + 22, oy + 22, ox + w - 22, oy + h - 22], outline=NAVY + (255,), width=border)
    y = oy + 22 + border + pad * 0.45
    for l, b in zip(lines, bbs):
        cap = f.getbbox('H'); d.text((ox + (w - (b[2] - b[0])) / 2 - b[0], y + (lh - (cap[3] - cap[1])) / 2 - cap[1]), l, font=f, fill=NAVY + (255,))
        y += lh
    # printed / halftoned feel on the card: slight grain + ink speckle
    a = np.array(card).astype(np.float32)
    mask = a[..., 3:] > 0
    a[..., :3] += rng.normal(0, 9, a[..., :3].shape) * mask
    card = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    # soft shadow
    sh = Image.new("RGBA", card.size, (0, 0, 0, 0)); sh.putalpha(card.split()[3].point(lambda v: int(v * 0.35)))
    out = Image.new("RGBA", (card.size[0] + 40, card.size[1] + 40), (0, 0, 0, 0))
    out.alpha_composite(sh.filter(ImageFilter.GaussianBlur(12)), (28, 34))
    out.alpha_composite(card, (10, 10))
    return out

def small_text(t, size=34, color=(245, 245, 240)):
    f = ImageFont.truetype(MONT, size); b = f.getbbox(t)
    img = Image.new("RGBA", (b[2] - b[0] + 20, b[3] - b[1] + 20), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((10 - b[0], 10 - b[1]), t, font=f, fill=color + (255,))
    sh = img.copy(); sh = Image.new("RGBA", img.size, (0, 0, 0, 0)); sh.putalpha(img.split()[3].point(lambda v: int(v * 0.5)))
    out = Image.new("RGBA", img.size, (0, 0, 0, 0)); out.alpha_composite(sh.filter(ImageFilter.GaussianBlur(2)), (2, 2)); out.alpha_composite(img)
    return out

def ease_out_back(x, s=1.7):
    x = min(max(x, 0), 1) - 1
    return x * x * ((s + 1) * x + s) + 1

class Card:
    def __init__(s, img, cx, cy, rot, t_in, t_out=99, frm="right"):
        s.img, s.cx, s.cy, s.rot, s.t_in, s.t_out, s.frm = img, cx, cy, rot, t_in, t_out, frm
        s.ph = rng.uniform(0, 6)
    def draw(s, canvas, t):
        if t < s.t_in or t > s.t_out: return
        k = ease_out_back((t - s.t_in) / 0.5)
        off = {"right": (1, 0.25), "left": (-1, 0.25), "bottom": (0.2, 1)}[s.frm]
        dx = (1 - k) * off[0] * W; dy = (1 - k) * off[1] * H
        r = s.rot + (1 - k) * (-14 if s.frm != "left" else 14) + 0.8 * math.sin(t * 1.7 + s.ph)
        im = s.img.rotate(r, resample=Image.BICUBIC, expand=True)
        x = s.cx + dx + 4 * math.sin(t * 1.1 + s.ph); y = s.cy + dy + 6 * math.sin(t * 1.4 + s.ph)
        canvas.alpha_composite(im, (int(x - im.size[0] / 2), int(y - im.size[1] / 2)))

def render(out, bg_frames, cards, halft=True, labels=True, zoom=(1.0, 1.08)):
    n = len(bg_frames)
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", "30",
                            "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    tl = small_text("Phisiofisica"); tr = small_text("#aulade bebê".replace("aulade", "aula de "))
    bl = small_text("Natação infantil"); br = small_text("20 minutos")
    for i in range(n):
        t = i / FPS
        z = zoom[0] + (zoom[1] - zoom[0]) * (t / max(n / FPS, 0.01))
        img = Image.fromarray(bg_frames[i])
        if abs(z - 1) > 1e-3:   # slow push-in (sub-pixel)
            cw, ch = W / z, H / z
            img = img.transform((W, H), Image.EXTENT, ((W - cw) / 2, (H - ch) * 0.4, (W + cw) / 2, (H - ch) * 0.4 + ch), Image.BICUBIC)
        if halft:
            img = Image.fromarray(halftone_frame(np.asarray(img)))
        canvas = img.convert("RGBA")
        if labels:
            canvas.alpha_composite(tl, (44, 300)); canvas.alpha_composite(tr, (W - tr.size[0] - 44, 300))
            canvas.alpha_composite(bl, (44, 1380)); canvas.alpha_composite(br, (W - br.size[0] - 44, 1380))
        for c in cards: c.draw(canvas, t)
        enc.stdin.write(canvas.convert("RGB").tobytes())
    enc.stdin.close(); enc.wait()

mode, out = sys.argv[1], sys.argv[2]
if mode == "opening":
    bg = frames(MAIN, 0, 5.867)
    cards = [Card(placard(["A AULA DE BEBÊ", "DURA 20 MINUTOS"], 118), 530, 420, -6, 0.15, frm="left"),
             Card(placard(["VOCÊ ACHA", "POUCO?"], 128), 640, 1640, 7, 2.1, frm="right")]
    render(out, bg, cards, halft=False, labels=False, zoom=(1.0, 1.0))
elif mode == "m1":   # 28.70 -> 39.30 : temperatura corporal / 20 min suficiente / troca de calor
    T0 = 28.70
    bg = frames(U + "697d6c9d-IMG_2728.mp4", 14.0, 10.6, crop=(0.0, 0.12, 0.62, 0.55))
    cards = [Card(placard(["REGULANDO A", "TEMPERATURA"], 120), 500, 700, -10, 31.1 - T0, frm="left"),
             Card(placard(["20 MINUTOS", "É O SUFICIENTE"], 118), 600, 1180, 8, 34.3 - T0, frm="right")]
    render(out, bg, cards)
elif mode == "m2":   # 55.00 -> 65.60 : concentração / muitos estímulos
    T0 = 55.00
    bg = frames(U + "ffcc6076-IMG_2736.MOV", 0.0, 10.6, speed=0.55)
    cards = [Card(placard(["PERDE A", "CONCENTRAÇÃO"], 124), 520, 700, -9, 57.1 - T0, frm="left"),
             Card(placard(["MUITOS", "ESTÍMULOS"], 140), 600, 1190, 10, 59.9 - T0, frm="right")]
    render(out, bg, cards)
print("done", out)
