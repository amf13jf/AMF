import subprocess, sys, math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

SRC = sys.argv[1]
OUT = sys.argv[2]
W, H, FPS = 1080, 1920, 30
FONT_BLACK = "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf"
FONT_BLACK_IT = "/usr/share/fonts/opentype/inter/InterDisplay-BlackItalic.otf"
FONT_BOLD = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
ACCENT = (215, 255, 58)
WHITE = (255, 255, 255)


def decode(crop, ss, t, w, h):
    cmd = ["ffmpeg", "-v", "error", "-ss", str(ss), "-i", SRC, "-t", str(t),
           "-vf", f"{crop},scale={w}:{h},fps={FPS}", "-pix_fmt", "rgb24", "-f", "rawvideo", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    n = len(raw) // (w * h * 3)
    return [Image.frombuffer("RGB", (w, h), raw[i * w * h * 3:(i + 1) * w * h * 3]) for i in range(n)]


# Portrait-mode gameplay (clean, after player controls disappear) and landscape celebration
P = decode("crop=1760:990:202:274", 3.5, 3.2, 1920, 1080)
L = decode("crop=2160:1190:0:1330", 0.0, 1.9, 2160, 1190)
print("frames", len(P), len(L), file=sys.stderr)


def ease_out(x):
    x = min(max(x, 0), 1); return 1 - (1 - x) ** 3


def ease_io(x):
    x = min(max(x, 0), 1); return x * x * (3 - 2 * x)


def background(img):
    small = img.resize((img.width // 16, img.height // 16), Image.BILINEAR)
    small = small.filter(ImageFilter.GaussianBlur(3))
    s = max(W / small.width, H / small.height) * 1.1
    bg = small.resize((int(small.width * s), int(small.height * s)), Image.BILINEAR)
    l, t = (bg.width - W) // 2, (bg.height - H) // 2
    bg = bg.crop((l, t, l + W, t + H))
    return ImageEnhance.Brightness(bg).enhance(0.45)


VIGNETTE = None
def vignette():
    global VIGNETTE
    if VIGNETTE is None:
        y, x = np.mgrid[0:H, 0:W]
        d = np.sqrt(((x - W / 2) / (W / 2)) ** 2 + ((y - H / 2) / (H / 2)) ** 2)
        a = np.clip((d - 0.75) * 0.9, 0, 0.75)
        VIGNETTE = Image.fromarray((a * 255).astype(np.uint8), "L")
    return VIGNETTE


def compose(img, crop_box, z, fx, fy, cy=H / 2, shake=0.0):
    """img cropped to crop_box, scaled to width W*z; (fx,fy) = focal point (0..1) kept near centre."""
    src = img.crop(crop_box)
    canvas = background(src)
    fw = int(W * z); fh = int(src.height * fw / src.width)
    fg = src.resize((fw, fh), Image.BILINEAR)
    # Visible window: fg is clipped to a 16:9-ish band of height = min(fh, W*z*0.5625) around cy
    x = W / 2 - fx * fw + (0.5 * fw - W / 2) * 0  # focal to centre
    x = W / 2 - fx * fw
    x = min(0, max(W - fw, x)) if fw >= W else (W - fw) / 2
    y = cy - fy * fh
    if shake:
        x += random.uniform(-shake, shake); y += random.uniform(-shake, shake)
    canvas.paste(fg, (int(x), int(y)))
    return canvas, (int(y), int(y + fh))


def text_img(txt, font_path, size, fill, stroke=0, stroke_fill=(0, 0, 0)):
    f = ImageFont.truetype(font_path, size)
    bb = f.getbbox(txt, stroke_width=stroke)
    im = Image.new("RGBA", (bb[2] - bb[0] + 40, bb[3] - bb[1] + 40), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((20 - bb[0], 20 - bb[1]), txt, font=f, fill=fill,
                            stroke_width=stroke, stroke_fill=stroke_fill)
    return im


def shadowed(im, r=14, alpha=170):
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    a = im.split()[3].filter(ImageFilter.GaussianBlur(r)).point(lambda v: v * alpha // 255)
    sh.putalpha(a)
    out = Image.new("RGBA", (im.width, im.height), (0, 0, 0, 0))
    out.alpha_composite(sh, (0, 6)); out.alpha_composite(im)
    return out


def put(canvas, im, cx, cy, scale=1.0, alpha=1.0, rot=0):
    if alpha <= 0.01 or scale <= 0.01:
        return
    if scale != 1.0:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BILINEAR)
    if rot:
        im = im.rotate(rot, resample=Image.BICUBIC, expand=True)
    if alpha < 1:
        a = im.split()[3].point(lambda v: int(v * alpha)); im = im.copy(); im.putalpha(a)
    canvas.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))


def bar(canvas, x, y, w, h, color, alpha=1.0):
    d = ImageDraw.Draw(canvas, "RGBA")
    d.rectangle([x, y, x + w, y + h], fill=color + (int(255 * alpha),))


# Pre-rendered text
T_MATCH = shadowed(text_img("AJAX 2 x 3 TOTTENHAM", FONT_BLACK, 78, WHITE))
T_SUB = shadowed(text_img("SEMIFINAL  •  CHAMPIONS 2019", FONT_BOLD, 40, ACCENT))
T_MIN = text_img("90+6'", FONT_BLACK_IT, 64, (10, 20, 40))
T_GOAL = shadowed(text_img("LUUUUCAAAAS!", FONT_BLACK_IT, 118, WHITE, stroke=6, stroke_fill=(10, 20, 40)), r=22, alpha=200)
T_GOAL_GLOW = text_img("LUUUUCAAAAS!", FONT_BLACK_IT, 118, ACCENT, stroke=6, stroke_fill=ACCENT)
T_NAME = shadowed(text_img("LUCAS MOURA", FONT_BLACK, 110, WHITE))
T_HAT = shadowed(text_img("HAT-TRICK HISTÓRICO", FONT_BOLD, 52, ACCENT))

out = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                        "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
                        "-crf", "17", "-pix_fmt", "yuv420p", OUT], stdin=subprocess.PIPE)

FULL_P = (0, 200, 1920, 1080)  # drop the "10 narracoes" badge
frames = []
# ---- Segment 1: build-up, src 3.5 -> 6.0 at 1x (75 frames)
N1 = 75
# ---- Segment 2: slow motion src 6.0 -> 6.7 at 0.5x (blended, 42 frames); flash at src 6.45
N2 = 42
# ---- Segment 3: celebration src 0.0 -> 0.5 (15) + 0.5 -> 1.9 (42), outro 15
N3a, N3b, N4 = 15, 42, 18
TOTAL = N1 + N2 + N3a + N3b + N4
FLASH = N1 + int((6.45 - 6.0) * FPS * 2)  # output frame index of the goal
print("total", TOTAL, "flash", FLASH, file=sys.stderr)

last = None
for f in range(TOTAL):
    t = f / FPS
    if f < N1:
        k = f / N1
        z = 1.0 + 0.30 * ease_io(k)
        canvas, (top, bot) = compose(P[f], FULL_P, z, 0.5, 0.5 + 0.05 * k)
    elif f < N1 + N2:
        k = (f - N1) / N2
        s = 75 + (f - N1) / 2
        i0 = min(int(s), len(P) - 1); i1 = min(i0 + 1, len(P) - 1); a = s - int(s)
        img = Image.blend(P[i0], P[i1], a) if a else P[i0]
        z = 1.30 + 0.75 * ease_io(k)
        sh = 22 * max(0, 1 - (f - FLASH) / 12) if f >= FLASH else 0
        canvas, (top, bot) = compose(img, FULL_P, z, 0.5, 0.55 + 0.15 * ease_io(k), shake=sh)
    elif f < N1 + N2 + N3a:
        j = f - N1 - N2
        sh = 14 * (1 - j / N3a)
        canvas, (top, bot) = compose(L[j], (0, 0, 2160, 1190), 1.75, 0.38, 0.55, shake=sh)
    elif f < N1 + N2 + N3a + N3b:
        j = f - N1 - N2 - N3a
        k = j / N3b
        # crop away the phone-notification area (top ~40% of the frame)
        canvas, (top, bot) = compose(L[N3a + j], (0, 480, 2160, 1190), 1.5 + 0.2 * k, 0.45, 0.5, cy=H * 0.47)
    else:
        canvas = last.copy(); top, bot = last_tb
    last = canvas; last_tb = (top, bot)
    canvas = canvas.convert("RGBA")
    canvas.alpha_composite(Image.merge("RGBA", (*[Image.new("L", (W, H), 0)] * 3, vignette())))

    # ---------- overlays
    if f < N1 + 8:
        k_in = ease_out(t / 0.5)
        k_out = 1 - ease_io((f - (N1 - 6)) / 14)
        a = min(k_in, k_out)
        y0 = max(160, top - 230)
        put(canvas, T_MATCH, W / 2 - 400 * (1 - k_in), y0 + 40, alpha=a)
        put(canvas, T_SUB, W / 2 + 400 * (1 - ease_out((t - 0.15) / 0.5)), y0 + 120, alpha=min(ease_out((t - 0.15) / 0.5), k_out))
        # minute badge at the bottom
        kb = ease_out((t - 0.5) / 0.4)
        if kb > 0:
            bw, bh = T_MIN.width + 30, T_MIN.height
            bx, by = W / 2 - bw / 2, min(H - 300, bot + 90) - bh / 2 + 60 * (1 - kb)
            bar(canvas, int(bx), int(by), int(bw * kb), int(bh), ACCENT, alpha=k_out)
            put(canvas, T_MIN, W / 2, by + bh / 2, alpha=kb * k_out)

    if f >= FLASH:
        g = f - FLASH
        # white flash
        fa = max(0, 1 - g / 7)
        if fa > 0:
            canvas.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(235 * fa))))
        end = N1 + N2 + N3a + 10
        if f < end + 8:
            pop = 1.0 + 0.6 * max(0, 1 - g / 6) ** 2 if g < 6 else 1.0 + 0.02 * math.sin(g * 0.9)
            a = 1 - ease_io((f - end) / 8)
            jx = random.uniform(-6, 6) if g < 14 else 0
            cyg = H * 0.2
            put(canvas, T_GOAL_GLOW.filter(ImageFilter.GaussianBlur(18)), W / 2 + jx, cyg, scale=pop * 0.72, alpha=a * 0.8, rot=6)
            put(canvas, T_GOAL, W / 2 + jx, cyg, scale=pop * 0.72, alpha=a, rot=6)

    s4 = N1 + N2 + N3a + 6
    if f >= s4:
        g = f - s4
        k = ease_out(g / 12)
        kh = ease_out((g - 5) / 12)
        fade = 1 - ease_io((f - (TOTAL - 8)) / 8)
        ytxt = H * 0.74
        bar(canvas, int(W / 2 - 300 * k), int(ytxt - 90), int(600 * k), 8, ACCENT, alpha=fade)
        put(canvas, T_NAME, W / 2, ytxt + 20 * (1 - k), scale=0.8 + 0.2 * k, alpha=k * fade)
        put(canvas, T_HAT, W / 2, ytxt + 110 + 30 * (1 - kh), alpha=kh * fade)

    if f >= TOTAL - 10:
        canvas.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * ease_io((f - (TOTAL - 10)) / 10)))))

    out.stdin.write(canvas.convert("RGB").tobytes())
    if f in (10, 60, 100, FLASH + 2, 140, 170, 200):
        canvas.convert("RGB").save(f"{sys.argv[3]}/chk_{f:03d}.jpg", quality=80)

out.stdin.close(); out.wait()
print("done", TOTAL / FPS, file=sys.stderr)
