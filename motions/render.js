const {chromium}=require('playwright');const {spawn}=require('child_process');const path=require('path');
const QS=[['01-pedido-minimo','Qual o pedido mínimo?'],['02-tipos-de-meias','Quais tipos de meias vocês vendem?'],['03-so-atacado','É só no atacado?'],['04-antiderrapantes-personalizar','Meias antiderrapantes, tem como personalizar?']];
const FPS=30, DUR=parseFloat(process.env.DUR||'6');
(async()=>{const b=await chromium.launch();const pg=await b.newPage({viewport:{width:1080,height:1920}});
for(const [name,q] of QS){ for(const alpha of [0,1]){
  await pg.goto('file://'+path.resolve('template.html')+'?q='+encodeURIComponent(q)+'&alpha='+alpha);
  await pg.evaluate(()=>document.fonts.ready);
  const out=alpha?`out/${name}-transparente.mov`:`out/${name}.mp4`;
  const args=['-y','-f','image2pipe','-framerate',''+FPS,'-i','-',
    ...(alpha?['-c:v','prores_ks','-profile:v','4444','-pix_fmt','yuva444p10le']:['-c:v','libx264','-pix_fmt','yuv420p','-crf','18','-movflags','+faststart']),out];
  const ff=spawn('ffmpeg',args,{stdio:['pipe','ignore','inherit']});
  for(let i=0;i<FPS*DUR;i++){await pg.evaluate(t=>render(t),i/FPS);
    const buf=await pg.screenshot({type:'png',omitBackground:!!alpha});
    if(!ff.stdin.write(buf)) await new Promise(r=>ff.stdin.once('drain',r));}
  ff.stdin.end(); await new Promise(r=>ff.on('close',r)); console.log('ok',out);
}}
await b.close();})();
