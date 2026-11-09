import json, re
from fontTools.ttLib import TTFont

W_OUT, H_OUT = 1080, 1920
FPS = 30
FONT = "/root/.fonts/Montserrat-800.ttf"
EM = 70                 # visual em size in px (matches reference)
FS = round(EM * 1.562)  # libass sizes by win ascent+descent
MAX_W = 940             # max line width in px -> guarantees a single line
SUB_Y = 1160            # baseline-ish position (vertical center of the line)

# ---------- Corrected transcript (segment index -> text) ----------
fixes = [  # (substring of whisper text, corrected full segment text)
    ("Meu nome é Ana Clara", "Boa noite, tudo bem? Meu nome é Ana Clara, em que eu posso ajudar?"),
    ("nosso mesanino", "Esse aqui é o nosso mezanino, onde vocês ficam assistindo as crianças lá dentro da piscina."),
    ("Onde o pai troca", "Onde o pai troca a menina e a mãe, o menino."),
    ("se havendo mais", "E seguindo mais aqui, temos a nossa piscina."),
    ("osônio", "Trabalhamos também com o sistema de ozônio,"),
    ("Olílio", "onde a gente evita deixar o olhinho das crianças arder."),
    ("com a auxílio", "Todas as nossas aulas são com o auxílio de professores, tá bom?"),
    ("Nosso celular", "Nosso celular,"),
    ("Qualquer dúvida", "qualquer dúvida,"),
    ("Só entrar em contato", "é só entrar em contato com a gente, que a gente te atende, tá bom?"),
    ("aula instrumental", "Te aguardamos para a aula experimental."),
]
segs = json.load(open("transcript.json"))
for s in segs:
    s["text"] = s["text"].strip()
    for k, v in fixes:
        if k in s["text"]: s["text"] = v
# ---------- Text measuring ----------
tt = TTFont(FONT)
cmap = tt.getBestCmap(); hmtx = tt["hmtx"]; upm = tt["head"].unitsPerEm
def width(txt):
    return sum(hmtx[cmap.get(ord(c), cmap[ord("?")])][0] for c in txt) * EM / upm

# ---------- Chunk each segment into single-line captions ----------
STOP = set("a o as os e de da do das dos que em no na pra para um uma com nosso nossa nossos nossas é eu vou se te".split())
def chunks(text):
    words = text.split()
    out, cur = [], []
    i = 0
    while i < len(words):
        w = words[i]
        trial = " ".join(cur + [w])
        if cur and (width(trial) > MAX_W or len(cur) >= 4):
            # don't end a caption on a weak word: push trailing weak words forward
            carry = []
            while len(cur) > 1 and cur[-1].lower().strip(",.?!") in STOP and not re.search(r"[,.?!]$", cur[-1]):
                carry.insert(0, cur.pop())
            out.append(cur); cur = carry
            continue
        cur.append(w); i += 1
        if re.search(r"[,.?!]$", w) and (len(cur) >= 2 or (i < len(words))):
            out.append(cur); cur = []
    if cur: out.append(cur)
    merged = []
    for c in out:
        if merged and len(c) == 1 and width(" ".join(merged[-1] + c)) <= MAX_W and len(merged[-1]) < 5 and not re.search(r"[.?!]$", merged[-1][-1]):
            merged[-1] += c
        else:
            merged.append(c)
    return merged

cues = []
for s in segs:
    ws = s["words"]
    t0, t1 = ws[0]["s"] if ws else s["start"], ws[-1]["e"] if ws else s["end"]
    cs = chunks(s["text"])
    total = sum(len(" ".join(c)) for c in cs)
    acc = 0
    for c in cs:
        L = len(" ".join(c))
        a = t0 + (t1 - t0) * acc / total
        b = t0 + (t1 - t0) * (acc + L) / total
        acc += L
        cues.append([a, b, " ".join(c)])
# close tiny gaps so captions don't flicker; keep at least 0.6 s on screen
for i, c in enumerate(cues):
    nxt = cues[i + 1][0] if i + 1 < len(cues) else 1e9
    c[1] = max(c[1], c[0] + 0.6)
    if nxt - c[1] < 0.35: c[1] = nxt
    c[1] = min(c[1], nxt)
    assert width(c[2]) <= MAX_W + 1, c

def ts(t):
    cs = int(round(t * 100)); h, cs = divmod(cs, 360000); m, cs = divmod(cs, 6000); s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

ass = [
    "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W_OUT}", f"PlayResY: {H_OUT}", "WrapStyle: 2", "ScaledBorderAndShadow: yes", "",
    "[V4+ Styles]",
    "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
    # Sharp white text
    f"Style: Main,Montserrat ExtraBold,{FS},&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,5,40,40,0,1",
    # Soft drop shadow: black @65% opacity (alpha 0x59), slightly blurred, offset 4px
    f"Style: Shadow,Montserrat ExtraBold,{FS},&H59000000,&H59000000,&H59000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,5,40,40,0,1",
    "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
]
X = W_OUT // 2
# shadow at -5deg-ish angle, distance 4 -> mostly down/right
for a, b, txt in cues:
    anim = r"\fad(90,90)\fscx94\fscy94\t(0,140,\fscx100\fscy100)"
    ass.append(f"Dialogue: 0,{ts(a)},{ts(b)},Shadow,,0,0,0,,{{\\pos({X+4},{SUB_Y+5})\\blur4{anim}}}{txt}")
    ass.append(f"Dialogue: 1,{ts(a)},{ts(b)},Main,,0,0,0,,{{\\pos({X},{SUB_Y}){anim}}}{txt}")
open("subs.ass", "w").write("\n".join(ass) + "\n")
for c in cues: print(f"{c[0]:6.2f}-{c[1]:6.2f} [{width(c[2]):4.0f}px] {c[2]}")

# ---------- Zoom keyframes (time, zoom). Pairs at shot cuts reset framing. ----------
kf = [(0, 1.00), (3.29, 1.05),
      (3.30, 1.10), (9.5, 1.02), (15.5, 1.09), (19.25, 1.05),
      (19.27, 1.00), (24.4, 1.07), (29.75, 1.02),
      (29.77, 1.09), (35.0, 1.02), (40.31, 1.07),
      (40.34, 1.00), (46.0, 1.08), (52.5, 1.02), (58.5, 1.09), (65.0, 1.01), (69.0, 1.00),
      (74.0, 1.06), (80.5, 1.01), (86.5, 1.08), (92.35, 1.03),
      (92.37, 1.00), (106.0, 1.07)]
parts = []
for (ta, za), (tb, zb) in zip(kf, kf[1:]):
    if tb - ta < 0.05: continue
    u = f"((t-{ta})/{tb-ta:.4f})"
    ease = f"({u}*{u}*(3-2*{u}))"          # smoothstep: soft ease-in/out
    parts.append(f"between(t,{ta},{tb})*({za}+{zb-za:.4f}*{ease})")
z = "(" + "+".join(parts) + ")"
z = z.replace("t", "(in/30)").replace("be(in/30)ween", "between")
a = f"(1-1/{z})"
FX, FY = 0.5, 0.42   # zoom toward upper-middle (faces)
persp = (f"perspective=x0='{FX}*W*{a}':y0='{FY}*H*{a}':x1='W-{1-FX}*W*{a}':y1='{FY}*H*{a}':"
         f"x2='{FX}*W*{a}':y2='H-{1-FY:.2f}*H*{a}':x3='W-{1-FX}*W*{a}':y3='H-{1-FY:.2f}*H*{a}':"
         "interpolation=cubic:eval=frame")
open("persp.txt", "w").write(persp)
