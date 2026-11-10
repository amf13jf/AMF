"""Dynamic one-line captions (Montserrat ExtraBold, active word highlighted + pop)."""
import json, re
from fontTools.ttLib import TTFont

W, H = 1080, 1920
EM = 70; FS = round(EM * 1.562)
MAX_W = 940
Y = 1160
HL = "&H3FD2FF&"   # highlight colour (BGR) = #FFD23F

fixes = [
    ("Fisiofísica é um lugar", "Aqui na Phisiofisica é um lugar para todo mundo."),
    ("Você sabe por que", "Você sabe por\u00a0que eles confiam tanto na gente?"),
    ("concorre", "Desde a primeira aula, o professor acompanha o aluno de perto,"),
    ("gostando de entender", "buscando entender suas necessidades e dificuldades."),
    ("medicino", "Com essa atenção, conseguimos adaptar o ensino"),
    ("cada avance", "Assim, cada avanço é valorizado"),
    ("A mãe da Alícia", "Sou mãe da Alícia, que faz natação aqui."),
    ("Você tem uns dois anos", "Já tem uns dois anos que nós estamos aqui na Phisiofisica."),
    ("anotação para minha filha", "E a natação para minha filha, sou mãe atípica,"),
    ("anotação para ela", "a natação para ela foi fundamental, foi assim,"),
    ("com a Maria", "uma virada de chave, porque a água traz calmaria,"),
    ("alívio do estresse", "traz para ela um alívio do estresse, do dia\u00a0a\u00a0dia,"),
    ("ama demais a anotação", "E a Alícia ama, ama demais a natação,"),
    ("aonde nós estamos", "ama o ambiente, né, onde nós estamos."),
    ("Alícia foi uma virada", "E pra Alícia foi uma virada de chave."),
]
segs = json.load(open("transcript.json"))
tt = TTFont("/root/.fonts/Montserrat-800.ttf"); cmap = tt.getBestCmap(); hm = tt["hmtx"]
def width(s): return sum(hm[cmap.get(ord(c), cmap[ord("?")])][0] for c in s) * EM / 1000

STOP = set("a o as os e de da do das dos que em no na pra para um uma com é eu se te sou".split())
def chunks(words):
    out, cur = [], []
    i = 0
    while i < len(words):
        w = words[i]
        if cur and (width(" ".join(cur + [w])) > MAX_W or len(cur) >= 4):
            carry = []
            while len(cur) > 1 and cur[-1].lower().strip(",.?!") in STOP:
                carry.insert(0, cur.pop())
            out.append(cur); cur = carry; continue
        cur.append(w); i += 1
        if re.search(r"[,.?!]$", w): out.append(cur); cur = []
    if cur: out.append(cur)
    return out

def ts(t):
    c = int(round(t * 100)); h, c = divmod(c, 360000); m, c = divmod(c, 6000); s, c = divmod(c, 100)
    return f"{h}:{m:02d}:{s:02d}.{c:02d}"

# word-level timing for corrected text: map by character position onto whisper's words
timed = []
for s in segs:
    txt = s["text"].strip()
    for k, v in fixes:
        if k in txt: txt = v
    ws = s["words"]
    orig = "".join(w["w"] for w in ws)
    # cumulative char -> time function from whisper words
    marks = []; pos = 0
    for w in ws:
        marks.append((pos, w["s"])); pos += len(w["w"]); marks.append((pos, w["e"]))
    def at(frac):
        p = frac * pos
        for (p0, t0), (p1, t1) in zip(marks, marks[1:]):
            if p <= p1: return t0 + (t1 - t0) * ((p - p0) / (p1 - p0) if p1 > p0 else 0)
        return marks[-1][1]
    words = txt.split(" "); total = len(txt); c = 0
    seg_words = []
    for w in words:
        a = at(c / total); c += len(w); b = at(c / total); c += 1
        seg_words.append([w, a, b])
    timed.append(seg_words)

lines = ["[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}", "WrapStyle: 2", "ScaledBorderAndShadow: yes", "",
         "[V4+ Styles]",
         "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
         f"Style: Main,Montserrat ExtraBold,{FS},&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,5,40,40,0,1",
         f"Style: Shadow,Montserrat ExtraBold,{FS},&H59000000,&H59000000,&H59000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,5,40,40,0,1",
         "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
events = []
for sw in timed:
    k = 0
    for ch in chunks([w[0] for w in sw]):
        events.append(sw[k:k + len(ch)]); k += len(ch)
for i, ws in enumerate(events):
    start = ws[0][1]
    nxt = events[i + 1][0][1] if i + 1 < len(events) else 1e9
    end = max(ws[-1][2] + 0.25, start + 0.5)
    if nxt - end < 0.4: end = nxt
    end = min(end, nxt)
    assert width(" ".join(w[0] for w in ws)) <= MAX_W
    txt = " ".join(w[0] for w in ws)
    anim = r"\fad(90,90)\fscx94\fscy94\t(0,140,\fscx100\fscy100)"
    lines.append(f"Dialogue: 0,{ts(start)},{ts(end)},Shadow,,0,0,0,,{{\\pos({W//2+4},{Y+5})\\blur4{anim}}}{txt}")
    lines.append(f"Dialogue: 1,{ts(start)},{ts(end)},Main,,0,0,0,,{{\\pos({W//2},{Y}){anim}}}{txt}")
open("subs.ass", "w").write("\n".join(lines) + "\n")
for ws in events: print(f"{ws[0][1]:6.2f} {' '.join(w[0] for w in ws)}")
