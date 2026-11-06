// usage: node render.js scene.html out.mp4|--preview t1,t2,...  outdir
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');
(async () => {
  const [html, target, extra] = process.argv.slice(2);
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  await page.goto('file://' + path.resolve(html));
  await page.evaluate(() => document.fonts.ready);
  await page.evaluate(() => Promise.all([...document.fonts].map(f => f.load())));
  if (target === '--preview') {
    for (const t of extra.split(',')) {
      await page.evaluate(t => render(+t), t);
      await page.screenshot({ path: `${process.argv[5]}/p_${t}.png` });
    }
  } else {
    const FPS = 30, N = Math.round(7.0 * FPS);
    const ff = spawn('ffmpeg', ['-v', 'error', '-y', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'png', '-i', '-',
      '-c:v', 'libx264', '-preset', 'medium', '-crf', '16', '-pix_fmt', 'yuv420p', target], { stdio: ['pipe', 'inherit', 'inherit'] });
    for (let f = 0; f < N; f++) {
      await page.evaluate(t => render(t), f / FPS);
      const buf = await page.screenshot({ type: 'png' });
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    }
    ff.stdin.end();
    await new Promise(r => ff.on('close', r));
  }
  await browser.close();
})();
