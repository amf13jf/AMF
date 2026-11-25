"""Roteiro do vídeo "Aura - Mito x Verdade" (60s, 5 perguntas).

Transcrito com Whisper e revisado à mão. Formato mito x verdade: em cada
pergunta entra um cartão vinho "MITO OU VERDADE? · n/5" com a pergunta sendo
escrita; na resposta, um carimbo MITO (✗) ou VERDADE (✓); a explicação vem na
legenda Outfit Bold; o convite final vira um balão de comentário.
"""

DYN_ROLE_SIZES = {"n": 62, "s": 52, "b": 116}
DYN_CENTER_Y = 1420

# Legenda dinâmica (Outfit Bold): cada bloco é uma lista de linhas
# (papel, alinhamento, [(início, palavra), ...]). Papéis: "n" normal,
# "s" pequena, "b" grande. Alinhamento dentro do bloco: "l", "c" ou "r".
DYNAMIC_CHUNKS = [
    [("s", "l", [(4.44, "mas"), (4.64, "é"), (4.78, "muito")]),
     ("b", "l", [(5.06, "importante")])],
    [("n", "c", [(5.46, "dizer")])],
    [("s", "l", [(5.84, "que"), (6.08, "o")]),
     ("b", "l", [(6.16, "clareamento")])],
    [("n", "c", [(6.74, "só"), (7.18, "pode")])],
    [("n", "c", [(7.58, "ser"), (7.84, "feito")])],
    [("s", "l", [(8.24, "com"), (8.54, "o")]),
     ("b", "l", [(8.62, "acompanhamento")])],
    [("s", "l", [(9.12, "do")]),
     ("b", "l", [(9.46, "dentista.")])],
    [("s", "l", [(14.98, "é")]),
     ("b", "l", [(15.22, "indispensável")])],
    [("s", "l", [(16.06, "o"), (16.34, "uso")]),
     ("b", "l", [(16.52, "fio"), (16.74, "dental")])],
    [("n", "c", [(17.04, "porque"), (17.40, "é")])],
    [("n", "c", [(17.64, "só"), (17.74, "ele")])],
    [("s", "l", [(17.96, "que"), (18.08, "vai"), (18.18, "tirar"), (18.38, "a")]),
     ("b", "l", [(18.54, "sujeirinha")])],
    [("n", "c", [(18.94, "que"), (19.06, "fica"), (19.18, "no")])],
    [("n", "c", [(19.36, "meio"), (19.50, "dos"), (19.62, "seus")])],
    [("n", "c", [(19.74, "dentes.")])],
    [("s", "l", [(22.94, "implante")]),
     ("b", "l", [(23.42, "não"), (23.76, "dói,")])],
    [("s", "l", [(24.40, "isso"), (24.56, "eu"), (24.72, "posso"), (24.88, "te")]),
     ("b", "l", [(25.08, "afirmar.")])],
    [("n", "c", [(25.72, "Isso"), (25.88, "porque")])],
    [("s", "l", [(26.18, "o")]),
     ("b", "l", [(26.28, "procedimento")])],
    [("s", "l", [(26.70, "é"), (26.90, "feito"), (27.12, "de"), (27.28, "modo")]),
     ("b", "l", [(27.46, "planejado")])],
    [("s", "l", [(28.26, "e"), (28.66, "com")]),
     ("b", "l", [(28.82, "anestesia,")])],
    [("n", "c", [(29.66, "é"), (29.66, "claro.")])],
    [("n", "c", [(34.46, "na"), (34.72, "verdade")])],
    [("n", "c", [(35.06, "o"), (35.26, "que"), (35.30, "ela")])],
    [("n", "c", [(35.40, "faz")])],
    [("s", "l", [(35.74, "é")]),
     ("b", "l", [(36.00, "agredir")])],
    [("s", "l", [(36.44, "a"), (36.56, "sua")]),
     ("b", "l", [(36.74, "gengiva")])],
    [("s", "l", [(37.30, "e"), (37.50, "vai"), (37.62, "te"), (37.76, "causar"), (38.12, "muitas")]),
     ("b", "l", [(38.52, "retrações")])],
    [("n", "c", [(39.12, "de"), (39.32, "gengiva")])],
    [("s", "l", [(39.62, "e"), (39.74, "te"), (39.76, "trazer")]),
     ("b", "l", [(40.00, "dor.")])],
    [("b", "c", [(45.42, "precisa"), (45.80, "sim.")])],
    [("n", "c", [(46.80, "Vamos"), (47.02, "lembrar")])],
    [("n", "c", [(47.40, "que"), (47.62, "o"), (47.70, "dentinho")])],
    [("n", "c", [(47.98, "de"), (48.12, "leite")])],
    [("s", "l", [(48.34, "também")]),
     ("b", "l", [(48.72, "dói")])],
    [("s", "l", [(49.28, "e")]),
     ("b", "l", [(49.42, "dói"), (49.66, "muito.")])],
    [("n", "c", [(50.34, "Você"), (50.54, "vai"), (50.68, "deixar")])],
    [("n", "c", [(50.94, "o"), (51.10, "seu"), (51.22, "filho")])],
    [("s", "l", [(51.50, "sentindo")]),
     ("b", "l", [(51.84, "dor")])],
    [("n", "c", [(52.16, "e")])],
    [("n", "c", [(52.70, "vamos"), (52.90, "lembrar")])],
    [("n", "c", [(53.28, "também"), (53.60, "que")])],
    [("n", "c", [(53.82, "isso"), (53.96, "é"), (54.06, "um")])],
    [("s", "l", [(54.10, "processo"), (54.32, "de")]),
     ("b", "l", [(54.58, "infecção")])],
    [("n", "c", [(55.14, "e")])],
    [("s", "l", [(55.66, "algo"), (55.86, "muito")]),
     ("b", "l", [(56.14, "grave")])],
    [("n", "c", [(56.38, "na"), (56.62, "saúde"), (56.86, "do")])],
    [("n", "c", [(57.02, "seu"), (57.12, "filho.")])],

]

# Cartões de pergunta, carimbos e o balão de comentário (todos por cima do vídeo;
# nenhum atravessa um corte de cena)
MOTIONS = [
    {"kind": "question", "start": 0.0, "end": 3.6, "count": "1/5",
     "words": [(0.00, "Júnia,"), (0.80, "é"), (0.94, "verdade"), (1.24, "que"), (1.50, "fazer"), (1.74, "clareamento"), (2.16, "enfraquece"), (2.84, "os"), (2.98, "dentes?")]},
    {"kind": "verdict", "verdict": "mito", "start": 3.62, "end": 4.7},
    {"kind": "question", "start": 10.22, "end": 13.95, "count": "2/5",
     "words": [(10.32, "Eu"), (10.44, "preciso"), (10.82, "mesmo"), (11.18, "passar"), (11.62, "o"), (11.94, "fio"), (11.98, "dental"), (12.22, "todos"), (12.72, "os"), (13.02, "dias?")]},
    {"kind": "verdict", "verdict": "verdade", "start": 13.98, "end": 15.0},
    {"kind": "question", "start": 20.22, "end": 21.95, "count": "3/5",
     "words": [(20.24, "É"), (20.34, "verdade"), (20.70, "que"), (20.92, "implante"), (21.28, "dói?")]},
    {"kind": "verdict", "verdict": "mito", "start": 21.98, "end": 22.92},
    {"kind": "question", "start": 29.7, "end": 33.62, "count": "4/5",
     "words": [(29.72, "É"), (30.02, "verdade"), (30.40, "que"), (30.82, "a"), (30.94, "escova"), (31.36, "com"), (31.54, "cerdas"), (31.98, "duras"), (32.42, "limpa,"), (32.98, "melhor?")]},
    {"kind": "verdict", "verdict": "mito", "start": 33.68, "end": 34.55},
    {"kind": "question", "start": 40.62, "end": 44.55, "count": "5/5",
     "words": [(40.76, "Dente"), (40.96, "de"), (41.20, "leite,"), (41.82, "com"), (41.90, "cárie"), (42.38, "ou"), (42.58, "canal"), (42.92, "não"), (43.08, "precisa"), (43.54, "tratar,"), (44.00, "né?")]},
    {"kind": "verdict", "verdict": "mito", "start": 44.62, "end": 45.45},
    {"kind": "chat", "start": 57.40, "end": 60.65, "y": 1250, "title": "Comentários",
     "subtitle": "deixe sua dúvida", "message": [(57.36, "Deixe"), (57.82, "aqui"), (58.00, "nos"), (58.08, "comentários"), (58.66, "a"), (58.98, "sua"), (59.16, "dúvida"), (59.52, "que"), (59.64, "eu"), (59.70, "te"), (59.78, "respondo.")]},
]

CAMERA = {
    "cuts": [10.2, 20.2, 29.867, 40.6, 57.5],
    "punch_ins": [(6.70, 1.12), (17.00, 1.12), (25.70, 1.12), (37.28, 1.12), (46.78, 1.12),
                  (50.32, 1.0), (52.68, 1.12)],
    "drift": 0.025,
    "cut_zoom": 0.05,
    "cut_blur": 4,
    "anchor": [(0.0, (0.42, 0.22))],
}

OUTPUT_SIZE = (1080, 1920)
