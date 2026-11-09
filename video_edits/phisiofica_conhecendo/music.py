"""Synthesize a light, soft, gently-moving background track (original, royalty-free)."""
import numpy as np, wave, sys

SR = 44100
DUR = float(sys.argv[1]) if len(sys.argv) > 1 else 106.0
OUT = sys.argv[2] if len(sys.argv) > 2 else "music.wav"
BPM = 92
BEAT = 60 / BPM
BAR = 4 * BEAT
N = int(DUR * SR)
rng = np.random.default_rng(7)

def midi(n): return 440 * 2 ** ((n - 69) / 12)

# Warm, airy progression (key of D): Dmaj9 - Bm9 - Gmaj7 - A6sus
prog = [
    [50, 57, 62, 66, 69, 76],  # Dmaj9-ish
    [47, 54, 62, 66, 69, 73],  # Bm11
    [43, 50, 59, 62, 66, 71],  # Gmaj7
    [45, 52, 61, 64, 66, 71],  # A6sus
]

L = np.zeros(N); R = np.zeros(N)

def add(sig, start, pan=0.0, gain=1.0):
    s = int(start * SR)
    if s >= N: return
    e = min(N, s + len(sig)); sig = sig[: e - s] * gain
    L[s:e] += sig * np.sqrt(0.5 * (1 - pan)); R[s:e] += sig * np.sqrt(0.5 * (1 + pan))

def env_adsr(n, a, d, s_lvl, r):
    t = np.arange(n) / SR; tot = n / SR
    e = np.where(t < a, t / a, np.where(t < a + d, 1 - (1 - s_lvl) * (t - a) / d, s_lvl))
    rel = t > tot - r
    e[rel] *= np.clip((tot - t[rel]) / r, 0, 1)
    return e

def pad_note(f, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    sig = np.zeros(n)
    for det in (-0.12, 0.0, 0.11):
        ff = f * 2 ** (det / 12)
        ph = rng.uniform(0, 2 * np.pi)
        sig += np.sin(2 * np.pi * ff * t + ph) + 0.18 * np.sin(4 * np.pi * ff * t + ph) + 0.06 * np.sin(6 * np.pi * ff * t)
    sig *= 1 + 0.15 * np.sin(2 * np.pi * 0.23 * t)  # slow shimmer
    return sig * env_adsr(n, 1.2, 0.8, 0.8, 1.6) / 3

def keys_note(f, dur=2.2):
    n = int(dur * SR); t = np.arange(n) / SR
    sig = (np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t * 6)
           + 0.12 * np.sin(2 * np.pi * 3.01 * f * t) * np.exp(-t * 9))
    e = np.exp(-t * 2.2) * np.minimum(1, t / 0.006)
    e[-2000:] *= np.linspace(1, 0, 2000)
    return sig * e

def kick():
    n = int(0.35 * SR); t = np.arange(n) / SR
    f = 55 + 70 * np.exp(-t * 30)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)

def shaker(dur=0.09):
    n = int(dur * SR); t = np.arange(n) / SR
    x = rng.standard_normal(n)
    x = np.diff(np.concatenate([[0], x]))  # brighten
    return x * np.exp(-t * 55) * np.minimum(1, t / 0.004)

def bass_note(f, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    return (np.sin(2 * np.pi * f * t) + 0.25 * np.sin(4 * np.pi * f * t)) * env_adsr(n, 0.02, 0.3, 0.7, 0.25)

intro_bars = 2       # pad only
n_bars = int(np.ceil(DUR / BAR))
arp_pattern = [0, 2, 3, 4, 5, 4, 3, 2]  # indices into chord (upper voices)
for b in range(n_bars):
    t0 = b * BAR
    ch = prog[b % 4]
    # pad (chord tones above bass)
    for k, note in enumerate(ch[1:5]):
        add(pad_note(midi(note), BAR + 1.6), t0, pan=(k - 1.5) * 0.35, gain=0.055)
    if b >= 1:
        # soft electric-piano arpeggio in eighths, +1 octave on top voices
        for i, idx in enumerate(arp_pattern):
            note = ch[idx] + 12
            vel = 0.75 + 0.25 * rng.random()
            add(keys_note(midi(note)), t0 + i * BEAT / 2 + rng.normal(0, 0.006),
                pan=0.45 * np.sin(i * 0.9), gain=0.045 * vel)
    if b >= intro_bars:
        add(bass_note(midi(ch[0] - 12), BEAT * 2.9), t0, gain=0.11)
        add(bass_note(midi(ch[0] - 12), BEAT * 0.9), t0 + 3 * BEAT, gain=0.08)
    if b >= intro_bars and b < n_bars - 1:
        for beat in range(4):
            if beat in (0, 2):
                add(kick(), t0 + beat * BEAT, gain=0.16)
        for e8 in range(8):
            add(shaker(), t0 + e8 * BEAT / 2 + rng.normal(0, 0.004),
                pan=0.3, gain=(0.035 if e8 % 2 else 0.018))

# Simple stereo reverb: convolve with decaying noise IR
def reverb(x, seed):
    r = np.random.default_rng(seed)
    n = int(2.6 * SR); t = np.arange(n) / SR
    ir = r.standard_normal(n) * np.exp(-t * 2.4)
    ir[: int(0.02 * SR)] = 0
    ir /= np.sqrt(np.sum(ir ** 2))
    m = len(x) + n - 1; size = 1 << (m - 1).bit_length()
    y = np.fft.irfft(np.fft.rfft(x, size) * np.fft.rfft(ir, size), size)[: len(x)]
    return y
wetL, wetR = reverb(L, 1), reverb(R, 2)
L = L * 0.75 + wetL * 0.35; R = R * 0.75 + wetR * 0.35

# Fades
t = np.arange(N) / SR
fade = np.minimum(1, t / 2.5) * np.clip((DUR - t) / 4.0, 0, 1)
L *= fade; R *= fade
peak = max(np.abs(L).max(), np.abs(R).max())
L /= peak / 0.89; R /= peak / 0.89
st = (np.stack([L, R], 1) * 32767).astype(np.int16)
w = wave.open(OUT, "wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(st.tobytes()); w.close()
print("ok", OUT, DUR)
