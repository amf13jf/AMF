"""Captions for v6 timeline: hook (new mom) + coordinator + new mom testimony. Style = reference 'Texto padrão'."""
import json, re
from fontTools.ttLib import TTFont

W, H = 1080, 1920
EM = 58; FS = round(EM * 1.562); MAX_W = 820; Y = 1160
tt = TTFont("/root/.fonts/Montserrat-800.ttf"); cmap = tt.getBestCmap(); hm = tt["hmtx"]
def width(s): return sum(hm[cmap.get(ord(c), cmap[ord("?")])][0] for c in s) * EM / 1000

def seg_words(s, fixes, offset, lo, hi):
    """Corrected words of a whisper segment, timed by char-position mapping, kept if inside [lo,hi] (source time)."""
    txt = s["text"].strip()
    for k, v in fixes:
        if k in txt: txt = v
    txt = txt.replace("20 minutos", "20\u00a0minutos")
    ws = s["words"]; marks = []; pos = 0
    for w in ws:
        marks.append((pos, w["s"])); pos += len(w["w"]); marks.append((pos, w["e"]))
    def at(fr):
        p = fr * pos
        for (p0, t0), (p1, t1) in zip(marks, marks[1:]):
            if p <= p1: return t0 + (t1 - t0) * ((p - p0) / (p1 - p0) if p1 > p0 else 0)
        return marks[-1][1]
    out = []; c = 0; total = len(txt)
    for w in txt.split(" "):
        a = at(c / total); c += len(w); b = at(c / total); c += 1
        if a >= lo - 0.05 and b <= hi + 0.05:
            out.append([w, a + offset, b + offset])
    return out

segs = json.load(open("transcript.json"))
fixes = [
    ("Márcio", "O meu nome é Márcio, eu tenho mais ou menos cinco anos aqui."),
    ("lugar agradável", "Aqui é um lugar agradável, a gente é bem recebido, os professores são ótimos."),
    ("precisando da natação", "precisando da natação. Eu adoro vir pra cá, é muito bom."),
    ("mas meu corpo", "Eu tive que fazer uma cirurgia, fiquei um mês em casa, meu corpo estava pesado,"),
    ("não posso ficar sem não", "Eu gosto muito, não posso ficar sem, não."),
    ("Pretendo", "Pretendo continuar mais bastante tempo ainda."),
]
groups = [seg_words(s, fixes, 0.0, 0.0, 999) for s in segs]
STOP = set("ou a o as os e de da do das dos que em no na pra para um uma com é eu se te sou à".split())
def chunks(words):
    out, cur, i = [], [], 0
    while i < len(words):
        w = words[i]
        if cur and (width(" ".join(x[0] for x in cur + [w])) > MAX_W or len(cur) >= 5):
            carry = []
            while len(cur) > 1 and cur[-1][0].lower().strip(",.?!") in STOP:
                carry.insert(0, cur.pop())
            out.append(cur); cur = carry; continue
        cur.append(w); i += 1
        if re.search(r"[,.?!]$", w[0]): out.append(cur); cur = []
    if cur: out.append(cur)
    for k in range(1, len(out)):   # avoid a lone last word: borrow one from the previous chunk
        if len(out[k]) == 1 and len(out[k-1]) > 2 and width(" ".join(x[0] for x in out[k-1][-1:] + out[k])) <= MAX_W and not re.search(r"[,.?!]$", out[k-1][-1][0]):
            out[k].insert(0, out[k-1].pop())
    return out

def ts(t):
    c = int(round(t * 100)); h, c = divmod(c, 360000); m, c = divmod(c, 6000); s, c = divmod(c, 100)
    return f"{h}:{m:02d}:{s:02d}.{c:02d}"

events = [ch for g in groups for ch in chunks(g)]
L = ["[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}", "WrapStyle: 2", "ScaledBorderAndShadow: yes", "",
     "[V4+ Styles]",
     "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
     f"Style: Main,Montserrat ExtraBold,{FS},&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,5,40,40,0,1",
     f"Style: Shadow,Montserrat ExtraBold,{FS},&H59000000,&H59000000,&H59000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,5,40,40,0,1",
     "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
anim = r"\fad(90,90)\fscx94\fscy94\t(0,140,\fscx100\fscy100)"
for i, ws in enumerate(events):
    a = ws[0][1]; nxt = events[i + 1][0][1] if i + 1 < len(events) else 1e9
    b = max(ws[-1][2] + 0.25, a + 0.5)
    if nxt - b < 0.4: b = nxt
    b = min(b, nxt)
    skip = []
    if any(x <= a < y for x, y in skip): continue
    for x, y in skip:
        if a < x < b: b = x
    txt = " ".join(w[0] for w in ws); assert width(txt) <= MAX_W, txt
    L.append(f"Dialogue: 0,{ts(a)},{ts(b)},Shadow,,0,0,0,,{{\\pos({W//2+3},{Y+4})\\blur3{anim}}}{txt}")
    L.append(f"Dialogue: 1,{ts(a)},{ts(b)},Main,,0,0,0,,{{\\pos({W//2},{Y}){anim}}}{txt}")
    print(f"{a:6.2f}-{b:6.2f} {txt}")
open("subs.ass", "w").write("\n".join(L) + "\n")
