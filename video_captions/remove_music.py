"""Tira a música de fundo e mantém só a voz (HTDemucs em ONNX).

Uso:
    python -m video_captions.remove_music entrada.mp4 voz.wav --model htdemucs.onnx

O modelo é o HTDemucs 4 stems da Meta exportado para ONNX (o mesmo do pacote
npm "demucs"). As partes que não rodam em ONNX (STFT/iSTFT e o recorte em
janelas) estão reimplementadas aqui, seguindo demucs/htdemucs.py.
"""

import argparse
import math
import subprocess

import numpy as np
import onnxruntime as ort

SR = 44100
SEGMENT = int(7.8 * SR)  # 343980 amostras, tamanho fixo de entrada do modelo
NFFT, HOP = 4096, 1024
SOURCES = ["drums", "bass", "other", "vocals"]
WINDOW = 0.5 * (1 - np.cos(2 * np.pi * np.arange(NFFT) / NFFT))  # hann periódica


def stft(x):
    """torch.stft(normalized=True, center=True, pad_mode='reflect') sobre o último eixo."""
    x = np.pad(x, [(0, 0)] * (x.ndim - 1) + [(NFFT // 2, NFFT // 2)], mode="reflect")
    n_frames = 1 + (x.shape[-1] - NFFT) // HOP
    idx = np.arange(NFFT)[None, :] + HOP * np.arange(n_frames)[:, None]
    frames = x[..., idx] * WINDOW  # (..., frames, nfft)
    z = np.fft.rfft(frames, axis=-1) / math.sqrt(NFFT)
    return np.swapaxes(z, -1, -2)  # (..., freqs, frames)


def istft(z, length):
    """torch.istft(normalized=True, center=True, length=length)."""
    frames = np.fft.irfft(np.swapaxes(z, -1, -2), n=NFFT, axis=-1) * math.sqrt(NFFT)
    n_frames = frames.shape[-2]
    full = NFFT + HOP * (n_frames - 1)
    out = np.zeros(z.shape[:-2] + (full,), dtype=np.float64)
    wsum = np.zeros(full)
    for f in range(n_frames):
        s = f * HOP
        out[..., s:s + NFFT] += frames[..., f, :] * WINDOW
        wsum[s:s + NFFT] += WINDOW ** 2
    out = out / np.where(wsum > 1e-11, wsum, 1.0)
    out = out[..., NFFT // 2:]
    if out.shape[-1] < length:
        out = np.pad(out, [(0, 0)] * (out.ndim - 1) + [(0, length - out.shape[-1])])
    return out[..., :length]


def spec(x):
    """HTDemucs._spec: espectrograma alinhado ao tamanho do segmento."""
    le = math.ceil(x.shape[-1] / HOP)
    pad = HOP // 2 * 3
    x = np.pad(x, [(0, 0)] * (x.ndim - 1) + [(pad, pad + le * HOP - x.shape[-1])],
               mode="reflect")
    z = stft(x)[..., :-1, :]
    return z[..., 2:2 + le]


def ispec(z, length):
    """HTDemucs._ispec."""
    z = np.pad(z, [(0, 0)] * (z.ndim - 2) + [(0, 1), (2, 2)])
    pad = HOP // 2 * 3
    le = HOP * math.ceil(length / HOP) + 2 * pad
    x = istft(z, le)
    return x[..., pad:pad + length]


def run_segment(sess, mix):
    """mix: (2, SEGMENT) -> (4 fontes, 2, SEGMENT)."""
    z = spec(mix[None])  # (1, 2, 2048, 336)
    mag = np.stack([z.real, z.imag], axis=2).reshape(1, 4, z.shape[-2], z.shape[-1])
    names = [i.name for i in sess.get_inputs()]
    out_x, out_xt = sess.run(None, {names[0]: mix[None].astype(np.float32),
                                    names[1]: mag.astype(np.float32)})
    b, s, c, fr, t = out_x.shape
    m = out_x.reshape(b, s, c // 2, 2, fr, t)
    zout = m[:, :, :, 0] + 1j * m[:, :, :, 1]
    return (out_xt + ispec(zout, SEGMENT))[0]


def separate(sess, audio, overlap=0.25):
    """Janelas sobrepostas com peso triangular (demucs.apply.apply_model)."""
    channels, length = audio.shape
    stride = int((1 - overlap) * SEGMENT)
    weight = np.concatenate([np.arange(1, SEGMENT // 2 + 2),
                             np.arange(SEGMENT - SEGMENT // 2 - 1, 0, -1)])[:SEGMENT]
    weight = weight / weight.max()
    out = np.zeros((len(SOURCES), channels, length))
    wsum = np.zeros(length)
    for offset in range(0, length, stride):
        chunk_len = min(SEGMENT, length - offset)
        delta = SEGMENT - chunk_len
        start = offset - delta // 2
        seg = np.zeros((channels, SEGMENT), dtype=np.float32)
        a, b = max(0, start), min(length, start + SEGMENT)
        seg[:, a - start:b - start] = audio[:, a:b]
        res = run_segment(sess, seg)
        res = res[..., delta // 2:delta // 2 + chunk_len]
        out[..., offset:offset + chunk_len] += weight[:chunk_len] * res
        wsum[offset:offset + chunk_len] += weight[:chunk_len]
        print(f"\r{min(offset + stride, length) / length:4.0%}", end="", flush=True)
    print()
    return out / wsum


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input")
    ap.add_argument("output", help="arquivo .wav com só a voz")
    ap.add_argument("--model", required=True, help="caminho do htdemucs.onnx")
    args = ap.parse_args()

    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", args.input, "-vn", "-ac", "2",
                                   "-ar", str(SR), "-f", "f32le", "-"])
    audio = np.frombuffer(raw, dtype=np.float32).reshape(-1, 2).T.astype(np.float64)
    # normalização como no demucs.separate
    ref = audio.mean(0)
    mean, std = ref.mean(), ref.std() + 1e-8
    sess = ort.InferenceSession(args.model)
    stems = separate(sess, (audio - mean) / std) * std + mean
    vocals = stems[SOURCES.index("vocals")].T.astype(np.float32)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2",
                    "-i", "-", args.output], input=vocals.tobytes(), check=True)
    print(f"voz salva em {args.output}")


if __name__ == "__main__":
    main()
