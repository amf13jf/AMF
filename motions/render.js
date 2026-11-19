const { chromium } = require('playwright');
const { execFileSync } = require('child_process');
const fs = require('fs'), path = require('path');
const FPS = 30;
const items = [
  ['01-como-tudo-comecou', 'Como tudo começou?'],
  ['02-desafios-de-empreender', 'Os desafios de empreender?'],
  ['03-construcao-entre-pausas', 'A construção do Entre Pausas?'],
  ['04-conquistas-e-significado', 'As conquistas e o significado de tudo isso?'],
  ['05-conselho-para-quem-esta-comecando', 'Um conselho para quem está começando a empreender?'],
];
const only = process.argv[2];
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  const out = path.join(__dirname, 'out'); fs.mkdirSync(out, { recursive: true });
  for (const [name, text] of items) {
    if (only && !name.startsWith(only)) continue;
    let n, dur;
    const grab = async (dir, extra) => {
      fs.rmSync(dir, { recursive: true, force: true }); fs.mkdirSync(dir, { recursive: true });
      await page.goto('file://' + path.join(__dirname, 'comment.html') + '?text=' + encodeURIComponent(text) + extra);
      dur = await page.evaluate(() => window.DURATION); n = Math.ceil(dur * FPS);
      for (let i = 0; i < n; i++) {
        await page.evaluate(t => window.render(t), i / FPS);
        await page.screenshot({ path: path.join(dir, String(i).padStart(4, '0') + '.png'), omitBackground: true });
      }
    };
    const fdir = path.join(__dirname, 'frames', name), gdir = fdir + '_white';
    await grab(fdir, '');
    await grab(gdir, '&bg=white');
    const inp = ['-y', '-framerate', String(FPS), '-i', path.join(fdir, '%04d.png')];
    // transparent overlay (ProRes 4444 with alpha)
    execFileSync('ffmpeg', [...inp, '-c:v', 'prores_ks', '-profile:v', '4444', '-pix_fmt', 'yuva444p10le', path.join(out, name + '_transparente.mov')], { stdio: 'ignore' });
    // white background MP4
    execFileSync('ffmpeg', ['-y', '-framerate', String(FPS), '-i', path.join(gdir, '%04d.png'), '-pix_fmt', 'yuv420p', '-c:v', 'libx264', '-crf', '18', '-movflags', '+faststart', path.join(out, name + '_fundobranco.mp4')], { stdio: 'ignore' });
    fs.rmSync(fdir,{recursive:true,force:true}); fs.rmSync(gdir,{recursive:true,force:true});
    console.log(name, n, 'frames', dur.toFixed(2) + 's');
  }
  await browser.close();
})();
