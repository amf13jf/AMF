// Renderiza motion.html quadro a quadro e gera o MP4 com ffmpeg.
// Uso: node render.js  (requer playwright e ffmpeg)
const { chromium } = require('playwright');
const { execFileSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const FPS = 30, DURATION = 5;
const dir = __dirname;
const framesDir = path.join(dir, 'frames');

(async () => {
  fs.rmSync(framesDir, { recursive: true, force: true });
  fs.mkdirSync(framesDir);
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined });
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  await page.goto('file://' + path.join(dir, 'motion.html'));
  await page.evaluate(() => document.fonts.ready);
  const total = FPS * DURATION;
  for (let i = 0; i < total; i++) {
    await page.evaluate(t => window.render(t), i / FPS);
    await page.screenshot({ path: path.join(framesDir, `f${String(i).padStart(4, '0')}.png`) });
  }
  await browser.close();
  execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-framerate', String(FPS),
    '-i', path.join(framesDir, 'f%04d.png'), '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
    '-crf', '16', '-movflags', '+faststart', path.join(dir, 'almoco-voando.mp4')], { stdio: 'inherit' });
  fs.rmSync(framesDir, { recursive: true, force: true });
  console.log('ok: almoco-voando.mp4');
})();
