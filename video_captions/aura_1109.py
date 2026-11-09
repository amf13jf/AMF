"""Roteiro do esquete "paciente que veio sem sentir nada" (clipes IMG_1771..1781).

A montagem é feita antes (ver BASE_EDIT): os clipes são cortados com folga
(~0,2s antes da primeira palavra e ~0,25s depois da última) e unidos com fades
curtos de áudio. Os tempos abaixo são da montagem final (17s).
"""

# Montagem: (arquivo, início, fim) em segundos de cada clipe original, na ordem
# 1771 - 1780 - 1775 - 1781 - 1777.
BASE_EDIT = [
    ("IMG_1771_1.MOV", 3.50, 7.45),  # "Oi, doutora. Essa paciente que veio, ela tinha o quê?"
    ("IMG_1780_1.MOV", 0.90, 1.95),  # "Nada!"
    ("IMG_1775_1.MOV", 0.70, 3.30),  # "Ué, mas ela veio sem sentir nada?"
    ("IMG_1781_1.MOV", 1.35, 2.35),  # "Nada."
    ("IMG_1777_1.MOV", 0.20, 8.60),  # "Isso mesmo, ela é um exemplo de paciente..."
]

DYN_ROLE_SIZES = {"n": 60, "s": 50, "b": 116}

# Legenda dinâmica (Outfit Bold): cada bloco é uma lista de linhas
# (papel, alinhamento, [(início, palavra), ...]). Papéis: "n" normal,
# "s" pequena, "b" grande. Alinhamento dentro do bloco: "l", "c" ou "r".
DYNAMIC_CHUNKS = [
    [("n", "c", [(0.76, "Oi,"), (1.28, "doutora.")])],
    [("n", "c", [(1.92, "Essa"), (2.00, "paciente"), (2.48, "que"), (2.62, "veio,")])],
    [("s", "l", [(2.78, "ela"), (3.04, "tinha")]),
     ("b", "l", [(3.20, "o"), (3.36, "quê?")])],
    [("b", "c", [(4.21, "Nada!")])],
    [("n", "c", [(5.25, "Ué,"), (5.56, "mas")])],
    [("s", "l", [(5.68, "ela"), (5.86, "veio"), (6.10, "sem"), (6.36, "sentir")]),
     ("b", "l", [(6.74, "nada?")])],
    [("b", "c", [(7.89, "Nada.")])],
    [("n", "c", [(8.81, "Isso"), (9.14, "mesmo,")])],
    [("s", "l", [(9.72, "ela"), (9.84, "é"), (9.92, "um"), (9.96, "exemplo"), (10.34, "de")]),
     ("b", "l", [(10.50, "paciente,")])],
    [("n", "c", [(10.98, "ela"), (11.04, "vem"), (11.36, "aqui")])],
    [("b", "c", [(11.56, "regularmente")])],
    [("s", "l", [(12.42, "de")]),
     ("b", "l", [(12.60, "seis"), (12.92, "em"), (13.06, "seis"), (13.26, "meses")])],
    [("n", "c", [(13.52, "fazer"), (13.86, "as"), (13.98, "suas")])],
    [("s", "l", [(14.06, "consultas")]),
     ("b", "l", [(14.38, "periódicas.")])],
    [("n", "c", [(15.46, "E"), (15.50, "aí")])],
    [("s", "l", [(15.62, "não"), (15.74, "tinha")]),
     ("b", "l", [(15.86, "nada")])],
    [("n", "c", [(16.02, "agora"), (16.26, "pra"), (16.40, "fazer.")])],
]

# Câmera: entrada leve nos cortes entre clipes, zoom lento e um "punch-in"
# (enquadramento mais fechado) no meio da explicação.
CAMERA = {
    "cuts": [3.95, 5.00, 7.60, 8.60],
    "punch_ins": [10.98],
    "punch_zoom": 1.12,
    "drift": 0.03,
    "cut_zoom": 0.05,
    "cut_blur": 4,
    "anchor": [(0.0, (0.50, 0.22)), (3.95, (0.38, 0.18)), (5.00, (0.72, 0.15)),
               (7.60, (0.33, 0.18)), (8.60, (0.42, 0.22))],
}

# Legenda um pouco mais alta (no plano aberto do notebook a mesa é branca)
DYN_CENTER_Y = 1320

# Exporta no 9:16 exato do Reels (1216x2160 deixava um fio preto em alguns players)
OUTPUT_SIZE = (1080, 1920)
