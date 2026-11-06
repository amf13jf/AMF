"""Paper-collage stop-motion goal (1080x1920, 24fps, drawings on twos)."""
import sys, math, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops

W, H, FPS, DUR = 1080, 1920, 24, 8.0
OUT = sys.argv[1]
PREVIEW = [float(x) for x in sys.argv[2].split(',')] if len(sys.argv) > 2 else None
R = np.random.default_rng(11)
FONTS = ["/usr/share/fonts/opentype/inter/InterDisplay-Black.otf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
         "/usr/share/fonts/truetype/freefont/FreeSansBoldOblique.ttf",
         "/usr/share/fonts/truetype/crosextra/Carlito-Bold.ttf",
         "/usr/share/fonts/truetype/liberation/LiberationMono-BoldItalic.ttf"]
YEL = (242, 194, 27)
RED = (214, 38, 61)
INK = (28, 26, 30)

clamp = lambda x, a=0, b=1: max(a, min(b, x))
def eo(x): x = clamp(x); return 1 - (1 - x) ** 3
def eio(x): x = clamp(x); return x * x * (3 - 2 * x)
def back(x): x = clamp(x); c = 2.2; return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


# ---------------- textures ----------------
def grain(h, w, amt=18, blur=0.8, seed=None):
    g = np.random.default_rng(seed).normal(0, 1, (h, w)).astype(np.float32)
    im = Image.fromarray(np.uint8(np.clip(128 + g * 40, 0, 255))).filter(ImageFilter.GaussianBlur(blur))
    return (np.asarray(im, np.float32) - 128) / 40 * amt


def paper(h, w, color, amt=10, seed=None):
    a = np.ones((h, w, 3), np.float32) * np.array(color, np.float32)
    a += grain(h, w, amt, 0.7, seed)[..., None]
    a += grain(h, w, amt * 0.8, 6, None if seed is None else seed + 1)[..., None]
    return np.clip(a, 0, 255)


def to_img(a, alpha=None):
    im = Image.fromarray(np.uint8(np.clip(a, 0, 255)))
    if alpha is not None:
        im = im.convert("RGBA"); im.putalpha(alpha)
    return im


def cutout(img, border=12, shadow=True, rough=True):
    """White paper border around an RGBA shape + soft drop shadow."""
    pad = border + 40
    base = Image.new("RGBA", (img.width + pad * 2, img.height + pad * 2), (0, 0, 0, 0))
    base.paste(img, (pad, pad), img)
    a = base.split()[3]
    if border:
        b = a.filter(ImageFilter.MaxFilter(border * 2 + 1 if border * 2 + 1 <= 41 else 41))
        if rough:
            n = Image.fromarray(np.uint8(np.clip(128 + grain(b.height, b.width, 90, 3), 0, 255)))
            b = ImageChops.multiply(b.filter(ImageFilter.GaussianBlur(3)), Image.eval(n, lambda v: min(255, v * 2)))
            b = b.point(lambda v: 255 if v > 110 else 0)
        wpaper = to_img(paper(b.height, b.width, (246, 244, 238), 6), b)
    out = Image.new("RGBA", base.size, (0, 0, 0, 0))
    if shadow:
        sa = (b if border else a).filter(ImageFilter.GaussianBlur(9)).point(lambda v: int(v * 0.45))
        sh = Image.new("RGBA", base.size, (20, 10, 0, 0)); sh.putalpha(sa)
        out.alpha_composite(sh, (10, 14))
    if border:
        out.alpha_composite(wpaper)
    out.alpha_composite(base)
    return out


def bw_texture(img_arr):
    g = img_arr.mean(axis=2, keepdims=True)
    return np.repeat(g, 3, axis=2)


# ---------------- background: grid paper ----------------
def grid_bg():
    a = paper(H, W, (238, 237, 233), 7, seed=1)
    im = to_img(a).convert("RGB")
    d = ImageDraw.Draw(im)
    for x in range(-10, W, 62):
        d.line([(x + R.uniform(-1, 1), 0), (x + R.uniform(-1, 1), H)], fill=(196, 196, 196), width=2)
    for y in range(-30, H, 62):
        d.line([(0, y + R.uniform(-1, 1)), (W, y + R.uniform(-1, 1))], fill=(196, 196, 196), width=2)
    # paper fibers / stains
    st = Image.fromarray(np.uint8(np.clip(128 + grain(H, W, 25, 40, 5), 0, 255)))
    im = Image.blend(im, Image.merge("RGB", [st] * 3), 0.08)
    return im.convert("RGBA")


BG = grid_bg()


# ---------------- sprites ----------------
def yellow_circle(r=440):
    s = r * 2 + 4
    m = Image.new("L", (s, s), 0); ImageDraw.Draw(m).ellipse([2, 2, s - 2, s - 2], fill=255)
    tex = paper(s, s, YEL, 14, seed=3)
    tex *= (1 - 0.06 * (np.asarray(Image.fromarray(np.uint8(np.clip(128 + grain(s, s, 60, 30, 9), 0, 255))), np.float32) / 255))[..., None]
    return cutout(to_img(tex, m), border=0)


def torn_strip(w, h, kind, seed):
    rng = np.random.default_rng(seed)
    edge = np.cumsum(rng.normal(0, 4, w + 1)); edge -= np.linspace(edge[0], edge[-1], w + 1); edge = edge * 1.0 + 30
    m = Image.new("L", (w, h), 0)
    pts = [(x, edge[x]) for x in range(w)] + [(w, h), (0, h)]
    ImageDraw.Draw(m).polygon(pts, fill=255)
    if kind == 'grass':
        # black & white "photo" of grass: vertical blades + mowing stripes
        n = rng.normal(0, 1, (h // 7 + 2, w)).astype(np.float32)
        blades = np.asarray(Image.fromarray(np.uint8(np.clip(128 + n * 60, 0, 255))).resize((w, h), Image.BICUBIC), np.float32)
        fine = rng.normal(0, 1, (h, w)).astype(np.float32) * 22
        y = np.arange(h)[:, None]
        stripes = 14 * np.tanh(3 * np.sin(np.arange(w)[None, :] / 95.0 + y / 400.0))
        blobs = np.asarray(Image.fromarray(np.uint8(np.clip(128 + rng.normal(0, 1, (h // 40 + 2, w // 40 + 2)) * 40, 0, 255))).resize((w, h), Image.BICUBIC), np.float32) - 128
        shade = 40 + 0.55 * blades + fine + stripes + 0.4 * blobs + 50 * (y / h)
        tex = np.repeat(shade[..., None], 3, 2) + grain(h, w, 10)[..., None]
    else:
        tex = paper(h, w, (230, 228, 220), 10, seed)
    # white torn fibre band along the top
    band = Image.new("L", (w, h), 0)
    ImageDraw.Draw(band).polygon([(x, edge[x] - 9 - abs(rng.normal(0, 4))) for x in range(w)] + [(w, h), (0, h)], fill=255)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    out.alpha_composite(to_img(paper(h, w, (247, 245, 240), 5), band))
    out.alpha_composite(to_img(tex, m))
    return out


def goal_sprite(w=780, h=430, bulge=0.0, cx=0.5, cy=0.55):
    im = Image.new("RGBA", (w + 60, h + 60), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    ox, oy = 30, 30
    # net mesh (perspective-ish, with bulge)
    def P(u, v):
        x, y = u * w, v * h
        dx, dy = x - cx * w, y - cy * h
        f = math.exp(-(dx * dx + dy * dy) / (2 * 150 ** 2))
        return (ox + x + dx * bulge * f * 0.6, oy + y + dy * bulge * f * 0.6 + 40 * bulge * f)
    N = 22
    for i in range(N + 1):
        u = i / N
        d.line([P(u, v / 30) for v in range(31)], fill=(70, 70, 75, 170), width=2)
    for j in range(13):
        v = j / 9
        d.line([P(u / 40, v) for u in range(41)], fill=(70, 70, 75, 170), width=2)
    # posts (white painted metal)
    d.rectangle([ox - 18, oy - 18, ox + w + 18, oy + 6], fill=(250, 250, 250, 255))
    d.rectangle([ox - 18, oy - 18, ox + 6, oy + h], fill=(250, 250, 250, 255))
    d.rectangle([ox + w - 6, oy - 18, ox + w + 18, oy + h], fill=(250, 250, 250, 255))
    # post shading line
    d.line([(ox - 18, oy + 6), (ox + w + 18, oy + 6)], fill=(170, 170, 175, 255), width=4)
    posts = Image.new("RGBA", im.size, (0, 0, 0, 0)); pd = ImageDraw.Draw(posts)
    pd.rectangle([ox - 18, oy - 18, ox + w + 18, oy + 6], fill=(250, 250, 250, 255))
    pd.rectangle([ox - 18, oy - 18, ox + 6, oy + h], fill=(250, 250, 250, 255))
    pd.rectangle([ox + w - 6, oy - 18, ox + w + 18, oy + h], fill=(250, 250, 250, 255))
    netonly = ImageChops.subtract(im.split()[3], posts.split()[3])
    net = im.copy(); net.putalpha(netonly)
    out = cutout(posts, border=8, rough=True)
    pad = (out.width - im.width) // 2
    sh = net.split()[3].filter(ImageFilter.GaussianBlur(4)).point(lambda v: int(v * 0.25))
    shi = Image.new("RGBA", net.size, (0, 0, 0, 0)); shi.putalpha(sh)
    out.alpha_composite(shi, (pad + 8, pad + 10)); out.alpha_composite(net, (pad, pad))
    return out


def ball_img(Rr, rot, xeyes=0.0, eyes=True, t=0):
    S = 2 * Rr + 2
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    x = (xx - Rr) / Rr; y = (yy - Rr) / Rr
    r2 = x * x + y * y; inside = r2 <= 1
    z = np.sqrt(np.clip(1 - r2, 0, 1))
    n = np.stack([x, -y, z], -1)
    nb = n @ rot.T
    phi = (1 + 5 ** .5) / 2
    ico = [(0, s1, s2 * phi) for s1 in (-1, 1) for s2 in (-1, 1)]
    ico = ico + [(b, c, a) for a, b, c in ico] + [(c, a, b) for a, b, c in ico]
    dod = [(a, b, c) for a in (-1, 1) for b in (-1, 1) for c in (-1, 1)]
    dod += [(0, s1 / phi, s2 * phi) for s1 in (-1, 1) for s2 in (-1, 1)]
    dod += [(s2 * phi, 0, s1 / phi) for s1 in (-1, 1) for s2 in (-1, 1)]
    dod += [(s1 / phi, s2 * phi, 0) for s1 in (-1, 1) for s2 in (-1, 1)]
    C = np.array(ico + dod, np.float32); C /= np.linalg.norm(C, axis=1, keepdims=True)
    dots = nb @ C.T
    srt = np.sort(dots, axis=-1)
    idx = np.argmax(dots, -1)
    base = np.where(idx < 12, 45.0, 232.0)
    seam = (srt[..., -1] - srt[..., -2]) < 0.012
    base = np.where(seam, 110.0, base)
    L = np.array([-0.45, 0.55, 0.7]); L /= np.linalg.norm(L)
    lam = np.clip(n @ L, 0, 1)
    spec = np.clip(n @ (L + np.array([0, 0, 1])) / np.linalg.norm(L + np.array([0, 0, 1])), 0, 1) ** 30
    sh = base * (0.35 + 0.75 * lam) + 120 * spec
    sh += grain(S, S, 8)
    rgb = np.repeat(np.clip(sh, 0, 255)[..., None], 3, 2)
    a = Image.fromarray(np.uint8(inside * 255)).filter(ImageFilter.GaussianBlur(0.8))
    im = to_img(rgb, a)
    if eyes:
        d = ImageDraw.Draw(im)
        for side in (-1, 1):
            ex, ey = Rr + side * Rr * 0.32, Rr * 0.82
            er = Rr * 0.2
            if xeyes > 0:
                marker_x(d, ex, ey, er * 1.2, YEL, int(Rr * 0.09), seed=int(side + 5))
            else:
                d.ellipse([ex - er, ey - er * 1.15, ex + er, ey + er * 1.15], fill=(250, 250, 250), outline=INK, width=max(3, int(Rr * 0.04)))
                px, py = ex + math.sin(t * 9 + side) * er * 0.4, ey + math.cos(t * 7) * er * 0.4
                d.ellipse([px - er * 0.45, py - er * 0.45, px + er * 0.45, py + er * 0.45], fill=INK)
        # scribbled grin
        d.arc([Rr * 0.65, Rr * 1.05, Rr * 1.35, Rr * 1.5], 10, 170, fill=INK, width=max(3, int(Rr * 0.05)))
    return cutout(im, border=10)


def marker_x(d, cx, cy, s, col, w, seed=0):
    rng = np.random.default_rng(seed)
    for k in range(3):
        j = lambda: rng.uniform(-s * 0.12, s * 0.12)
        d.line([(cx - s + j(), cy - s + j()), (cx + s + j(), cy + s + j())], fill=col, width=w)
        d.line([(cx + s + j(), cy - s + j()), (cx - s + j(), cy + s + j())], fill=col, width=w)


def scribble_x(size, seed):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    marker_x(ImageDraw.Draw(im), size / 2, size / 2, size * 0.36, YEL + (235,), max(6, size // 12), seed)
    return im


def foot_sprite():
    """Kraft-paper leg + foot (side view, toes to the right), striped sock. Anchor = top of leg."""
    w, h = 440, 620
    m = Image.new("L", (w, h), 0); d = ImageDraw.Draw(m)
    d.rounded_rectangle([90, 0, 210, 470], 50, fill=255)          # shin
    d.ellipse([60, 380, 260, 560], fill=255)                       # heel
    d.rounded_rectangle([140, 430, 390, 555], 60, fill=255)        # foot
    for i, (tx, ty, r) in enumerate([(380, 470, 36), (352, 440, 24), (320, 432, 20), (290, 430, 17), (262, 432, 14)]):
        d.ellipse([tx - r, ty - r, tx + r, ty + r], fill=255)
    kraft = paper(h, w, (196, 150, 104), 16, seed=21)
    fib = grain(h, w, 22, 1.2, 22)
    kraft[..., 0] += fib * 0.6; kraft[..., 1] += fib * 0.5; kraft[..., 2] += fib * 0.3
    im = to_img(kraft, m)
    dd = ImageDraw.Draw(im)
    # sock: paper stripes
    sockm = Image.new("L", (w, h), 0); ImageDraw.Draw(sockm).rounded_rectangle([86, 0, 214, 300], 40, fill=255)
    sock = to_img(paper(h, w, (245, 243, 236), 8), ImageChops.multiply(sockm, m))
    im.alpha_composite(sock)
    for y in (40, 90, 140):
        dd.rectangle([86, y, 214, y + 26], fill=RED + (255,))
    dd.rectangle([86, 190, 214, 206], fill=INK + (255,))
    # marker doodles: toenails + ankle bone
    for tx, ty, r in [(392, 462, 12), (360, 432, 8)]:
        dd.arc([tx - r, ty - r, tx + r, ty + r], 200, 340, fill=INK, width=4)
    dd.arc([140, 400, 190, 440], 180, 360, fill=(120, 80, 50), width=4)
    return cutout(im, border=11)


def heart_sprite(s, col, seed):
    S = int(s)
    m = Image.new("L", (S, S), 0); d = ImageDraw.Draw(m)
    pts = []
    for i in range(200):
        t = i / 200 * 2 * math.pi
        x = 16 * math.sin(t) ** 3
        y = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
        pts.append((S / 2 + x * S / 36, S / 2 + y * S / 36 - S * 0.03))
    d.polygon(pts, fill=255)
    im = to_img(paper(S, S, col, 14, seed), m)
    c = cutout(im, border=9)
    # masking tape
    tape = Image.new("RGBA", (int(S * 0.55), int(S * 0.17)), (232, 222, 190, 190))
    tape = tape.rotate(np.random.default_rng(seed).uniform(-25, 25), expand=True, resample=Image.BICUBIC)
    c.alpha_composite(tape, (c.width // 2 - tape.width // 2, int(c.height * 0.2)))
    return c


def stamp_foot(s, seed, col=INK):
    S = int(s)
    m = Image.new("L", (S, int(S * 1.5)), 0); d = ImageDraw.Draw(m)
    k = S / 100
    d.ellipse([22 * k, 45 * k, 82 * k, 140 * k], fill=255)
    for tx, ty, r in [(30, 28, 15), (52, 18, 11), (68, 20, 9.5), (81, 28, 8), (90, 40, 7)]:
        d.ellipse([(tx - r) * k, (ty - r) * k, (tx + r) * k, (ty + r) * k], fill=255)
    n = Image.fromarray(np.uint8(np.clip(128 + grain(m.height, m.width, 70, 1.5, seed), 0, 255)))
    m = ImageChops.multiply(m, n.point(lambda v: 255 if v > 70 else 60))
    ink = Image.new("RGBA", m.size, col + (0,)); ink.putalpha(m.point(lambda v: int(v * 0.9)))
    return ink


def letter_piece(ch, seed):
    rng = np.random.default_rng(seed)
    style = seed % 5
    bgc, fg = [((245, 243, 236), INK), (YEL, INK), (INK, (245, 243, 236)), (RED, (250, 250, 250)), ((205, 205, 200), INK)][style]
    f = ImageFont.truetype(FONTS[seed % len(FONTS)], int(rng.uniform(150, 200)))
    bb = f.getbbox(ch)
    w, h = bb[2] - bb[0] + 50, bb[3] - bb[1] + 50
    tex = paper(h, w, bgc, 12, seed)
    if style == 4:  # newsprint: faint tiny text lines
        for y in range(6, h, 9): tex[y:y + 2, 6:-6] -= rng.uniform(20, 45)
    m = Image.new("L", (w, h), 0)
    poly = [(rng.uniform(0, 8), rng.uniform(0, 8)), (w - rng.uniform(0, 8), rng.uniform(0, 8)),
            (w - rng.uniform(0, 8), h - rng.uniform(0, 8)), (rng.uniform(0, 8), h - rng.uniform(0, 8))]
    ImageDraw.Draw(m).polygon(poly, fill=255)
    im = to_img(tex, m)
    ImageDraw.Draw(im).text((25 - bb[0], 25 - bb[1]), ch, font=f, fill=fg)
    return cutout(im, border=0)


def control_bar():
    w, h = 560, 260
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    for (x0, y0, x1, y1) in [(20, 110, 540, 150), (250, 10, 290, 250)]:
        bw, bh = x1 - x0, y1 - y0
        wood = paper(bh, bw, (205, 160, 105), 10, 31)
        stripes = np.sin(np.arange(bw if bw > bh else bh) / 6.0 + grain(1, bw if bw > bh else bh, 2, 1)[0]) * 10
        if bw > bh: wood += stripes[None, :, None] * 0 + grain(bh, bw, 6, 0.5)[..., None]
        im.alpha_composite(to_img(wood, Image.new("L", (bw, bh), 255)), (x0, y0))
    im = im.rotate(-12, expand=True, resample=Image.BICUBIC)
    return cutout(im, border=0)


# ---------------- prebuilt ----------------
CIRCLE = yellow_circle()
GRASS = torn_strip(1200, 560, 'grass', 7)
FOOT = foot_sprite()
BAR = control_bar()
COLS = [RED, YEL, RED, (250, 120, 150), RED, YEL, RED, (250, 120, 150)]
HEARTS = [heart_sprite(R.uniform(130, 190), COLS[i], 40 + i) for i in range(8)]
HEART_BIG = heart_sprite(520, RED, 77)
STAMPS = [stamp_foot(120, 60 + i, (245, 243, 236)) for i in range(10)]
LETTERS = [letter_piece(c, 100 + i) for i, c in enumerate("GOOOL!")]
YSHEET = torn_strip(1300, 2300, 'paper', 3)
yarr = np.asarray(YSHEET).astype(np.float32); yarr[..., :3] = np.where(yarr[..., 3:4] > 0, np.clip(yarr[..., :3] * 0 + np.array(YEL) + grain(yarr.shape[0], yarr.shape[1], 12)[..., None], 0, 255), 0)
YSHEET = Image.fromarray(np.uint8(yarr))


def rotmat(a, b):
    ca, sa, cb, sb = math.cos(a), math.sin(a), math.cos(b), math.sin(b)
    Rx = np.array([[1, 0, 0], [0, ca, -sa], [0, sa, ca]]); Ry = np.array([[cb, 0, sb], [0, 1, 0], [-sb, 0, cb]])
    return (Rx @ Ry).astype(np.float32)


def place(canvas, spr, cx, cy, scale=1.0, rot=0.0, alpha=1.0, anchor=(0.5, 0.5)):
    if scale <= 0.01 or alpha <= 0.01: return
    s = spr
    if abs(scale - 1) > 1e-3: s = s.resize((max(1, int(s.width * scale)), max(1, int(s.height * scale))), Image.BICUBIC)
    ax, ay = s.width * anchor[0], s.height * anchor[1]
    if rot:
        # rotate around anchor: pad so anchor is centre
        pw = int(max(ax, s.width - ax) * 2); ph = int(max(ay, s.height - ay) * 2)
        p = Image.new("RGBA", (pw, ph), (0, 0, 0, 0)); p.paste(s, (int(pw / 2 - ax), int(ph / 2 - ay)))
        s = p.rotate(rot, expand=True, resample=Image.BICUBIC); ax, ay = s.width / 2, s.height / 2
    if alpha < 1:
        a = s.split()[3].point(lambda v: int(v * alpha)); s = s.copy(); s.putalpha(a)
    canvas.alpha_composite(s, (int(cx - ax), int(cy - ay)))


def boil(t, key, amp=3.0):
    d = int(t * 12)  # new drawing 12x per second
    r = np.random.default_rng(hash((d, key)) % (2 ** 32))
    return r.uniform(-amp, amp), r.uniform(-amp, amp), r.uniform(-0.8, 0.8)


def steps(x, n=6):  # stop-motion quantised easing
    return math.floor(clamp(x) * n) / n


# ---------------- timeline ----------------
T_KICK, T_HIT, T_END = 2.70, 3.25, 8.0
PIV = (330, 120); LEG = 470
BALL0 = (720, 900)
GOAL = (540, 1330)
HEART_POS = [(150, 380), (930, 330), (120, 1000), (960, 920), (240, 170), (820, 610), (90, 640), (990, 1420)]
STAMP_PATH = [(95 + i * 127, 1770 - 50 * math.sin(i * 0.7)) for i in range(8)]
ball_cache = {}


def frame(t):
    # quantise time to drawings (on twos) -> stop-motion feel
    tq = math.floor(t * 12) / 12
    c = BG.copy()
    sx, sy = 0, 0
    if T_HIT <= tq < T_HIT + 0.35:
        a = 22 * (1 - (tq - T_HIT) / 0.35); r = np.random.default_rng(int(tq * 100)); sx, sy = r.uniform(-a, a), r.uniform(-a, a)
    if T_KICK <= tq < T_KICK + 0.15:
        sx += 8 * (1 if int(tq * 24) % 2 else -1)

    # yellow circle
    k = back((tq - 0.15) / 0.35)
    bx, by, br = boil(tq, 'c', 2)
    place(c, CIRCLE, 540 + sx + bx, 1180 + sy + by, scale=k, rot=br * 0.3)

    # ransom/doodles behind? -> marker dashed trajectory
    if 1.7 <= tq < T_HIT + 0.2:
        d = ImageDraw.Draw(c)
        prog = clamp((tq - 1.7) / 0.5)
        pts = []
        for i in range(int(40 * prog)):
            u = i / 40
            x = BALL0[0] + (GOAL[0] + 20 - BALL0[0]) * u + 200 * math.sin(math.pi * u)
            y = BALL0[1] + (GOAL[1] - BALL0[1]) * u - 120 * math.sin(math.pi * u)
            pts.append((x + sx, y + sy))
        for i in range(0, len(pts) - 1, 2):
            d.line([pts[i], pts[i + 1]], fill=INK, width=7)
        if prog >= 1 and len(pts) > 2:
            ex, ey = pts[-1]; d.line([(ex - 30, ey - 34), (ex, ey), (ex + 34, ey - 22)], fill=INK, width=7)

    # goal
    bul = 0.0
    if tq >= T_HIT: bul = 1.0 * math.exp(-(tq - T_HIT) * 4) * math.cos((tq - T_HIT) * 22)
    gy = -900 * (1 - eo(steps((tq - 0.55) / 0.4, 5))) if tq < 1.0 else 0
    if tq >= 0.55:
        key = round(bul, 2)
        g = goal_sprite(bulge=key)
        bx, by, br = boil(tq, 'g', 2)
        place(c, g, GOAL[0] + sx + bx, GOAL[1] + gy + sy + by, rot=br * 0.5)

    # ball
    if tq >= 0.8:
        if tq < T_KICK:
            bs = back((tq - 0.8) / 0.3); bxp, byp = BALL0; byp += 14 * math.sin(tq * 6); rot = rotmat(0.3, tq * 0.6); r_ = 110; xe = 0
        elif tq < T_HIT:
            u = (tq - T_KICK) / (T_HIT - T_KICK)
            bxp = BALL0[0] + (GOAL[0] + 20 - BALL0[0]) * u + 200 * math.sin(math.pi * u)
            byp = BALL0[1] + (GOAL[1] - BALL0[1]) * u - 120 * math.sin(math.pi * u)
            bs = 1.0; r_ = int(110 * (1 - 0.4 * u)); rot = rotmat(u * 9, u * 7); xe = 0
        else:
            u = tq - T_HIT
            bxp = GOAL[0] + 20; byp = GOAL[1] + 70 - abs(math.sin(u * 7)) * 60 * math.exp(-u * 1.5)
            bs = 1.0; r_ = 66; rot = rotmat(9, 7); xe = 1
        keyb = (r_, round(tq, 3), xe)
        img = ball_img(r_, rot, xeyes=xe, t=tq)
        bx, by, br = boil(tq, 'b', 3)
        if T_KICK <= tq < T_HIT:  # marker speed lines
            d = ImageDraw.Draw(c)
            for i in range(3):
                d.line([(bxp - 60 - 40 * i + sx, byp - 70 + 45 * i + sy), (bxp - 150 - 40 * i + sx, byp - 120 + 45 * i + sy)], fill=INK, width=8)
        place(c, img, bxp + sx + bx, byp + sy + by, scale=bs, rot=br * 3)

    # grass strip (in front of the goal)
    gk = eo(steps((tq - 0.35) / 0.35, 5))
    bx, by, br = boil(tq, 'gr', 2)
    place(c, GRASS, 540 + sx + bx, 1920 + 280 - 560 * gk + 120 + sy + by - 0, anchor=(0.5, 0.5))

    # puppet foot on strings
    if tq >= 1.0:
        drop = -1100 * (1 - eo(steps((tq - 1.0) / 0.5, 6)))
        if tq < 2.3: th = 6 * math.sin(tq * 9)
        elif tq < T_KICK - 0.1: th = -34 * eio((tq - 2.3) / 0.3)
        elif tq < T_KICK + 0.1: th = -34 + 62 * eio((tq - (T_KICK - 0.1)) / 0.2)
        elif tq < T_HIT + 0.2: th = 28 - 10 * eio((tq - T_KICK - 0.1) / 0.4)
        else: th = 14 * math.sin((tq - T_HIT) * 8)  # happy dance
        if tq > T_HIT + 0.2: drop -= 380 * eo(steps((tq - T_HIT - 0.2) / 0.4, 5))
        bx, by, br = boil(tq, 'f', 2)
        px, py = PIV[0] + sx + bx, PIV[1] + drop + sy + by
        ang = math.radians(-th)
        lx, ly = px, py + 190                       # top of the shin
        def rotp(x, y): return (lx + x * math.cos(ang) - y * math.sin(ang), ly + x * math.sin(ang) + y * math.cos(ang))
        d = ImageDraw.Draw(c)
        for a_, b_ in [((px - 245, py + 40), rotp(0, 30)), ((px + 245, py - 30), rotp(235, 450)), ((px + 20, py - 90), rotp(-70, 440))]:
            d.line([a_, b_], fill=(55, 55, 55), width=3)
        anchor = ((150 + 51) / FOOT.width, (0 + 51) / FOOT.height)
        place(c, FOOT, lx, ly, rot=th, anchor=anchor)
        place(c, BAR, px, py, rot=th * 0.2 + br)

    # kick burst (yellow marker rays)
    if T_KICK - 0.02 <= tq < T_KICK + 0.35:
        d = ImageDraw.Draw(c)
        cx, cy = BALL0[0] - 90, BALL0[1] - 10
        rr = np.random.default_rng(int(tq * 12))
        for i in range(11):
            a = i / 11 * 2 * math.pi + rr.uniform(-0.2, 0.2)
            r0, r1 = 120 + rr.uniform(0, 30), 230 + rr.uniform(0, 80)
            d.line([(cx + math.cos(a) * r0, cy + math.sin(a) * r0), (cx + math.cos(a) * r1, cy + math.sin(a) * r1)], fill=YEL, width=16)

    # hearts taped onto the grid
    for i, (hx, hy) in enumerate(HEART_POS):
        t0 = T_HIT + 0.15 + i * 0.09
        if tq < t0: continue
        k = back((tq - t0) / 0.25)
        bx, by, br = boil(tq, ('h', i), 2.5)
        place(c, HEARTS[i], hx + sx + bx, hy + sy + by - 10 * math.sin(tq * 3 + i), scale=k, rot=(i % 3 - 1) * 14 + br * 2)

    # yellow scribble X marks (like the reference), over the goal corners
    if tq >= T_HIT + 0.1:
        for j, (xx, yy, s) in enumerate([(205, 1150, 170), (880, 1160, 150)]):
            k = clamp((tq - T_HIT - 0.1 - j * 0.1) / 0.17)
            if k > 0:
                place(c, scribble_x(s, 300 + j + int(tq * 12) % 3), xx + sx, yy + sy, scale=k)

    # ransom letters GOOOL!
    for i, L in enumerate(LETTERS):
        t0 = T_HIT + 0.12 + i * 0.12
        if tq < t0: continue
        k = back((tq - t0) / 0.2)
        bx, by, br = boil(tq, ('L', i), 3)
        x = 540 + (i - 2.5) * 158
        place(c, L, x + sx + bx, 700 + (i % 2) * 34 + sy + by, scale=k * 0.95, rot=[-8, 6, -4, 9, -6, 12][i] + br * 2)

    # footprint stamps walking across the bottom
    for i, (fx, fy) in enumerate(STAMP_PATH):
        t0 = 4.1 + i * 0.17
        if tq < t0: continue
        sq = 1.25 if tq - t0 < 0.08 else 1.0
        place(c, STAMPS[i], fx, fy + (i % 2) * 60, scale=sq * 0.85, rot=-90 + (i % 2) * 10)

    # ending: yellow torn sheet wipes up, big taped heart + stamp
    if tq >= 6.6:
        k = eo(steps((tq - 6.6) / 0.45, 6))
        place(c, YSHEET, 540, 1920 + 1150 - 2150 * k)
        if tq >= 7.1:
            kh = back((tq - 7.1) / 0.25)
            bx, by, br = boil(tq, 'H', 3)
            place(c, HEART_BIG, 540 + bx, 900 + by, scale=kh, rot=-6 + br * 2)
            if tq >= 7.4:
                place(c, stamp_foot(220, 999), 780, 1330, scale=1.15 if tq < 7.48 else 1.0, rot=-25)
            if tq >= 7.25:
                place(c, ball_img(120, rotmat(9, 7), xeyes=1, t=tq), 330, 1300, scale=back((tq - 7.25) / 0.25), rot=12)
                d = ImageDraw.Draw(c)
    return c.convert("RGB")


if PREVIEW:
    for t in PREVIEW:
        frame(t).save(f"{OUT}/c_{t}.jpg", quality=85)
    sys.exit()

ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                       "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", OUT], stdin=subprocess.PIPE)
prev_q, prev_buf = None, None
for f in range(int(DUR * FPS)):
    t = f / FPS
    q = math.floor(t * 12)
    if q != prev_q:
        prev_buf = frame(t).tobytes(); prev_q = q
    ff.stdin.write(prev_buf)
ff.stdin.close(); ff.wait()
print("done")
