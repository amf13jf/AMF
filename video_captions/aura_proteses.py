"""Roteiro do vídeo "Aura - Próteses e reabilitações" (já montado, 31s).

Transcrito com Whisper e revisado à mão. O primeiro take (pergunta da maçã)
vira um motion em tela cheia: a maçã gira e ganha uma mordida a cada
palavra-chave. A apresentação da Dra vira uma plaquinha de nome, e o resto
segue o padrão da Aura (legenda Outfit Bold, cortes leves e zooms).
"""

DYN_ROLE_SIZES = {"n": 62, "s": 52, "b": 116}
DYN_CENTER_Y = 1400

# Legenda dinâmica (Outfit Bold): cada bloco é uma lista de linhas
# (papel, alinhamento, [(início, palavra), ...]). Papéis: "n" normal,
# "s" pequena, "b" grande. Alinhamento dentro do bloco: "l", "c" ou "r".
DYNAMIC_CHUNKS = [
    [("n", "c", [(4.00, "Pra"), (4.08, "quem"), (4.20, "nunca")])],
    [("n", "c", [(4.42, "passou"), (4.70, "por")])],
    [("n", "c", [(4.94, "isso,")])],
    [("s", "l", [(5.32, "pode"), (5.46, "parecer"), (5.80, "uma")]),
     ("b", "l", [(6.06, "bobagem.")])],
    [("n", "c", [(6.64, "Só"), (6.76, "quem"), (6.90, "precisa")])],
    [("s", "l", [(7.26, "pensar")]),
     ("b", "l", [(7.62, "duas"), (8.00, "vezes")])],
    [("s", "l", [(8.44, "antes"), (8.72, "de"), (8.92, "dar"), (9.06, "uma")]),
     ("b", "l", [(9.16, "mordida")])],
    [("s", "l", [(9.62, "sabe"), (10.00, "o"), (10.20, "que"), (10.20, "isso")]),
     ("b", "l", [(10.36, "significa.")])],
    [("n", "c", [(14.40, "e"), (14.44, "acompanho"), (14.88, "pessoas")])],
    [("s", "l", [(15.22, "há"), (15.50, "mais"), (15.68, "de")]),
     ("b", "l", [(15.82, "12"), (16.04, "anos")])],
    [("s", "l", [(16.34, "que"), (16.56, "enfrentam"), (17.08, "esse")]),
     ("b", "l", [(17.34, "problema.")])],
    [("n", "c", [(18.04, "E"), (18.20, "sabe"), (18.40, "de")])],
    [("n", "c", [(18.56, "uma"), (18.68, "coisa?")])],
    [("n", "c", [(19.26, "Na"), (19.34, "maioria"), (19.54, "das")])],
    [("n", "c", [(19.84, "vezes,")])],
    [("s", "l", [(20.20, "uma")]),
     ("b", "l", [(20.40, "prótese")])],
    [("s", "l", [(20.78, "pode"), (21.02, "fazer"), (21.28, "uma")]),
     ("b", "l", [(21.38, "diferença"), (21.60, "enorme.")])],
    [("s", "l", [(22.38, "E"), (22.46, "até"), (22.66, "aqueles")]),
     ("b", "l", [(22.98, "alimentos")])],
    [("n", "c", [(23.32, "que"), (23.62, "você")])],
    [("n", "c", [(23.90, "evita"), (24.26, "há")])],
    [("n", "c", [(24.48, "anos")])],
    [("s", "l", [(24.68, "podem"), (25.10, "voltar"), (25.42, "a"), (25.60, "fazer"), (25.74, "parte"), (26.08, "da"), (26.24, "sua")]),
     ("b", "l", [(26.38, "rotina.")])],
    [("n", "c", [(26.88, "Quer"), (26.94, "saber")])],
    [("s", "l", [(27.20, "quais"), (27.40, "são"), (27.58, "as")]),
     ("b", "l", [(27.68, "possibilidades")])],
    [("n", "c", [(28.18, "pra"), (28.40, "você?")])],
    [("n", "c", [(28.70, "Clique")])],
    [("n", "c", [(29.30, "no"), (29.42, "link")])],
    [("s", "l", [(29.70, "e"), (30.00, "mande"), (30.24, "uma")]),
     ("b", "l", [(30.30, "mensagem.")])],
]

MOTIONS = [{
    # "Você tem medo de morder uma maçã com receio do que possa acontecer com seus dentes?"
    "kind": "apple",
    "start": -0.4,  # já aparece inteiro no primeiro quadro
    "end": 4.25,
    "spin": 38,  # graus por segundo
    "bites": [(75, 0.90), (220, 1.90), (310, 2.80)],  # (posição na maçã, hora da mordida)
    "line": [(0.00, "Você"), (0.22, "tem"), (0.42, "medo"), (0.68, "de"), (0.84, "*morder"),
             (1.06, "uma"), (1.24, "*maçã")],
    "line2": [(1.64, "com"), (1.84, "receio"), (2.32, "do"), (2.38, "que"), (2.48, "possa"),
              (2.70, "acontecer"), (3.12, "com"), (3.36, "seus")],
    "big": (3.50, "dentes?"),
}]

# "Eu sou a doutora Júnia, da Clínica Aura Odontologia Humanizada"
NAMETAGS = [{"start": 11.00, "end": 14.35, "name": "Dra. Junia Almeida",
             "sub": "Aura Odontologia Humanizada", "y": 1500}]

CAMERA = {
    "cuts": [4.0, 6.667, 10.933, 17.9, 22.333, 26.867],
    "punch_ins": [(14.40, 1.12), (20.18, 1.12), (24.66, 1.12), (28.68, 1.12)],
    "drift": 0.03,
    "cut_zoom": 0.05,
    "cut_blur": 4,
    "anchor": [(0.0, (0.50, 0.20)), (10.933, (0.40, 0.30)), (17.9, (0.50, 0.25)),
               (22.333, (0.50, 0.22)), (26.867, (0.50, 0.22))],
}

OUTPUT_SIZE = (1080, 1920)
