"""Roteiro do vídeo "Aura - Chat 1" (já montado e com filtro, 33s).

Transcrito com Whisper e revisado à mão. Legenda Outfit Bold e três motions:
a janela de chat por cima da cena de abertura, os dois "nem toda..." com o
dente e a lista "pode / não pode" do chat. Os motions que terminam num corte
saem fechando em círculo por cima da cena seguinte (exit_wipe), para não
aparecer um pedaço da cena antiga antes do corte.
"""

DYN_ROLE_SIZES = {"n": 62, "s": 52, "b": 116}
DYN_CENTER_Y = 1400

# Legenda dinâmica (Outfit Bold): cada bloco é uma lista de linhas
# (papel, alinhamento, [(início, palavra), ...]). Papéis: "n" normal,
# "s" pequena, "b" grande. Alinhamento dentro do bloco: "l", "c" ou "r".
DYNAMIC_CHUNKS = [
    [("s", "l", [(4.76, "Você"), (5.00, "também")]),
     ("b", "l", [(5.34, "já"), (5.54, "fez"), (5.70, "isso,"), (6.16, "né?")])],
    [("s", "l", [(6.68, "Sente"), (6.90, "uma")]),
     ("b", "l", [(7.12, "dor"), (7.28, "no"), (7.42, "dente")])],
    [("s", "l", [(7.66, "e"), (7.86, "corre"), (8.10, "para"), (8.26, "o")]),
     ("b", "l", [(8.32, "chat")])],
    [("n", "c", [(8.52, "para"), (8.72, "pesquisar")])],
    [("n", "c", [(9.22, "se"), (9.36, "vai"), (9.44, "precisar")])],
    [("n", "c", [(9.82, "de")])],
    [("s", "l", [(9.92, "fazer"), (10.08, "um")]),
     ("b", "l", [(10.20, "canal.")])],
    [("n", "c", [(15.20, "Por"), (15.38, "isso"), (15.54, "não")])],
    [("n", "c", [(15.64, "dá"), (15.72, "para"), (15.82, "saber")])],
    [("s", "l", [(16.06, "o"), (16.20, "que"), (16.26, "está")]),
     ("b", "l", [(16.48, "acontecendo")])],
    [("s", "l", [(17.08, "olhando"), (17.86, "por"), (18.06, "uma")]),
     ("b", "l", [(18.24, "foto")])],
    [("s", "l", [(18.60, "ou"), (18.98, "pesquisando"), (19.50, "pelo")]),
     ("b", "l", [(19.70, "chat.")])],
    [("s", "l", [(25.80, "Para"), (26.08, "isso,"), (26.60, "só")]),
     ("b", "l", [(26.74, "vindo"), (26.94, "aqui.")])],
    [("n", "c", [(28.10, "E"), (28.30, "me"), (28.44, "conta"), (28.70, "aqui")])],
    [("n", "c", [(28.96, "qual"), (29.18, "foi"), (29.38, "a")])],
    [("n", "c", [(29.46, "coisa")])],
    [("s", "l", [(29.62, "mais")]),
     ("b", "l", [(29.88, "absurda")])],
    [("n", "c", [(30.46, "que"), (30.56, "você"), (30.76, "já")])],
    [("n", "c", [(30.94, "pesquisou")])],
    [("s", "l", [(31.46, "na")]),
     ("b", "l", [(31.56, "internet")])],
    [("n", "c", [(31.96, "que"), (32.24, "você"), (32.44, "achou")])],
    [("n", "c", [(32.70, "que"), (32.82, "tinha.")])],

]

MOTIONS = [
    {
        # "Chat, estou com uma mancha escura no dente e às vezes sinto dor. Será que preciso de canal?"
        "kind": "chat",
        "start": 0.0,
        "end": 4.55,  # termina inteira antes do corte (4,567s)
        "y": 1250,
        "title": "Chat",
        "message": [(0.00, "Chat,"), (0.44, "estou"), (0.58, "com"), (0.72, "uma"),
                    (0.82, "mancha"), (1.04, "escura"), (1.38, "no"), (1.56, "dente"),
                    (1.88, "e"), (2.08, "às"), (2.28, "vezes"), (2.50, "sinto"), (2.72, "dor."),
                    (3.24, "Será"), (3.50, "que"), (3.70, "preciso"), (3.92, "de"),
                    (4.30, "canal?")],
    },
    {
        # "Porque nem toda mancha escura é cárie e nem toda cárie está visível."
        "kind": "signals",
        "start": 10.70,
        "end": 15.32,  # sai em círculo por cima da cena seguinte (corte em 14,967s)
        "exit_wipe": 0.35,
        "switch": 12.88,
        "phase1": {
            "label": "NEM TODA",
            "icon": "tooth",
            "spot": 11.40,  # a mancha aparece em "mancha"
            "line": [(10.74, "Porque"), (10.96, "nem"), (11.22, "toda"), (11.40, "mancha"),
                     (11.74, "escura")],
            "big": (12.12, "é cárie"),
        },
        "phase2": {
            "label": "E NEM TODA",
            "icon": "lost",
            "lose": 14.20,  # o dente “some” em "está visível"
            "line": [(12.90, "e"), (13.36, "nem"), (13.56, "toda"), (13.70, "*cárie")],
            "line2": [(14.20, "está")],
            "big": (14.44, "visível."),
        },
    },
    {
        # "Você pode usar o chat para pesquisar, mas não pode usar para definir qual tratamento você precisa."
        "kind": "checklist",
        "start": 20.133,
        "end": 26.28,  # sai em círculo por cima da cena seguinte (corte em 25,933s)
        "exit_wipe": 0.35,
        "title": [(20.36, "Você"), (20.58, "pode"), (20.92, "usar"), (21.14, "o"), (21.26, "*chat")],
        "items": [
            [(21.44, "para"), (21.68, "*pesquisar")],
            [(22.88, "não"), (23.80, "para"), (24.10, "*definir")],
            [(24.56, "o"), (24.74, "*tratamento")],
        ],
        "marks": ["check", "cross", "cross"],
    },
]

OUTPUT_SIZE = (1080, 1920)
