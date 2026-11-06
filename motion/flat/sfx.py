"""Synthesises a cartoon soundtrack (ukulele-ish plucks + comic SFX) timed to comic.html."""
import sys, wave
import numpy as np

SR = 48000
DUR = 7.0
T_KICK, T_HIT = 2.55, 3.4
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

# ---- footsteps (pitter-patter) during the run
st = 0.0
while st < T_KICK - 0.05:
    add(noise(0.035, 0.5) * np.exp(-np.linspace(0, 8, int(SR * 0.035))), st, 0.35)
    add(tone(220, 140, 0.05, k=40), st, 0.25)
    st += np.pi / 13
# little "pop" when the heart bubble appears
add(tone(500, 1300, 0.09, k=25), 0.55, 0.35)
# ---- kick: thump + POW
add(tone(160, 50, 0.25, k=14), T_KICK + 0.08, 0.9)
add(noise(0.08, 0.6) * np.exp(-np.linspace(0, 10, int(SR * 0.08))), T_KICK + 0.08, 0.5)
# slide whistle as the ball flies at the camera
add(tone(450, 1700, T_HIT - T_KICK - 0.15, vib=25, vibf=7, env='lin'), T_KICK + 0.12, 0.22)
# ---- goal: boom + boing + cheer
add(tone(70, 35, 1.2, k=3.5), T_HIT, 1.0)
add(noise(0.3, 0.4) * np.exp(-np.linspace(0, 6, int(SR * 0.3))), T_HIT, 0.6)
add(tone(260, 180, 0.9, vib=60, vibf=11, k=3), T_HIT + 0.05, 0.45)  # boiiing
cheer = noise(2.6, 0.08) * np.concatenate([np.linspace(0, 1, int(SR * 0.4)), np.exp(-np.linspace(0, 2.2, int(SR * 2.2)))])[:int(SR * 2.6)]
add(cheer, T_HIT + 0.05, 0.9)
# heart pops
for i in range(12):
    add(tone(600 + 90 * i, 1200 + 90 * i, 0.07, k=30), T_HIT + 0.1 + i * 0.07 + rng.uniform(0, 0.03), 0.18)
# second bubble pop
add(tone(500, 1300, 0.09, k=25), T_HIT + 0.9, 0.35)
# heart-iris "ta-daa"
for j, m in enumerate([72, 76, 79, 84]):
    add(pluck(midi(m), 1.0, 0.6), DUR - 0.75 + j * 0.02, 0.32)
add(tone(midi(84), midi(84), 0.6, vib=6, vibf=6, k=3), DUR - 0.62, 0.15)

out = out[:int(SR * DUR)]
fade = int(SR * 0.25); out[-fade:] *= np.linspace(1, 0, fade)
out = np.tanh(out * 1.1)
out /= max(1e-9, np.abs(out).max()) / 0.89
pcm = (out * 32767).astype(np.int16)
with wave.open(sys.argv[1], 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
print('ok')
