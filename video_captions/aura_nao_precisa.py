"""Roteiro do vídeo "Aura - Você não precisa disso" (já montado, 39s).

Transcrito com Whisper (palavra a palavra) e revisado à mão. Edição no estilo
dos últimos vídeos da Aura: legenda Outfit Bold, entrada leve com zoom nos
cortes de cena, enquadramentos mais fechados dentro das tomadas longas e um
motion de lista com check em "o que precisa fazer, o porquê e o quanto custa".
"""

DYN_ROLE_SIZES = {"n": 62, "s": 52, "b": 116}
DYN_CENTER_Y = 1400

# Legenda dinâmica (Outfit Bold): cada bloco é uma lista de linhas
# (papel, alinhamento, [(início, palavra), ...]). Papéis: "n" normal,
# "s" pequena, "b" grande. Alinhamento dentro do bloco: "l", "c" ou "r".
DYNAMIC_CHUNKS = [
    [("s", "l", [(0.00, "Você"), (0.20, "não")]),
     ("b", "l", [(0.34, "precisa"), (0.58, "disso.")])],
    [("n", "c", [(1.06, "Foi"), (1.14, "o"), (1.20, "que")])],
    [("n", "c", [(1.28, "eu"), (1.40, "disse"), (1.56, "para")])],
    [("n", "c", [(1.76, "uma"), (1.84, "paciente")])],
    [("n", "c", [(2.46, "que"), (2.90, "me")])],
    [("n", "c", [(3.00, "procurou")])],
    [("s", "l", [(3.40, "com"), (3.60, "o"), (3.64, "dente")]),
     ("b", "l", [(3.78, "quebrado")])],
    [("n", "c", [(4.20, "pensando"), (4.68, "que")])],
    [("n", "c", [(4.86, "teria"), (5.04, "que"), (5.20, "tirar")])],
    [("n", "c", [(5.38, "o"), (5.58, "dente"), (5.72, "para")])],
    [("s", "l", [(5.90, "colocar"), (6.10, "o")]),
     ("b", "l", [(6.30, "implante")])],
    [("n", "c", [(6.60, "e,"), (6.90, "na"), (6.96, "verdade,")])],
    [("n", "c", [(7.50, "era"), (7.64, "apenas")])],
    [("s", "l", [(7.90, "colocar"), (8.26, "uma")]),
     ("b", "l", [(8.54, "coroa.")])],
    [("n", "c", [(9.00, "E"), (9.10, "sabe"), (9.24, "por")])],
    [("n", "c", [(9.44, "que"), (9.52, "eu"), (9.62, "estou")])],
    [("n", "c", [(9.64, "te"), (9.72, "contando"), (10.00, "isso?")])],
    [("s", "l", [(10.50, "Porque"), (10.66, "nem")]),
     ("b", "l", [(10.82, "sempre")])],
    [("n", "c", [(11.14, "o"), (11.24, "paciente"), (11.58, "precisa")])],
    [("n", "c", [(11.96, "realizar"), (12.34, "o")])],
    [("n", "c", [(12.60, "tratamento")])],
    [("s", "l", [(12.86, "que"), (13.06, "está")]),
     ("b", "l", [(13.12, "imaginando.")])],
    [("n", "c", [(13.68, "Neste"), (13.84, "caso,")])],
    [("n", "c", [(14.26, "por"), (14.28, "exemplo,")])],
    [("n", "c", [(15.04, "o"), (15.14, "tratamento"), (15.40, "era")])],
    [("s", "l", [(15.62, "bem"), (15.84, "mais")]),
     ("b", "l", [(16.00, "simples")])],
    [("n", "c", [(16.34, "do"), (16.54, "que"), (16.62, "o")])],
    [("n", "c", [(16.68, "paciente"), (17.00, "estava")])],
    [("n", "c", [(17.80, "imaginando.")])],
    [("n", "c", [(18.36, "Apesar"), (18.76, "do")])],
    [("n", "c", [(18.90, "dente"), (19.12, "ter"), (19.34, "quebrado")])],
    [("n", "c", [(19.82, "uma"), (20.00, "grande"), (20.28, "parte,")])],
    [("n", "c", [(20.92, "ainda")])],
    [("s", "l", [(21.28, "era"), (21.46, "totalmente")]),
     ("b", "l", [(21.76, "possível")])],
    [("b", "c", [(23.00, "recuperar")])],
    [("n", "c", [(23.40, "e")])],
    [("s", "l", [(23.56, "restabelecer")]),
     ("b", "l", [(24.26, "função"), (24.62, "e estética")])],
    [("s", "l", [(25.48, "num"), (25.92, "tratamento")]),
     ("b", "l", [(26.26, "simples.")])],
    [("s", "l", [(26.70, "Aqui"), (27.14, "na")]),
     ("b", "l", [(27.34, "Aura,")])],
    [("n", "c", [(27.78, "a"), (27.80, "nossa"), (27.90, "preocupação")])],
    [("n", "c", [(28.52, "não"), (28.76, "é"), (28.94, "fazer")])],
    [("s", "l", [(29.18, "o maior"), (29.48, "número"), (29.72, "de")]),
     ("b", "l", [(29.90, "procedimentos,")])],
    [("n", "c", [(30.58, "mas"), (30.70, "sim"), (30.94, "o que")])],
    [("n", "c", [(31.08, "o")])],
    [("s", "l", [(31.14, "paciente"), (31.46, "realmente")]),
     ("b", "l", [(31.78, "precisa.")])],
    [("n", "c", [(37.20, "Porque")])],
    [("s", "l", [(37.26, "aqui"), (37.46, "nós")]),
     ("b", "l", [(37.58, "respeitamos")])],
    [("s", "l", [(38.14, "a"), (38.32, "sua")]),
     ("b", "l", [(38.56, "necessidade.")])],
]

MOTIONS = [{
    # "Você sai daqui sabendo o que precisa fazer, o porquê e o quanto custa."
    "kind": "checklist",
    "start": 32.40,
    "end": 37.067,
    "title": [(32.44, "Você"), (32.64, "sai"), (32.88, "daqui")],
    "big": (33.04, "sabendo"),
    "items": [
        [(33.50, "o"), (33.60, "que"), (33.68, "precisa"), (33.96, "*fazer")],
        [(34.76, "o"), (34.98, "*porquê")],
        [(35.50, "e"), (35.80, "o"), (36.14, "*quanto"), (36.42, "*custa")],
    ],
}]

CAMERA = {
    "cuts": [1.067, 9.0, 13.633, 26.933, 37.067],
    "punch_ins": [(4.18, 1.12), (6.88, 1.0), (10.48, 1.2), (15.02, 1.12), (18.34, 1.0),
                  (20.90, 1.12), (22.95, 1.0), (30.56, 1.12)],
    "drift": 0.03,
    "cut_zoom": 0.05,
    "cut_blur": 4,
    "anchor": [(0.0, (0.40, 0.25)), (1.067, (0.50, 0.18)), (9.0, (0.50, 0.15)),
               (13.633, (0.50, 0.20)), (26.933, (0.50, 0.20)), (37.067, (0.55, 0.20))],
}

OUTPUT_SIZE = (1080, 1920)
