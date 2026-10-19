import subprocess, sys, os
S = sys.argv[1]; SRC = sys.argv[2]; PURURUCA = sys.argv[3]; OUT = sys.argv[4]
TAKE1_END = 5.5
# Take 02 shots from the pururuca video: (start, end)
TAKE2_SHOTS = [(0.0, 2.62), (17.6, 19.0), (19.4, 21.0)]
FONT = f"{S}/fonts/Anton-Regular.ttf"
TXT = f"{S}/build/txt"
VID_END = 11.12
TOTAL = VID_END + 3.6
WHITE, YELLOW = "white", "0xFFC629"
# (start, end, [(text, size, color)], top_y)
caps = [
  # Take 01
  (0.25, 2.7,  [("PEDIMOS DESCULPAS", 118, WHITE), ("A QUEM PROMETEU", 118, WHITE)], 1180),
  (2.7, 5.5,   [("ECONOMIZAR", 190, YELLOW), ("ESSA SEMANA...", 118, WHITE)], 1160),
  # Take 02
  (5.5, 7.6,   [("MAS UMA BARRIGA", 112, WHITE), ("DE PORCO", 112, WHITE), ("CROCANTE", 190, YELLOW)], 1080),
  (7.6, 9.4,   [("COM UMA CERVEJINHA", 112, WHITE), ("GELADA", 190, YELLOW)], 1160),
  (9.4, VID_END, [("HOJE SERIA", 112, WHITE), ("BOM DEMAIS,", 112, WHITE), ("NÉ?", 220, YELLOW)], 1060),
  # Take 03 (end card)
  (VID_END + 0.15, TOTAL, [("MANDA ESSE VÍDEO", 120, WHITE), ("PRA QUEM VAI", 120, WHITE),
                           ("ESQUECER", 190, YELLOW), ("A ECONOMIA", 190, YELLOW),
                           ("E TE ACOMPANHAR NESSA!", 104, WHITE)], 560),
]
segs = [f"[0:v]trim=0:{TAKE1_END},setpts=PTS-STARTPTS,delogo=x=770:y=1832:w=285:h=66,fps=30,setsar=1[s0]"]
for k, (a0, a1) in enumerate(TAKE2_SHOTS, 1):
    segs.append(f"[1:v]trim={a0}:{a1},setpts=PTS-STARTPTS,scale=1080:1920:force_original_aspect_ratio=increase,"
                f"crop=1080:1920,fps=30,setsar=1[s{k}]")
labels = "".join(f"[s{k}]" for k in range(len(segs)))
pre = ";".join(segs) + f";{labels}concat=n={len(segs)}:v=1:a=0[base]"
f = [f"[base]tpad=stop_mode=clone:stop_duration={TOTAL-VID_END+0.1}",
     f"boxblur=25:2:enable='gte(t,{VID_END})'",
     f"eq=brightness=-0.18:saturation=0.8:enable='gte(t,{VID_END})'"]
n = 0
for (t0, t1, lines, y) in caps:
    for i, (txt, size, col) in enumerate(lines):
        size = int(size * 0.8)
        n += 1
        p = f"{TXT}/{n}.txt"; open(p, "w").write(txt)
        ts = round(t0 + i * 0.12, 2)
        a = f"if(lt(t,{ts}),0,min(1,(t-{ts})/0.12))"
        yy = f"{y}+(1-min(1,max(0,(t-{ts})/0.15)))*40"
        f.append(f"drawtext=fontfile={FONT}:textfile={p}:fontsize={size}:fontcolor={col}"
                 f":borderw=7:bordercolor=black:shadowx=0:shadowy=8:shadowcolor=black@0.5"
                 f":x=(w-text_w)/2:y='{yy}':alpha='{a}':enable='between(t,{ts},{t1})'")
        y += int(size * 1.22)
vf = pre + ";" + ",".join(f) + "[v]"
af = f"[0:a]apad,atrim=0:{TOTAL},afade=t=out:st={VID_END-1.0}:d=1.4[a]"
cmd = ["ffmpeg", "-v", "error", "-y", "-i", SRC, "-i", PURURUCA, "-filter_complex", vf + ";" + af,
       "-map", "[v]", "-map", "[a]", "-t", str(TOTAL), "-c:v", "libx264", "-preset", "slow", "-crf", "18",
       "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", OUT]
subprocess.run(cmd, check=True)
