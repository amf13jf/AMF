"""Roteiro do esquete "paciente que veio sem sentir nada" (clipes IMG_1771..1781).

A montagem é feita antes (ver BASE_EDIT): os clipes são cortados com folga
(~0,2s antes da primeira palavra e ~0,25s depois da última) e unidos com fades
curtos de áudio. Os tempos abaixo são da montagem final (16s).
"""

# Montagem: (arquivo, início, fim) em segundos de cada clipe original, na ordem.
# IMG_1780 ("Nada!" em plano aberto) ficou de fora; usei o take fechado 1781.
BASE_EDIT = [
    ("IMG_1771_1.MOV", 3.50, 7.45),  # "Oi, doutora. Essa paciente que veio, ela tinha o quê?"
    ("IMG_1781_1.MOV", 1.35, 2.35),  # "Nada."
    ("IMG_1775_1.MOV", 0.70, 3.30),  # "Ué, mas ela veio sem sentir nada?"
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
    [("b", "c", [(4.24, "Nada.")])],
    [("n", "c", [(5.20, "Ué,"), (5.51, "mas")])],
    [("s", "l", [(5.63, "ela"), (5.81, "veio"), (6.05, "sem"), (6.31, "sentir")]),
     ("b", "l", [(6.69, "nada?")])],
    [("n", "c", [(7.76, "Isso"), (8.09, "mesmo,")])],
    [("s", "l", [(8.67, "ela"), (8.79, "é"), (8.87, "um"), (8.91, "exemplo"), (9.29, "de")]),
     ("b", "l", [(9.45, "paciente,")])],
    [("n", "c", [(9.93, "ela"), (9.99, "vem"), (10.31, "aqui")])],
    [("b", "c", [(10.51, "regularmente")])],
    [("s", "l", [(11.37, "de")]),
     ("b", "l", [(11.55, "seis"), (11.87, "em"), (12.01, "seis"), (12.21, "meses")])],
    [("n", "c", [(12.47, "fazer"), (12.81, "as"), (12.93, "suas")])],
    [("s", "l", [(13.01, "consultas")]),
     ("b", "l", [(13.33, "periódicas.")])],
    [("n", "c", [(14.41, "E"), (14.45, "aí")])],
    [("s", "l", [(14.57, "não"), (14.69, "tinha")]),
     ("b", "l", [(14.81, "nada")])],
    [("n", "c", [(14.97, "agora"), (15.21, "pra"), (15.35, "fazer.")])],
]

# Câmera: entrada leve nos cortes entre clipes, zoom lento e um "punch-in"
# (enquadramento mais fechado) no meio da explicação.
CAMERA = {
    "cuts": [3.950, 4.950, 7.550],
    "punch_ins": [9.93],
    "punch_zoom": 1.12,
    "drift": 0.03,
    "cut_zoom": 0.05,
    "cut_blur": 4,
    "anchor": [(0.0, (0.50, 0.22)), (3.95, (0.33, 0.18)), (4.95, (0.72, 0.15)),
               (7.55, (0.42, 0.22))],
}
