import json, sys
w = [list(x) for x in json.load(open(sys.argv[1]))["src.mp4"]]
fix = {63: "uma", 64: "cicatriz", 66: "grande", 71: "lábio", 138: "muito", 139: "emotiva,",
       170: "propus", 218: "no", 220: "de", 222: "ver", 1: "Aproximadamente"}
drop = {0, 60, 102, 149, 177, 206, 248, 273}  # cortados do vídeo ("né?" soltos)
hide = {140}  # só some da legenda (o áudio "muita motiva" vira "muito emotiva")
for i, t in fix.items():
    if t: w[i][2] = t
EMPH = {  # b-index-tuple: s-indices
    (2, 3, 4): [1], (16,): [13, 14, 15], (23, 24): [20, 21, 22], (35,): [33, 34],
    (54, 55): [52, 53], (64,): [63], (80,): [78, 79], (84, 85, 86): [82, 83],
    (111,): [110], (117,): [116], (146, 147, 148): [144, 145], (155,): [153, 154],
    (182,): [180, 181], (193,): [191, 192], (196, 197): [194, 195], (224,): [222, 223],
    (230,): [226, 227, 228, 229], (241, 242): [238, 239, 240], (247,): [246],
    (265, 266): [264], (280,): [278, 279], (281,): [], (283,): [282],
}
HOOK = list(range(218, 231))
LEAK_BEFORE = {198, 215, 249}

def segments(idx):
    """Agrupa palavras em trechos contínuos (quebra em pausas > 0.30s ou palavra removida)."""
    segs, cur = [], []
    for i in idx:
        if i in drop:
            if cur: segs.append(cur); cur = []
            continue
        if cur and (w[i][0] - w[cur[-1]][1] > 0.30 or i - cur[-1] > 1 or i in LEAK_BEFORE):
            segs.append(cur); cur = []
        cur.append(i)
    if cur: segs.append(cur)
    return segs

hook = segments(HOOK)
story = segments(range(1, len(w)))
plan = []  # (a, b, bw, words)
for group, bw in ((hook, True), (story, False)):
    for k, seg in enumerate(group):
        a = w[seg[0]][0] - 0.12
        b = w[seg[-1]][1] + 0.16
        # não invade a palavra vizinha (nem removida)
        prev_end = w[seg[0] - 1][1] if seg[0] > 0 else 0
        nxt_start = w[seg[-1] + 1][0] if seg[-1] + 1 < len(w) else 1e9
        a = max(a, (prev_end + w[seg[0]][0]) / 2)
        b = min(b, (w[seg[-1]][1] + nxt_start) / 2)
        plan.append([round(a, 3), round(b, 3), bw, seg])

# junta trechos que ficariam com emenda minúscula (mesma fala contínua)
merged = []
for p in plan:
    if merged and not p[2] and not merged[-1][2] and p[0] - merged[-1][1] < 0.06 \
            and p[3][0] not in LEAK_BEFORE:
        merged[-1][1] = p[1]; merged[-1][3] += p[3]
    else:
        merged.append(p)
plan = merged

# linha do tempo editada
tmap, off, cuts = {}, 0.0, []
for j, (a, b, bw, seg) in enumerate(plan):
    if j: cuts.append(round(off, 3))
    for i in seg:
        tmap[(j, i)] = round(off + w[i][0] - a, 2)
    for i in list(seg):
        if i in hide: seg.remove(i)
    off += b - a
total = off

# legendas
emph_of = {}
for bs, ss in EMPH.items():
    for i in bs: emph_of[i] = bs
chunks = []
for j, (a, b, bw, seg) in enumerate(plan):
    k = 0
    while k < len(seg):
        i = seg[k]
        later = [bs for bs in EMPH if bs[0] in seg[k:] and set(EMPH[bs]) and EMPH[bs][0] == i]
        if later:
            bs = later[0]; ss = EMPH[bs]
            if all(x in seg for x in ss + list(bs)):
                chunks.append([("s", "l", [(tmap[(j, x)], w[x][2]) for x in ss]),
                               ("b", "l", [(tmap[(j, x)], w[x][2]) for x in bs])])
                k = seg.index(bs[-1]) + 1; continue
        if i in emph_of and emph_of[i][0] == i and all(x in seg for x in emph_of[i]):
            bs = emph_of[i]
            chunks.append([("b", "c", [(tmap[(j, x)], w[x][2]) for x in bs])])
            k = seg.index(bs[-1]) + 1; continue
        grp = [i]
        while k + len(grp) < len(seg) and len(grp) < 2:
            n = seg[k + len(grp)]
            if n in emph_of or any(EMPH[bs] and EMPH[bs][0] == n for bs in EMPH): break
            if w[n][0] - w[grp[-1]][0] > 0.22: break
            grp.append(n)
        chunks.append([("n", "c", [(tmap[(j, x)], w[x][2]) for x in grp])])
        k += len(grp)

leaks = [cuts[i] for i, p in enumerate(plan[1:]) if p[3][0] in LEAK_BEFORE or plan[i][2]]
# zoom alterna a cada corte e também nas trocas de frase dentro de trechos longos
marks = set(cuts)
for j, (a, b, bw, seg) in enumerate(plan):
    last = tmap[(j, seg[0])]
    for x, y in zip(seg, seg[1:]):
        t = tmap[(j, y)] - 0.06
        pause = w[y][0] - w[x][1]
        prev = max([m for m in marks if m <= t] + [0])
        natural = w[x][2][-1] in ",.?" or pause >= 0.15
        if (t - prev > (2.4 if natural else 3.6)) \
                and min([m for m in marks if m > t] + [1e9]) - t > 1.5:
            marks.add(round(t, 2)); last = t
jump = []
z = 1.0
for c in sorted(marks):
    if c in leaks: z = 1.0
    else: z = 1.14 if z == 1.0 else 1.0
    jump.append((c, z))

out = ['"""Roteiro do relato (IMG_1715): prótese após cirurgia de tumor na face.',
       '',
       'Editado no estilo da referência: gancho em preto e branco, pausas e "né?"',
       'removidos com folga, zoom alternado a cada corte (esconde os cortes secos) e',
       'brilho de luz nas viradas da história. Gerado por build1715.py; tempos =',
       f'montagem final ({total:.1f}s).', '"""', '',
       '# (início, fim, preto_e_branco) de cada trecho do vídeo original, na ordem',
       'EDIT = [']
for a, b, bw, seg in plan:
    out.append(f'    ({a:.3f}, {b:.3f}, {bw}),  # {" ".join(w[i][2] for i in seg)[:70]}')
out += [']', '', 'DYN_ROLE_SIZES = {"n": 62, "s": 52, "b": 112}', 'DYN_CENTER_Y = 1400', '',
        '# Legenda dinâmica (Outfit Bold): blocos de linhas (papel, alinhamento, palavras)',
        'DYNAMIC_CHUNKS = [']
for ch in chunks:
    lines = ", ".join(f'("{r}", "{al}", [{", ".join(f"({t:.2f}, {json.dumps(x, ensure_ascii=False)})" for t, x in ws)}])' for r, al, ws in ch)
    out.append(f'    [{lines}],')
out += [']', '', 'CAMERA = {',
        '    "cuts": [],',
        f'    "punch_ins": {jump},',
        f'    "leaks": {leaks},',
        '    "drift": 0.0,',
        '    "anchor": [(0.0, (0.50, 0.18))],',
        '}', '', 'OUTPUT_SIZE = (1080, 1920)', '']
open(sys.argv[2], "w").write("\n".join(out))
print("trechos", len(plan), "total", round(total, 2), "cortes", len(cuts), "leaks", leaks)
