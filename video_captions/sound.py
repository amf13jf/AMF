"""Sons sintetizados (sem direitos autorais): whoosh nas transições e trilha de fundo.

Uso:
    python -m video_captions.sound video.mp4 saida.mp4 --script aura_1109

Lê os cortes e punch-ins de CAMERA no roteiro, gera um whoosh em cada um e uma
trilha calma (piano elétrico + pad + baixo + shaker, ~84 BPM). A trilha abaixa
sozinha quando há voz (sidechain) e o resultado é normalizado para -14 LUFS.
"""

import argparse
import importlib
import os
import subprocess
import tempfile

import numpy as np

SR = 48000
rng = np.random.default_rng(7)


def midi_hz(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def env_adsr(n, attack, decay_tau):
    t = np.arange(n) / SR
    return np.minimum(1.0, t / attack) * np.exp(-t / decay_tau)


def fft_convolve(x, ir):
    n = len(x) + len(ir) - 1
    size = 1 << (n - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(x, size) * np.fft.rfft(ir, size), size)[:n]


def reverb(x, seconds=2.2, wet=0.28):
    t = np.arange(int(seconds * SR)) / SR
    ir = rng.standard_normal(len(t)) * np.exp(-t / (seconds / 5))
    ir = lowpass(ir, 5000)
    ir /= np.sqrt((ir ** 2).sum())
    out = fft_convolve(x, ir)[:len(x)]
    return (1 - wet) * x + wet * out * 3


def lowpass(x, cutoff):
    """Passa-baixa suave no domínio da frequência."""
    spec = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    return np.fft.irfft(spec / np.sqrt(1 + (f / cutoff) ** 4), len(x))


# ---------------------------------------------------------------- whoosh


def whoosh(length=0.6, peak=0.62, f_lo=250, f_hi=3800, gain=1.0):
    """Ruído com filtro passa-faixa que sobe até o pico e desce depois."""
    n = int(length * SR)
    noise = rng.standard_normal(n + 2048)
    win, hop = 1024, 256
    window = np.hanning(win)
    out = np.zeros(n + 2048)
    norm = np.zeros(n + 2048)
    freqs = np.fft.rfftfreq(win, 1 / SR)
    for start in range(0, n, hop):
        k = start / n
        rise = min(1.0, k / peak)
        fall = max(0.0, (k - peak) / (1 - peak))
        fc = f_lo + (f_hi - f_lo) * (rise ** 2 if k < peak else (1 - fall) ** 1.5)
        band = np.exp(-0.5 * (np.log(np.maximum(freqs, 1) / fc) / 0.55) ** 2)
        frame = np.fft.irfft(np.fft.rfft(noise[start:start + win] * window) * band, win)
        out[start:start + win] += frame * window
        norm[start:start + win] += window ** 2
    out = out[:n] / np.maximum(norm[:n], 1e-3)
    t = np.arange(n) / n
    env = np.where(t < peak, (t / peak) ** 2.2, np.exp(-(t - peak) / 0.12))
    out *= env
    return gain * out / (np.abs(out).max() + 1e-9)


# ---------------------------------------------------------------- trilha


CHORDS = [  # Cmaj9, Am9, Fmaj9, G6/9 (notas MIDI)
    [48, 55, 59, 62, 64],
    [45, 52, 55, 59, 60],
    [41, 48, 52, 55, 57],
    [43, 50, 52, 57, 59],
]


def ep_note(freq, dur, vel):
    """Piano elétrico simples: senoide + harmônicos com decaimento."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    tone = (np.sin(2 * np.pi * freq * t) + 0.35 * np.sin(2 * np.pi * 2 * freq * t)
            * np.exp(-t / 0.3) + 0.08 * np.sin(2 * np.pi * 3 * freq * t) * np.exp(-t / 0.15))
    trem = 1 + 0.06 * np.sin(2 * np.pi * 4.5 * t)
    return vel * tone * trem * env_adsr(n, 0.008, 1.1)


def music(duration, bpm=84):
    n = int(duration * SR)
    beat = 60 / bpm
    bar = 4 * beat
    mix = np.zeros(n + SR * 3)

    def add(sig, at):
        i = int(at * SR)
        mix[i:i + len(sig)] += sig[:max(0, len(mix) - i)]

    bars = int(np.ceil(duration / bar)) + 1
    for b in range(bars):
        chord = CHORDS[b % len(CHORDS)]
        t0 = b * bar
        # piano elétrico: acorde + arpejo leve em colcheias
        for note in chord[1:]:
            add(ep_note(midi_hz(note + 12), 2.5, 0.10), t0)
        arp = [chord[2], chord[3], chord[4], chord[3]] * 2
        for i, note in enumerate(arp):
            if i in (0, 3, 5, 6):
                add(ep_note(midi_hz(note + 24), 1.2, 0.055), t0 + i * beat / 2)
        # pad
        pn = int(bar * SR * 1.1)
        pt = np.arange(pn) / SR
        pad = sum(np.sin(2 * np.pi * midi_hz(nt + 12) * pt + rng.uniform(0, 6))
                  for nt in chord[1:4])
        pad *= np.minimum(1, pt / 0.8) * np.minimum(1, (pn / SR - pt) / 0.6) * 0.022
        add(pad, t0)
        # baixo nos tempos 1 e 3
        for k in (0, 2):
            bn = int(beat * 1.8 * SR)
            bt = np.arange(bn) / SR
            add(0.16 * np.sin(2 * np.pi * midi_hz(chord[0] - 12) * bt) * env_adsr(bn, 0.01, 0.5),
                t0 + k * beat)
        # shaker em colcheias (ruído filtrado bem baixinho)
        for i in range(8):
            sn = int(0.06 * SR)
            sh = rng.standard_normal(sn) * np.exp(-np.arange(sn) / (0.012 * SR))
            add(sh * (0.018 if i % 2 else 0.010), t0 + i * beat / 2)
    mix = mix[:n]
    mix = reverb(mix)
    t = np.arange(n) / SR
    mix *= np.minimum(1, t / 0.8) * np.minimum(1, (duration - t) / 1.8)
    return mix / (np.abs(mix).max() + 1e-9) * 0.8


# ---------------------------------------------------------------- mix


def write_wav(path, x):
    stereo = np.stack([x, x], axis=1).astype(np.float32)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2",
                    "-i", "-", path], input=stereo.tobytes(), check=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("output")
    ap.add_argument("--script", required=True)
    ap.add_argument("--music-db", type=float, default=-17.0,
                    help="volume da trilha antes do sidechain (dB)")
    ap.add_argument("--sfx-db", type=float, default=-9.0, help="volume dos whooshes (dB)")
    args = ap.parse_args()

    script = importlib.import_module(f"{__package__}.{args.script}")
    cam = getattr(script, "CAMERA", {})
    duration = float(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
        args.video]))

    sfx = np.zeros(int((duration + 1) * SR))
    for t, length, gain in ([(c, 0.6, 1.0) for c in cam.get("cuts", [])]
                            + [(p, 0.4, 0.45) for p in cam.get("punch_ins", [])]):
        w = whoosh(length, gain=gain)
        i = int((t - 0.62 * length) * SR)  # o pico cai em cima do corte
        sfx[max(0, i):i + len(w)] += w[max(0, -i):]
    sfx = sfx[:int(duration * SR)]

    with tempfile.TemporaryDirectory() as tmp:
        mpath, spath = os.path.join(tmp, "music.wav"), os.path.join(tmp, "sfx.wav")
        write_wav(mpath, music(duration))
        write_wav(spath, sfx)
        fc = (f"[1:a]volume={args.music_db}dB[m];"
              "[0:a]asplit=2[v][sc];"
              "[m][sc]sidechaincompress=threshold=0.03:ratio=6:attack=40:release=400[md];"
              f"[2:a]volume={args.sfx_db}dB[s];"
              "[v][md][s]amix=inputs=3:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[a]")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", args.video, "-i", mpath, "-i", spath,
                        "-filter_complex", fc, "-map", "0:v", "-map", "[a]", "-c:v", "copy",
                        "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-movflags", "+faststart",
                        args.output], check=True)
    print(f"pronto: {args.output}")


if __name__ == "__main__":
    main()
