import subprocess, sys
SRC = sys.argv[1]; MUSIC = sys.argv[2]; OUT = sys.argv[3]
FPS = 30; BEAT = 60 / 130
FB = "/usr/share/fonts/opentype/inter/Inter-BlackItalic.otf"
FX = "/usr/share/fonts/opentype/inter/Inter-ExtraBoldItalic.otf"

# (src_start, src_end, beats, base_zoom, white_flash, slowmo)
SEG = [
    (17.3, 19.3, 4, 1.00, True,  False),
    (21.8, 24.9, 4, 1.06, False, False),
    (33.8, 35.8, 8, 1.12, True,  True),
    (36.0, 40.0, 4, 1.00, True,  False),
    (43.4, 46.5, 4, 1.15, False, False),
    (46.5, 49.1, 4, 1.10, True,  False),
    (49.2, 54.6, 4, 1.35, False, False),
    (54.7, 58.5, 4, 1.00, True,  False),
    (60.5, 64.5, 4, 1.10, False, False),
    (64.8, 69.4, 8, 1.00, True,  False),
]
S1_END_F = 489        # first speech ends at 16.3s
S2_START_F = 2311     # speaker fully on screen (77.03s), after original crossfade
A1_END = 17.2         # first speech audio tail ends
A2_START = 76.03      # second speech audio starts (J-cut)
PRE = 21              # pre-roll frames before the drop

f = []
f.append(f"[0:v]trim=start=16.6:end=17.4,setpts=PTS-STARTPTS,fps={FPS},scale=1296:2304:flags=lanczos,"
         f"zoompan=z='1.0+0.0025*on':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=864x1536:fps={FPS},"
         f"trim=end_frame={PRE},setpts=N/{FPS}/TB,setsar=1[pre]")
cum = 0; labels = ['[pre]']
for i, (s, e, b, z, fl, sm) in enumerate(SEG):
    f0 = round(cum * BEAT * FPS); cum += b; f1 = round(cum * BEAT * FPS)
    nf = f1 - f0; dur = nf / FPS
    chain = f"[0:v]trim=start={s}:end={e},setpts=PTS-STARTPTS,"
    if sm:
        chain += "minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1,"
    speed = (e - s) / dur
    chain += f"setpts=PTS/{speed:.5f},fps={FPS},tpad=stop_mode=clone:stop_duration=1,"
    chain += (f"scale=1296:2304:flags=lanczos,zoompan=z='{z}+0.22*exp(-on/3.2)':d=1:"
              f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=864x1536:fps={FPS},")
    chain += f"trim=end_frame={nf},setpts=N/{FPS}/TB,setsar=1"
    if fl:
        chain += ",fade=t=in:st=0:d=0.17:color=white"
    if i == len(SEG) - 1:
        chain += f",fade=t=out:st={dur-0.12:.3f}:d=0.12:color=white"
    chain += f"[g{i}]"; f.append(chain); labels.append(f"[g{i}]")
MONT = (round(cum * BEAT * FPS) + PRE) / FPS
P = PRE / FPS
SLOW0 = P + 8 * BEAT; SLOW1 = P + 16 * BEAT

def dt(text, font, size, color, x, y, en, extra=""):
    return (f"drawtext=fontfile={font}:text='{text}':fontsize={size}:fontcolor={color}:"
            f"x='{x}':y='{y}':enable='{en}'{extra}")

ov = [
    # opening title
    dt("FUTEBOL", FB, 132, "white", f"if(lt(t-{P},0.22),-tw+(tw+(W-tw)/2)*(t-{P})/0.22,(W-tw)/2)", "580",
       f"between(t,{P},{P+1.78})", ":shadowcolor=black@0.6:shadowx=6:shadowy=6"),
    dt("FEMININO", FB, 132, "0xFFD400", f"if(lt(t-{P},0.3),W-(W-(W-tw)/2)*(t-{P})/0.3,(W-tw)/2)", "720",
       f"between(t,{P+0.08},{P+1.78})", ":shadowcolor=black@0.6:shadowx=6:shadowy=6"),
    # persistent broadcast bug
    dt("MELHORES MOMENTOS", FX, 40, "black", f"if(lt(t-{P+1.85},0.25),-tw+(tw+70)*(t-{P+1.85})/0.25,70)", "190",
       f"between(t,{P+1.85},{MONT-0.15})", ":box=1:boxcolor=0xFFD400:boxborderw=18"),
    dt("FUTEBOL FEMININO", FX, 30, "white", f"if(lt(t-{P+1.95},0.25),-tw+(tw+70)*(t-{P+1.95})/0.25,70)", "262",
       f"between(t,{P+1.95},{MONT-0.15})", ":box=1:boxcolor=0xD7141A:boxborderw=12"),
    # replay badge during slow motion
    dt("REPLAY", FB, 46, "white", "W-tw-70", "190",
       f"between(t,{SLOW0:.3f},{SLOW1:.3f})", ":box=1:boxcolor=0xD7141A:boxborderw=16"),
]
f.append("".join(labels) + f"concat=n={len(SEG)+1}:v=1:a=0,"
         "eq=contrast=1.12:saturation=1.35:brightness=0.01:gamma=0.97,unsharp=5:5:0.55,"
         "vignette=angle=PI/5," + ",".join(ov) + ",format=yuv420p[mont]")
f.append(f"[0:v]trim=end_frame={S1_END_F},setpts=PTS-STARTPTS,setsar=1,format=yuv420p[v1]")
f.append(f"[0:v]trim=start_frame={S2_START_F},setpts=PTS-STARTPTS,setsar=1,format=yuv420p[v2]")
f.append("[v1][mont][v2]concat=n=3:v=1:a=0[vout]")

# audio: original speech untouched, silence under montage, music on top
S1_END = S1_END_F / FPS; LEAD = S2_START_F / FPS - A2_START
GAP = S1_END + MONT - LEAD - A1_END
f.append(f"[0:a]atrim=end={A1_END},asetpts=PTS-STARTPTS[a1]")
f.append(f"[0:a]atrim=start={A2_START},asetpts=PTS-STARTPTS[a2]")
f.append(f"anullsrc=r=44100:cl=stereo,atrim=duration={GAP:.5f}[as]")
f.append("[a1][as][a2]concat=n=3:v=0:a=1,aformat=sample_rates=44100:channel_layouts=stereo,asplit[sp][key]")
f.append(f"[1:a]volume='if(between(t,{S1_END+P-1.85:.3f},{S1_END+MONT:.3f}),1,1.9)':eval=frame[mus0]")
f.append("[mus0][key]sidechaincompress=threshold=0.03:ratio=5:attack=20:release=350[mus]")
f.append("[sp][mus]amix=inputs=2:normalize=0:duration=first,alimiter=limit=0.95[aout]")

open("fc.txt", "w").write(";\n".join(f))
cmd = ["ffmpeg", "-y", "-v", "error", "-stats", "-i", SRC, "-i", MUSIC, "-filter_complex_script", "fc.txt",
       "-map", "[vout]", "-map", "[aout]", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
       "-profile:v", "high", "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "aac", "-b:a", "192k",
       "-movflags", "+faststart", OUT]
print("montage", MONT, "gap", GAP, "T0", S1_END + P, "total", S1_END + MONT + (4285 - S2_START_F) / FPS)
subprocess.run(cmd, check=True)
