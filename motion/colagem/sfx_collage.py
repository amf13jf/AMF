"""Synthesises a cartoon soundtrack (ukulele-ish plucks + comic SFX) timed to comic.html."""
import sys, wave
import numpy as np

SR = 48000
DUR = 8.0
T_KICK, T_HIT = 2.70, 3.25
out = np.zeros(int(SR * DUR) + SR)
rng = np.random.default_rng(3)


def add(sig, t, gain=1.0):
    i = int(t * SR)
    n = min(len(sig), len(out) - i)
    out[i:i + n] += sig[:n] * gain


def pluck(freq, dur=0.6, bright=0.5):
    n = int(SR * dur); p = int(SR / freq)
    buf = rng.uniform(-1, 1, p)
    y = np.zeros(n)
    for i in range(n):
        y[i] = buf[i % p]
        buf[i % p] = 0.996 * (bright * buf[i % p] + (1 - bright) * buf[(i + 1) % p]) if True else 0
    return y * np.exp(-np.linspace(0, 4, n))


def tone(f0, f1, dur, shape='sine', vib=0, vibf=0, env='exp', k=6):
    t = np.linspace(0, dur, int(SR * dur), endpoint=False)
    f = f0 + (f1 - f0) * t / dur + vib * np.sin(2 * np.pi * vibf * t)
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = np.sin(ph) if shape == 'sine' else np.sign(np.sin(ph)) * 0.5 + 0.5 * np.sin(ph)
    e = np.exp(-k * t) if env == 'exp' else np.minimum(1, t / 0.02) * np.minimum(1, (dur - t) / 0.05)
    return s * e


def noise(dur, lp=0.2):
    x = rng.uniform(-1, 1, int(SR * dur))
    y = np.zeros_like(x); a = 0
    for i, v in enumerate(x):
        a += lp * (v - a); y[i] = a
    return y


midi = lambda m: 440 * 2 ** ((m - 69) / 12)
# ---- happy uke strum: C G Am F at 132 bpm
beat = 60 / 132
chords = [[60, 64, 67, 72], [55, 62, 67, 71], [57, 64, 69, 72], [53, 60, 65, 69]]
cache = {}
def strum(ch, t, g):
    for j, m in enumerate(ch):
        if m not in cache: cache[m] = pluck(midi(m), 0.7)
        add(cache[m], t + j * 0.012, g)

b = 0; t = 0.05
pattern = [1, 0, 0.6, 0.7, 0, 0.6, 0.8, 0.5]  # eighth-note accents
while t < DUR - 0.3:
    ch = chords[(b // 8) % 4]
    acc = pattern[b % 8]
    g = 0.22 * acc
    if T_KICK < t < T_HIT: g *= 0.25          # hold the breath during the shot
    if t >= T_HIT: g *= 1.35                   # party after the goal
    if acc: strum(ch, t, g)
    t += beat / 2; b += 1
# bass "boom-chick"
for i in range(int(DUR / beat)):
    tt = 0.05 + i * beat
    if T_KICK < tt < T_HIT: continue
    root = [48, 43, 45, 41][(i // 4) % 4]
    add(tone(midi(root), midi(root), 0.3, k=9), tt, 0.35 if i % 2 == 0 else 0.0)

def rustle(t, g=0.5, d=0.18):
    n = noise(d, 0.55) * np.exp(-np.linspace(0, 5, int(SR * d))) * (1 + 0.6 * np.sin(np.linspace(0, 60, int(SR * d))))
    add(n, t, g)
for tt in (0.15, 0.35, 0.55, 0.8): rustle(tt, 0.55)
add(tone(500, 1300, 0.09, k=25), 0.82, 0.3)            # ball pops in
for i in range(5): add(tone(140 + 30 * i, 120 + 30 * i, 0.06, k=30), 1.0 + i * 0.09, 0.25)  # wooden creaks, foot comes down
for i in range(4): add(noise(0.03, 0.7) * np.exp(-np.linspace(0, 8, int(SR * 0.03))), 1.75 + i * 0.12, 0.3)  # marker dashes
add(noise(0.25, 0.25) * np.linspace(0, 1, int(SR * 0.25)), T_KICK - 0.25, 0.5)  # whoosh (swing)
add(tone(160, 50, 0.25, k=14), T_KICK, 0.9)
add(noise(0.08, 0.6) * np.exp(-np.linspace(0, 10, int(SR * 0.08))), T_KICK, 0.5)
add(tone(450, 1700, T_HIT - T_KICK - 0.05, vib=25, vibf=7, env='lin'), T_KICK + 0.03, 0.2)
add(tone(70, 35, 1.2, k=3.5), T_HIT, 1.0)
add(noise(0.3, 0.4) * np.exp(-np.linspace(0, 6, int(SR * 0.3))), T_HIT, 0.6)
add(tone(260, 180, 0.9, vib=60, vibf=11, k=3), T_HIT + 0.05, 0.45)
cheer = noise(2.6, 0.08) * np.concatenate([np.linspace(0, 1, int(SR * 0.4)), np.exp(-np.linspace(0, 2.2, int(SR * 2.2)))])[:int(SR * 2.6)]
add(cheer, T_HIT + 0.05, 0.8)
for i in range(6): rustle(T_HIT + 0.12 + i * 0.12, 0.45, 0.1)              # ransom letters slap on
for i in range(8): add(tone(600 + 90 * i, 1200 + 90 * i, 0.07, k=30), T_HIT + 0.15 + i * 0.09, 0.2)  # hearts
for i in range(8):                                                           # stamps
    add(tone(110, 70, 0.12, k=25), 4.1 + i * 0.17, 0.6); add(noise(0.04, 0.5) * np.exp(-np.linspace(0, 8, int(SR * 0.04))), 4.1 + i * 0.17, 0.3)
rustle(6.6, 0.8, 0.45)                                                        # big yellow sheet
add(tone(500, 1300, 0.09, k=25), 7.1, 0.4); add(tone(500, 1300, 0.09, k=25), 7.25, 0.35)
add(tone(110, 70, 0.14, k=22), 7.4, 0.7)
for j, m in enumerate([72, 76, 79, 84]):
    add(pluck(midi(m), 1.0, 0.6), 7.1 + j * 0.02, 0.32)
out = out[:int(SR * DUR)]
fade = int(SR * 0.25); out[-fade:] *= np.linspace(1, 0, fade)
out = np.tanh(out * 1.1)
out /= max(1e-9, np.abs(out).max()) / 0.89
pcm = (out * 32767).astype(np.int16)
with wave.open(sys.argv[1], 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
print('ok')
