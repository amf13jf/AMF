import numpy as np, wave, sys

SR = 44100
BPM = 130.0
BEAT = 60.0 / BPM
T0 = float(sys.argv[1])        # drop time (start of montage)
NB = int(sys.argv[2])          # montage beats
TOTAL = float(sys.argv[3])     # total duration
OUT = sys.argv[4]
TE = T0 + NB * BEAT
N = int(TOTAL * SR) + SR
rng = np.random.default_rng(7)

L = np.zeros(N); R = np.zeros(N)

def add(sig, t, gain=1.0, pan=0.0):
    i = int(round(t * SR))
    if i >= N: return
    if i < 0:
        sig = sig[-i:]; i = 0
    n = min(len(sig), N - i)
    l = gain * np.sqrt(0.5 * (1 - pan)); r = gain * np.sqrt(0.5 * (1 + pan))
    L[i:i+n] += sig[:n] * l * np.sqrt(2) / 2 * 2 ** 0.5
    R[i:i+n] += sig[:n] * r * np.sqrt(2) / 2 * 2 ** 0.5

def fft_filter(x, lo=None, hi=None):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    m = np.ones_like(f)
    if hi: m *= 1 / np.sqrt(1 + (f / hi) ** 8)
    if lo: m *= 1 / np.sqrt(1 + (lo / np.maximum(f, 1e-3)) ** 8)
    return np.fft.irfft(X * m, len(x))

def t_(d): return np.arange(int(d * SR)) / SR

def saw(f, d, ph=0.0):
    t = t_(d); return 2 * ((f * t + ph) % 1.0) - 1

# ---------- instruments ----------
def kick(soft=False):
    t = t_(0.45)
    f = 45 + 110 * np.exp(-t * 28)
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = np.sin(ph) * np.exp(-t * (7 if not soft else 9))
    click = fft_filter(rng.standard_normal(len(t)), lo=1500) * np.exp(-t * 300) * 0.25
    s = np.tanh(1.8 * (s + (0 if soft else click)))
    return s

def clap():
    d = 0.35; t = t_(d)
    n = fft_filter(rng.standard_normal(len(t)), lo=900, hi=6000)
    env = np.zeros_like(t)
    for k, off in enumerate([0, 0.011, 0.022]):
        env += (t >= off) * np.exp(-np.maximum(t - off, 0) * 90)
    env += (t >= 0.03) * np.exp(-np.maximum(t - 0.03, 0) * 14) * 0.6
    return n * env / 3

def snare():
    t = t_(0.25)
    body = np.sin(2 * np.pi * 190 * t) * np.exp(-t * 30) * 0.6
    n = fft_filter(rng.standard_normal(len(t)), lo=1200, hi=9000) * np.exp(-t * 22) * 0.5
    return body + n

def hat(open_=False):
    d = 0.25 if open_ else 0.06; t = t_(d)
    n = fft_filter(rng.standard_normal(len(t)), lo=7000)
    return n * np.exp(-t * (14 if open_ else 70)) * 0.35

def supersaw(freqs, d, cutoff, voices=5, det=0.012):
    s = np.zeros(int(d * SR))
    for f in freqs:
        for v in range(voices):
            dv = (v - (voices - 1) / 2) / ((voices - 1) / 2) * det
            s += saw(f * (1 + dv), d, rng.random())
    s /= (len(freqs) * voices)
    return fft_filter(s, hi=cutoff)

def bassnote(f, d, cutoff=900):
    t = t_(d)
    s = 0.6 * saw(f, d) + 0.6 * saw(f * 1.005, d, 0.3)
    s = fft_filter(s, hi=cutoff) + 0.8 * np.sin(2 * np.pi * f * t)
    env = np.minimum(t / 0.004, 1) * np.exp(-t * 3)
    return np.tanh(1.5 * s * env)

def pluck(f, d=0.2):
    t = t_(d)
    s = saw(f, d) * 0.5 + saw(f * 2.003, d) * 0.25
    s = fft_filter(s, hi=4000)
    return s * np.exp(-t * 16) * np.minimum(t / 0.002, 1)

def impact():
    t = t_(2.5)
    boom = np.sin(2 * np.pi * (38 + 60 * np.exp(-t * 6)) * t) * np.exp(-t * 2.2)
    crash = fft_filter(rng.standard_normal(len(t)), lo=3000) * np.exp(-t * 2.5) * 0.35
    return np.tanh(1.5 * boom) + crash

def riser(d):
    t = t_(d)
    n = rng.standard_normal(len(t))
    # chunked sweeping band to emulate rising filter
    out = np.zeros_like(n); ch = int(0.05 * SR)
    for i in range(0, len(n), ch):
        p = i / len(n)
        out[i:i+ch] = fft_filter(n[i:i+ch], lo=300 + 6000 * p ** 2, hi=1200 + 12000 * p)
    sweep = np.sin(2 * np.pi * np.cumsum(200 + 1200 * (t / d) ** 2) / SR) * 0.15
    env = (t / d) ** 2
    return (out * 0.6 + sweep) * env

def whoosh(d=0.3):
    t = t_(d)
    n = fft_filter(rng.standard_normal(len(t)), lo=800, hi=7000)
    env = np.sin(np.pi * (t / d)) ** 2 * (t / d)
    return n * env * 0.5

# ---------- harmony ----------
ROOTS = [55.0, 43.65, 65.41, 49.0]  # A F C G
CHORDS = [[220, 261.63, 329.63], [174.61, 220, 261.63], [261.63, 329.63, 392.0], [196.0, 246.94, 293.66]]
ARP = [[440, 523.25, 659.25, 523.25], [349.23, 440, 523.25, 440], [523.25, 659.25, 783.99, 659.25], [392, 493.88, 587.33, 493.88]]

def bt(b): return T0 + b * BEAT   # beat -> time

# sidechain envelope (filled where kicks occur in the drop)
side = np.ones(N)
def duck(t, depth=0.75, rel=0.22):
    i = int(t * SR); d = int(rel * SR)
    if i >= N: return
    e = 1 - depth * np.exp(-np.arange(d) / SR * (5 / rel))
    n = min(d, N - i); side[i:i+n] = np.minimum(side[i:i+n], e[:n])

music = {k: (np.zeros(N), np.zeros(N)) for k in ["drums", "tonal"]}
def addto(stem, sig, t, gain=1.0, pan=0.0):
    global L, R
    sl, sr = L, R
    L, R = music[stem]
    add(sig, t, gain, pan)
    L, R = sl, sr

# ---------- INTRO bed (under first speech) ----------
start_beat = -int(np.floor(T0 / BEAT))
for b in range(start_beat, 0):
    tb = bt(b)
    bar = (b // 4) % 4
    if b % 4 == 0:
        addto("tonal", supersaw(CHORDS[bar], 4 * BEAT, 1100, voices=4), tb, 0.55)
        addto("tonal", bassnote(ROOTS[bar], 4 * BEAT, 300) * 0.5, tb, 0.5)
    if b % 2 == 0 and b < -4:
        addto("drums", kick(soft=True), tb, 0.45)
    addto("drums", hat(), tb + BEAT / 2, 0.18, 0.3)
addto("tonal", riser(4 * BEAT), bt(-4), 0.8)

# ---------- DROP / MONTAGE ----------
for b in range(NB):
    tb = bt(b); bar = (b // 4) % 4
    halftime = 8 <= b < 16
    ending = b >= NB - 2
    if ending:
        continue
    if halftime:
        if b % 4 == 0: addto("drums", kick(), tb, 0.95); duck(tb, 0.6, 0.4)
        if b % 4 == 2: addto("drums", clap(), tb, 0.8); addto("drums", snare(), tb, 0.4)
        if b % 4 == 0:
            addto("tonal", supersaw(CHORDS[bar], 4 * BEAT, 700), tb, 0.6)
            addto("tonal", bassnote(ROOTS[bar], 4 * BEAT, 250), tb, 0.6)
        if b >= 14:  # snare roll back into the drop
            k = 4 if b == 14 else 8
            for j in range(k):
                addto("drums", snare(), tb + j * BEAT / k, 0.25 + 0.4 * ((b - 14) * k + j) / 16, 0.0)
        continue
    addto("drums", kick(), tb, 1.0); duck(tb)
    if b % 2 == 1: addto("drums", clap(), tb, 0.85)
    for j in range(4):
        addto("drums", hat(open_=(j == 2)), tb + j * BEAT / 4, 0.55 if j == 2 else (0.35 if j % 2 else 0.22), 0.25)
    # offbeat bass
    addto("tonal", bassnote(ROOTS[bar], BEAT / 2, 1400), tb + BEAT / 2, 0.75)
    addto("tonal", bassnote(ROOTS[bar], BEAT / 4, 1400), tb + 3 * BEAT / 4, 0.45)
    # chord stabs
    if b % 4 in (0, 1, 3) or True:
        for off in ([0.5] if b % 2 == 0 else [0.25, 0.75]):
            addto("tonal", supersaw(CHORDS[bar], 0.22, 3800) * np.exp(-t_(0.22) * 9), tb + off * BEAT, 0.95)
    # arp plucks (16ths)
    for j in range(4):
        addto("tonal", pluck(ARP[bar][j]), tb + j * BEAT / 4, 0.28, -0.35 if j % 2 else 0.35)
    if b == 15 or b == 31: pass

# transitions
addto("drums", impact(), bt(0), 1.0)
addto("drums", impact() * 0.8, bt(8), 1.0)
addto("tonal", riser(2 * BEAT) * 0.8, bt(14), 1.0)
for cb in [4, 16, 20, 24, 28, 32, 36, 40]:
    addto("drums", whoosh(0.28), bt(cb) - 0.28, 0.7)
addto("tonal", supersaw(CHORDS[3], 2 * BEAT, 900) * np.exp(-t_(2 * BEAT) * 1.5), bt(NB - 2), 0.6)
addto("drums", impact(), bt(NB - 2), 0.6)

# ---------- OUTRO bed (under second speech) ----------
b = NB
while bt(b) < TOTAL:
    tb = bt(b); bar = ((b - NB) // 4) % 4
    if (b - NB) % 4 == 0:
        addto("tonal", supersaw(CHORDS[bar], 4 * BEAT, 1000, voices=4), tb, 0.5)
        addto("tonal", bassnote(ROOTS[bar], 4 * BEAT, 300) * 0.5, tb, 0.45)
    if (b - NB) % 2 == 0 and b > NB + 3: addto("drums", kick(soft=True), tb, 0.4)
    if b > NB + 3: addto("drums", hat(), tb + BEAT / 2, 0.16, 0.3)
    b += 1

dl, dr = music["drums"]; tl, tr = music["tonal"]
L = dl + tl * side; R = dr + tr * side

# section levels: bed under speech much lower
tt = np.arange(N) / SR
g = np.full(N, 0.22)
ramp_in = (tt > T0 - 4 * BEAT) & (tt < T0)
g[ramp_in] = 0.22 + 0.25 * (tt[ramp_in] - (T0 - 4 * BEAT)) / (4 * BEAT)
g[(tt >= T0) & (tt < TE - 2 * BEAT)] = 1.0
tail = (tt >= TE - 2 * BEAT) & (tt < TE + 0.5)
g[tail] = 1.0 - 0.78 * (tt[tail] - (TE - 2 * BEAT)) / (2 * BEAT + 0.5)
fo = tt > TOTAL - 4
g[fo] *= np.clip((TOTAL - tt[fo]) / 4, 0, 1)
L *= g; R *= g
st = np.stack([L, R], 1)[: int(TOTAL * SR)]
st = np.tanh(st / (np.max(np.abs(st)) * 0.9) * 1.2) * 0.89
with wave.open(OUT, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((st * 32767).astype("<i2").tobytes())
print("ok", TE)
