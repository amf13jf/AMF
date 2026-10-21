// Renderiza motion.html quadro a quadro, sintetiza o áudio (teclas, relógio,
// dobra do papel e whoosh) e junta tudo no MP4 com ffmpeg.
// Uso: node render.js  (requer playwright e ffmpeg)
const { chromium } = require('playwright');
const { execFileSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const FPS = 30, DURATION = 4, SR = 44100;
const dir = __dirname;
const framesDir = path.join(dir, 'frames');
const wavPath = path.join(dir, 'audio.wav');

// RNG determinístico para as variações de cada tecla
let seed = 7;
const rand = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
const noise = () => rand() * 2 - 1;

function synth(ev) {
  const buf = new Float32Array(SR * DURATION);
  const add = (t0, fn, len) => {
    const s0 = Math.round(t0 * SR);
    for (let i = 0; i < len * SR && s0 + i < buf.length; i++) buf[s0 + i] += fn(i / SR);
  };

  // Tecla: estalo agudo + ruído curto + "toc" grave do fundo da tecla
  for (const k of ev.keys) {
    const amp = 0.45 + 0.2 * rand();
    const pitch = (k.space ? 0.6 : 1) * (0.85 + 0.3 * rand());
    let lp = 0;
    add(k.t, x => {
      lp += 0.35 * (noise() - lp);
      const click = lp * Math.exp(-x * 260);
      const body = Math.sin(2 * Math.PI * 180 * pitch * x) * Math.exp(-x * 90) * 0.5;
      const top = Math.sin(2 * Math.PI * 2400 * pitch * x) * Math.exp(-x * 500) * 0.35;
      const rel = x > 0.035 ? lp * 0.4 * Math.exp(-(x - 0.035) * 400) : 0; // soltar a tecla
      return amp * (click + body + top + rel);
    }, 0.07);
  }

  // Relógio: tique agudo / taque um pouco mais grave
  for (const k of ev.ticks) {
    const f = k.tock ? 2600 : 3400;
    add(k.t, x => 0.7 * (Math.sin(2 * Math.PI * f * x) * Math.exp(-x * 350) + noise() * Math.exp(-x * 900) * 0.6), 0.04);
  }

  // Papel dobrando: dois amassados rápidos
  [0, 0.07].forEach((d, j) => {
    let lp = 0;
    add(ev.fold + d, x => { lp += 0.5 * (noise() - lp); return 0.35 * (1 - j * 0.3) * lp * Math.exp(-x * 45); }, 0.12);
  });

  // Whoosh: ruído filtrado com corte e volume subindo e descendo
  {
    let lp1 = 0, lp2 = 0;
    const D = ev.whooshDur;
    add(ev.whoosh, x => {
      const u = x / D;
      const env = Math.pow(Math.sin(Math.PI * Math.min(1, u)), 2) * (u < 0.55 ? 1 : 1 - (u - 0.55) * 0.6);
      const a = 0.04 + 0.22 * Math.sin(Math.PI * Math.min(1, u));
      lp1 += a * (noise() - lp1);
      lp2 += a * (lp1 - lp2);
      return 0.55 * env * lp2 * 3;
    }, D);
  }

  // Normaliza e escreve WAV 16-bit mono
  let peak = 0;
  for (const v of buf) peak = Math.max(peak, Math.abs(v));
  const g = 0.89 / (peak || 1);
  const data = Buffer.alloc(buf.length * 2);
  buf.forEach((v, i) => data.writeInt16LE(Math.round(Math.max(-1, Math.min(1, v * g)) * 32767), i * 2));
  const h = Buffer.alloc(44);
  h.write('RIFF', 0); h.writeUInt32LE(36 + data.length, 4); h.write('WAVE', 8);
  h.write('fmt ', 12); h.writeUInt32LE(16, 16); h.writeUInt16LE(1, 20); h.writeUInt16LE(1, 22);
  h.writeUInt32LE(SR, 24); h.writeUInt32LE(SR * 2, 28); h.writeUInt16LE(2, 32); h.writeUInt16LE(16, 34);
  h.write('data', 36); h.writeUInt32LE(data.length, 40);
  fs.writeFileSync(wavPath, Buffer.concat([h, data]));
}

(async () => {
  fs.rmSync(framesDir, { recursive: true, force: true });
  fs.mkdirSync(framesDir);
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined });
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  await page.goto('file://' + path.join(dir, 'motion.html'));
  await page.evaluate(() => document.fonts.ready);
  synth(await page.evaluate(() => window.AUDIO_EVENTS));
  const total = FPS * DURATION;
  for (let i = 0; i < total; i++) {
    await page.evaluate(t => window.render(t), i / FPS);
    await page.screenshot({ path: path.join(framesDir, `f${String(i).padStart(4, '0')}.png`) });
  }
  await browser.close();
  execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-framerate', String(FPS),
    '-i', path.join(framesDir, 'f%04d.png'), '-i', wavPath,
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '16',
    '-c:a', 'aac', '-b:a', '192k', '-t', String(DURATION),
    '-movflags', '+faststart', path.join(dir, 'almoco-voando.mp4')], { stdio: 'inherit' });
  fs.rmSync(framesDir, { recursive: true, force: true });
  fs.rmSync(wavPath, { force: true });
  console.log('ok: almoco-voando.mp4');
})();
