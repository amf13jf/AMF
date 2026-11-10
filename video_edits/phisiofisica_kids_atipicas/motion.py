"""Collage / cut-out paper motion for the black section (16.3s -> 36.0s)."""
import math, subprocess, sys, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

W, H, FPS = 1080, 1920, 30
T0, T1 = 16.30, 36.00
DUR = T1 - T0
NF = int(round(DUR * FPS))
U = "/root/.claude/uploads/00a1eb58-2f10-553f-a2af-6cc22a747030/"
MAIN = U + "0a4d9313-Phisiofisica_-_kids_ati_picas.mp4"
F_BOLD = "/root/.fonts/Montserrat-800.ttf"
F_HAND = "/root/.fonts/Caveat-700.ttf"
BLUE = (38, 84, 196)
rng = np.random.default_rng(3)

# ---------------- helpers ----------------
def ease_out_back(x, s=1.9):
    x = min(max(x, 0), 1); x -= 1
    return x * x * ((s + 1) * x + s) + 1
def ease_in_out(x):
    x = min(max(x, 0), 1); return x * x * (3 - 2 * x)

def load_clip(path, start, dur, size, crop):
    """Decode clip (auto-rotated) -> list of PIL images, cropped (x,y,w,h in fractions) & resized."""
    cx, cy, cw, ch = crop
    vf = f"crop=iw*{cw}:ih*{ch}:iw*{cx}:ih*{cy},scale={size[0]}:{size[1]}:flags=lanczos,fps=30"
    cmd = ["ffmpeg", "-v", "error", "-ss", str(start), "-t", str(dur), "-i", path, "-vf", vf,
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    n = len(raw) // (size[0] * size[1] * 3)
    arr = np.frombuffer(raw, np.uint8).reshape(n, size[1], size[0], 3)
    return [Image.fromarray(a) for a in arr]

def still(path, t, size, crop):
    return load_clip(path, t, 0.04, size, crop)[0]

def paper_bg():
    w, h = W + 160, H + 160
    base = np.ones((h, w, 3), np.float32) * np.array([234, 226, 210], np.float32)
    # low frequency blotches
    low = rng.standard_normal((h // 64 + 2, w // 64 + 2)).astype(np.float32)
    low = np.array(Image.fromarray(((low - low.min()) / np.ptp(low) * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC), np.float32) / 255 - 0.5
    base += low[..., None] * 18
    # fine grain
    base += rng.normal(0, 5, (h, w, 1)).astype(np.float32)
    img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img, "RGBA")
    # paper fibres
    for _ in range(900):
        x, y = rng.uniform(0, w), rng.uniform(0, h)
        a = rng.uniform(0, math.pi); L = rng.uniform(6, 30)
        c = int(rng.uniform(170, 255))
        d.line([(x, y), (x + L * math.cos(a), y + L * math.sin(a))], fill=(c, c - 8, c - 20, 40), width=1)
    # soft creases
    for y in (h * 0.37, h * 0.71):
        d.line([(0, y), (w, y + rng.uniform(-30, 30))], fill=(255, 255, 255, 60), width=3)
        d.line([(0, y + 3), (w, y + 3 + rng.uniform(-30, 30))], fill=(150, 140, 120, 40), width=2)
    img = img.filter(ImageFilter.GaussianBlur(0.6))
    # vignette
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    v = 1 - 0.22 * (((xx / w - 0.5) ** 2 + (yy / h - 0.5) ** 2) * 2.2)
    return Image.fromarray(np.clip(np.array(img, np.float32) * v[..., None], 0, 255).astype(np.uint8))

def jagged_poly(w, h, amp, step, pad):
    pts = []
    for x in np.arange(0, w, step): pts.append((pad + x, pad + rng.uniform(-amp, amp)))
    for y in np.arange(0, h, step): pts.append((pad + w + rng.uniform(-amp, amp), pad + y))
    for x in np.arange(w, 0, -step): pts.append((pad + x, pad + h + rng.uniform(-amp, amp)))
    for y in np.arange(h, 0, -step): pts.append((pad + rng.uniform(-amp, amp), pad + y))
    return pts

def add_shadow(rgba, off=(10, 16), blur=14, op=0.38):
    pad = 40
    w, h = rgba.size
    out = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    a = rgba.split()[3].point(lambda v: int(v * op))
    sh = Image.new("RGBA", rgba.size, (40, 30, 20, 0)); sh.putalpha(a)
    out.alpha_composite(sh, (pad + off[0], pad + off[1]))
    out = out.filter(ImageFilter.GaussianBlur(blur))
    out.alpha_composite(rgba, (pad, pad))
    return out

def distress(alpha_img, density=0.10):
    """Punch speckle holes into text alpha for a worn/printed look."""
    w, h = alpha_img.size
    n = rng.random((h // 3 + 1, w // 3 + 1))
    m = Image.fromarray(((n > density) * 255).astype(np.uint8)).resize((w, h), Image.NEAREST).filter(ImageFilter.GaussianBlur(0.8))
    m = m.point(lambda v: 255 if v > 140 else 0)
    return ImageChops.multiply(alpha_img, m)

def torn_label(lines, size=86, color=BLUE):
    f = ImageFont.truetype(F_BOLD, size)
    lw = [f.getbbox(l) for l in lines]
    tw = max(b[2] - b[0] for b in lw); lh = int(size * 1.12)
    w, h = tw + 110, lh * len(lines) + 70
    pad = 30
    img = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.polygon(jagged_poly(w, h, 9, 14, pad), fill=color + (255,))
    # paper texture on label
    arr = np.array(img, np.float32)
    arr[..., :3] += rng.normal(0, 7, arr[..., :3].shape)
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    txt = Image.new("L", img.size, 0); dt = ImageDraw.Draw(txt)
    y = pad + 35
    for l, b in zip(lines, lw):
        dt.text((pad + (w - (b[2] - b[0])) / 2 - b[0], y - b[1] + (lh - (b[3] - b[1])) / 2), l, font=f, fill=255)
        y += lh
    txt = distress(txt, 0.12)
    white = Image.new("RGBA", img.size, (250, 247, 240, 255)); white.putalpha(txt)
    img.alpha_composite(white)
    return add_shadow(img, (8, 12), 10, 0.35)

def sticker_photo(size, border=20, torn=True):
    """Returns (frame_mask, outer_white) for a cut-out photo with irregular white border."""
    w, h = size; pad = 30
    W2, H2 = w + 2 * border, h + 2 * border
    canvas = (W2 + 2 * pad, H2 + 2 * pad)
    outer = Image.new("L", canvas, 0)
    ImageDraw.Draw(outer).polygon(jagged_poly(W2, H2, 5 if torn else 0, 18, pad), fill=255)
    outer = outer.filter(ImageFilter.GaussianBlur(0.7))
    return outer, (pad + border, pad + border)

def compose_photo(frame, outer, off):
    img = Image.new("RGBA", outer.size, (255, 255, 255, 0))
    white = Image.new("RGBA", outer.size, (252, 251, 247, 255)); white.putalpha(outer)
    img.alpha_composite(white)
    img.paste(frame, off)
    return add_shadow(img, (12, 18), 16, 0.40)

def hand_label(text, size=94, color=(25, 22, 20), bg=(255, 253, 246, 255)):
    f = ImageFont.truetype(F_HAND, size)
    b = f.getbbox(text)
    w, h = b[2] - b[0] + 60, b[3] - b[1] + 50
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    if bg:
        d.polygon(jagged_poly(w - 30, h - 24, 4, 12, 13), fill=bg)
    d.text((30 - b[0], 25 - b[1]), text, font=f, fill=color)
    return add_shadow(img, (5, 8), 6, 0.25 if bg else 0.0) if bg else img

def arrow(points, width=7, color=(25, 22, 20, 255), head=True):
    xs = [p[0] for p in points]; ys = [p[1] for p in points]
    pad = 40; x0, y0 = min(xs) - pad, min(ys) - pad
    img = Image.new("RGBA", (int(max(xs) - x0 + pad), int(max(ys) - y0 + pad)), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # smooth wobbly curve through points (quadratic)
    pts = []
    for i in range(len(points) - 1):
        (ax, ay), (bx, by) = points[i], points[i + 1]
        for s in np.linspace(0, 1, 20):
            pts.append((ax + (bx - ax) * s - x0 + rng.normal(0, 0.6), ay + (by - ay) * s - y0 + rng.normal(0, 0.6)))
    d.line(pts, fill=color, width=width, joint="curve")
    if head:
        (ax, ay), (bx, by) = pts[-6], pts[-1]
        ang = math.atan2(by - ay, bx - ax)
        for da in (2.6, -2.6):
            d.line([(bx, by), (bx + 34 * math.cos(ang + da), by + 34 * math.sin(ang + da))], fill=color, width=width)
    return img, (x0, y0)

def burst(n=3, L=60, color=(25, 22, 20, 255)):
    img = Image.new("RGBA", (200, 200), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    for i in range(n):
        a = math.radians(-60 + i * 35)
        x1, y1 = 100 + 30 * math.cos(a), 100 + 30 * math.sin(a)
        x2, y2 = 100 + (30 + L) * math.cos(a), 100 + (30 + L) * math.sin(a)
        mx, my = (x1 + x2) / 2 + 10 * math.cos(a + 1.57), (y1 + y2) / 2 + 10 * math.sin(a + 1.57)
        d.line([(x1, y1), (mx, my), (x2, y2)], fill=color, width=6, joint="curve")
    return img

def heart(size, color):
    s = 4; w = size * s
    img = Image.new("RGBA", (w + 60 * s, w + 60 * s), (0, 0, 0, 0))
    def shape(scale, fill):
        pts = []
        for t in np.linspace(0, 2 * math.pi, 200):
            x = 16 * math.sin(t) ** 3
            y = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
            pts.append((img.size[0] / 2 + x * w / 34 * scale, img.size[1] / 2 + y * w / 34 * scale))
        ImageDraw.Draw(img).polygon(pts, fill=fill)
    shape(1.18, (255, 255, 255, 255)); shape(1.0, color)
    img = img.resize((img.size[0] // s, img.size[1] // s), Image.LANCZOS)
    return add_shadow(img, (5, 8), 6, 0.3)

def star(size, color):
    s = 4; R = size * s / 2
    img = Image.new("RGBA", (int(R * 2.6), int(R * 2.6)), (0, 0, 0, 0))
    c = img.size[0] / 2
    def shape(r, fill):
        pts = [(c + (r if k % 2 == 0 else r * 0.45) * math.cos(-math.pi / 2 + k * math.pi / 5),
                c + (r if k % 2 == 0 else r * 0.45) * math.sin(-math.pi / 2 + k * math.pi / 5)) for k in range(10)]
        ImageDraw.Draw(img).polygon(pts, fill=fill)
    shape(R * 1.2, (255, 255, 255, 255)); shape(R, color)
    img = img.resize((img.size[0] // s, img.size[1] // s), Image.LANCZOS)
    return add_shadow(img, (5, 8), 6, 0.3)

# ---------------- element / animation system ----------------
class El:
    def __init__(self, img, cx, cy, t_in, t_out, rot=0.0, float_amp=6, float_rot=0.8, kind="pop", frames=None, z=0):
        self.img, self.cx, self.cy, self.t_in, self.t_out, self.rot = img, cx, cy, t_in, t_out, rot
        self.fa, self.fr, self.kind, self.frames, self.z = float_amp, float_rot, kind, frames, z
        self.ph = rng.uniform(0, 6.28)
    def draw(self, canvas, t, fi):
        if t < self.t_in or t > self.t_out + 0.4: return
        a_in = (t - self.t_in) / 0.45
        sc = ease_out_back(a_in)
        dx = dy = 0
        if self.kind == "slide":
            sc = 1; dx = (1 - ease_out_back(a_in, 1.2)) * (-W * 0.9 if self.cx < W / 2 else W * 0.9)
        elif self.kind == "drop":
            sc = 1; dy = (1 - ease_out_back(a_in, 1.4)) * -H * 0.6
        if t > self.t_out:                      # exit: shrink & fade quickly
            k = ease_in_out((t - self.t_out) / 0.35)
            sc *= (1 - k)
        if sc <= 0.01: return
        src = self.img
        if self.frames is not None:
            src = self.frames(t - self.t_in)
        r = self.rot + self.fr * math.sin(t * 1.9 + self.ph) + (1 - min(a_in, 1)) * 8
        im = src.rotate(r, resample=Image.BICUBIC, expand=True)
        if abs(sc - 1) > 0.002:
            im = im.resize((max(1, int(im.size[0] * sc)), max(1, int(im.size[1] * sc))), Image.BICUBIC)
        x = self.cx + dx + self.fa * 0.6 * math.sin(t * 1.3 + self.ph)
        y = self.cy + dy + self.fa * math.sin(t * 1.6 + self.ph * 1.3)
        canvas.alpha_composite(im, (int(x - im.size[0] / 2), int(y - im.size[1] / 2)))

def photo_el(clip, size, cx, cy, t_in, t_out, rot, speed=1.0, kind="pop"):
    outer, off = sticker_photo(size)
    cache = {}
    def frames(lt):
        i = min(int(max(lt, 0) * FPS * speed), len(clip) - 1)
        if i not in cache:
            cache.clear(); cache[i] = compose_photo(clip[i], outer, off)
        return cache[i]
    return El(frames(0), cx, cy, t_in, t_out, rot, 5, 0.6, kind, frames)

# ---------------- timing from transcript ----------------
words = [w for s in json.load(open("transcript.json")) for w in s["words"]]
def wt(word, after):
    for w in words:
        if w["s"] >= after - 0.05 and word.lower() in w["w"].lower():
            return w["s"] - T0
    raise KeyError(word)

S1, S2, S3 = 0.0, 23.85 - T0, 30.75 - T0     # scene starts (local time)
END = DUR

# ---------------- build scenes ----------------
print("decoding clips...", flush=True)
PH = (660, 830)
c1 = load_clip(U + "6e4e29cc-IMG_2718.MOV", 0, 5.66, PH, (0.02, 0.12, 0.96, 0.60))
c2 = load_clip(U + "d4a5c0db-IMG_2721.MOV", 0.5, 7.0, PH, (0.0, 0.18, 1.0, 0.70))
c3 = load_clip(U + "392eadeb-IMG_2720.MOV", 0, 3.94, PH, (0.0, 0.12, 1.0, 0.70))
mom = still(MAIN, 41.0, (380, 440), (0.18, 0.12, 0.64, 0.42))
kid = still(U + "d4a5c0db-IMG_2721.MOV", 9.5, (380, 440), (0.25, 0.30, 0.6, 0.45))
teacher = still(MAIN, 6.0, (380, 440), (0.15, 0.08, 0.70, 0.45))

def small_polaroid(img):
    outer, off = sticker_photo(img.size, border=16)
    return compose_photo(img, outer, off)

els = []
# Scene 1 – "Desde a primeira aula, o professor acompanha o aluno de perto..."
e1 = S2 - 0.35
els += [
    El(torn_label(["DESDE A", "PRIMEIRA AULA"], 100), 520, 300, S1 + 0.05, e1, rot=-2.5, kind="drop", z=5),
    photo_el(c1, PH, 560, 910, S1 + 0.35, e1, rot=3, speed=0.75),
    El(burst(), 930, 205, S1 + 0.5, e1, rot=10, float_amp=3),
    El(small_polaroid(teacher), 870, 1230, wt("concorre", T0) + 0.0, e1, rot=7),
    El(hand_label("acompanhamento de perto", 88), 470, 1440, wt("concorre", T0) + 0.25, e1, rot=-4, float_amp=3),
    El(hand_label("necessidades", 82, bg=(255, 214, 60, 255)), 220, 700, wt("necessidades", T0), e1, rot=-8),
    El(hand_label("dificuldades", 82, bg=(255, 255, 255, 255)), 230, 1120, wt("dificuldades", T0), e1, rot=5),
]
a_img, a_off = arrow([(150, 1390), (170, 1320), (260, 1270)])
els.append(El(a_img, a_off[0] + a_img.size[0] / 2, a_off[1] + a_img.size[1] / 2, wt("concorre", T0) + 0.35, e1, 0, 2, 0.3))

# Scene 2 – "...adaptar o ensino e respeitar o ritmo de aprendizagem de cada um."
e2 = S3 - 0.35
els += [
    El(torn_label(["ENSINO", "ADAPTADO"], 118, color=(226, 72, 60)), 540, 290, S2 + 0.05, e2, rot=2, kind="drop"),
    photo_el(c2, PH, 520, 910, S2 + 0.3, e2, rot=-3, speed=1.0, kind="slide"),
    El(small_polaroid(kid), 210, 1220, wt("ritmo", 24) - 0.3, e2, rot=-7),
    El(hand_label("no ritmo de cada um"), 600, 1440, wt("ritmo", 24), e2, rot=-3, float_amp=3),
    El(star(110, (255, 201, 40, 255)), 900, 640, S2 + 0.8, e2, rot=12),
    El(hand_label("aprendizagem", 82, bg=(255, 214, 60, 255)), 850, 1200, wt("aprendizagem", 24), e2, rot=6),
]
# Scene 3 – "Assim, cada avanço é valorizado e comemorado junto com a família."
e3 = END + 1
els += [
    El(torn_label(["CADA AVANÇO", "É COMEMORADO!"], 100), 540, 300, S3 + 0.05, e3, rot=-2, kind="drop"),
    photo_el(c3, PH, 545, 910, S3 + 0.3, e3, rot=2.5, speed=0.72),
    El(burst(), 120, 200, S3 + 0.45, e3, rot=-150, float_amp=3),
    El(star(90, (255, 201, 40, 255)), 160, 640, wt("valorizado", 30.5), e3, rot=-10),
    El(star(70, (38, 84, 196, 255)), 940, 560, wt("valorizado", 30.5) + 0.2, e3, rot=14),
    El(small_polaroid(mom), 860, 1220, wt("família", 30.5) - 0.35, e3, rot=6),
    El(hand_label("junto com a família"), 430, 1440, wt("família", 30.5) - 0.2, e3, rot=-4, float_amp=3),
    El(heart(110, (230, 57, 70, 255)), 140, 1250, wt("família", 30.5) + 0.1, e3, rot=-12),
]
els.sort(key=lambda e: e.z)

# ---------------- render ----------------
bg = paper_bg()
out = sys.argv[1] if len(sys.argv) > 1 else "motion.mp4"
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                        "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
order = sorted(range(len(els)), key=lambda i: (els[i].z, 0 if els[i].frames is not None else 1))
for fi in range(NF):
    t = fi / FPS
    # slow drifting background (sub-pixel via affine)
    ox = 80 + 50 * math.sin(t * 0.25); oy = 80 + 40 * math.cos(t * 0.21)
    frame = bg.transform((W, H), Image.AFFINE, (1, 0, ox, 0, 1, oy), resample=Image.BILINEAR).convert("RGBA")
    for i in order:
        els[i].draw(frame, t, fi)
    enc.stdin.write(frame.convert("RGB").tobytes())
    if fi % 60 == 0: print(f"frame {fi}/{NF}", flush=True)
enc.stdin.close(); enc.wait()
print("done", out)
