"""Roteiro com tempos (segundos) do vídeo "Aura - Implante".

Transcrito com Whisper (palavra a palavra) e revisado à mão. A Dra está de
jaleco o vídeo todo, então é só legenda dinâmica (Outfit Bold) + motions.
"""

# Legenda dinâmica (Outfit Bold): cada bloco é uma lista de linhas
# (papel, alinhamento, [(início, palavra), ...]). Papéis: "n" normal,
# "s" pequena, "b" grande. Alinhamento dentro do bloco: "l", "c" ou "r".
DYNAMIC_CHUNKS = [
    [("n", "c", [(0.00, "Você"), (0.24, "que"), (0.40, "é")])],
    [("s", "l", [(0.46, "aqui"), (0.58, "da")]),
     ("b", "l", [(0.66, "Zona"), (0.84, "Norte,")])],
    [("n", "c", [(1.22, "sabia"), (1.46, "que"), (1.68, "tem"), (1.76, "uma")])],
    [("s", "l", [(1.84, "clínica"), (2.16, "odontológica")]),
     ("b", "l", [(2.78, "completa")])],
    [("s", "l", [(3.22, "pertinho")]),
     ("b", "l", [(3.88, "de"), (4.02, "você?")])],
    [("n", "c", [(4.44, "Você"), (4.64, "que"), (4.84, "é")])],
    [("s", "l", [(4.86, "aqui"), (5.02, "de")]),
     ("b", "l", [(5.14, "São"), (5.26, "Judas")]),
     ("s", "r", [(5.38, "Tadeu,")])],
    [("n", "c", [(6.00, "sabia"), (6.24, "que"), (6.48, "tem"), (6.64, "uma")])],
    [("s", "l", [(6.78, "clínica"), (7.16, "odontológica")]),
     ("b", "l", [(7.78, "completa")])],
    [("s", "l", [(8.20, "pertinho")]),
     ("b", "l", [(8.84, "de"), (8.98, "você?")])],
    [("s", "l", [(9.50, "Aqui"), (9.76, "na")]),
     ("b", "l", [(9.92, "Aura")])],
    [("n", "c", [(10.12, "nós"), (10.28, "temos")])],
    [("s", "l", [(10.46, "diversos")]),
     ("b", "l", [(11.08, "tratamentos")])],
    [("n", "c", [(11.46, "para"), (11.66, "cuidar")])],
    [("s", "l", [(11.96, "da"), (12.10, "sua")]),
     ("b", "l", [(12.32, "saúde"), (12.76, "bucal.")])],
    [("n", "c", [(13.38, "Inclusive")])],
    [("n", "c", [(13.82, "nós"), (14.04, "temos")])],
    [("s", "l", [(14.22, "opções"), (14.74, "de")]),
     ("b", "l", [(14.92, "tratamento")])],
    [("n", "c", [(15.32, "para"), (15.50, "você")])],
    # 15,72s - 19,10s: motion 1 (perdeu dentes -> implante)
    [("n", "c", [(18.94, "Mas"), (19.10, "não")])],
    [("s", "l", [(19.28, "se")]),
     ("b", "l", [(19.42, "preocupe")])],
    [("n", "c", [(19.72, "em"), (19.90, "saber")])],
    [("s", "l", [(20.16, "qual")]),
     ("b", "l", [(20.50, "tratamento")]),
     ("s", "r", [(20.92, "precisa.")])],
    [("n", "c", [(21.60, "Nossa"), (21.76, "equipe")])],
    [("s", "l", [(22.02, "avalia"), (22.38, "o"), (22.54, "seu")]),
     ("b", "l", [(22.68, "caso")])],
    [("n", "c", [(23.06, "e"), (23.38, "explica")])],
    [("s", "l", [(23.76, "as")]),
     ("b", "l", [(23.90, "possibilidades.")])],
    # 24,85s - 27,62s: motion 2 (12 anos)
    [("s", "l", [(27.64, "E"), (28.02, "o"), (28.08, "primeiro")]),
     ("b", "l", [(28.34, "passo")])],
    [("n", "c", [(28.70, "pode"), (28.98, "estar")])],
    [("s", "l", [(29.18, "pertinho")]),
     ("b", "l", [(29.66, "da"), (29.76, "sua"), (29.90, "casa.")])],
    [("n", "c", [(30.52, "Entre"), (30.66, "em"), (30.72, "contato")])],
    [("s", "l", [(31.16, "e"), (31.30, "agende"), (31.62, "a"), (31.72, "sua")]),
     ("b", "l", [(31.92, "avaliação.")])],
]

MOTIONS = [
    {
        # "...que perdeu um ou mais dentes e quer voltar a mastigar com conforto."
        "kind": "signals",
        "start": 15.72,
        "end": 19.10,
        "switch": 17.12,
        "phase1": {
            "label": "PERDEU DENTES?",
            "icon": "lost",
            "lose": 16.30,  # o dente “some” enquanto ela fala "um ou mais"
            "line": [(15.76, "que"), (15.90, "perdeu"), (16.30, "um"), (16.44, "ou"),
                     (16.56, "mais")],
            "big": (16.80, "dentes"),
        },
        "phase2": {
            "label": "IMPLANTE",
            "icon": "implant",
            "line": [(17.22, "e"), (17.34, "quer"), (17.48, "voltar"), (17.70, "a")],
            "line2": [(17.88, "*mastigar"), (18.24, "com")],
            "big": (18.38, "conforto."),
        },
    },
    {
        # "Já são 12 anos cuidando de sorrisos aqui na região."
        "kind": "counter",
        "start": 24.85,
        "end": 27.62,
        "icon": "tooth",
        "label": "JÁ SÃO",
        "label_at": 24.90,
        "number": (25.24, 12),
        "unit": (25.56, "anos"),
        "line": [(25.88, "cuidando"), (26.26, "de"), (26.44, "*sorrisos")],
        "line2": [(26.90, "aqui"), (27.16, "na"), (27.30, "região.")],
    },
]
