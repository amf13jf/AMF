"""Roteiro do vídeo de odontopediatria (para os pais): clipes IMG_1704..1713.

A montagem é feita antes (ver VIDEO_EDIT / AUDIO_EDIT): a voz segue os 5 clipes
da Dra, cortados com folga; no IMG_1709 (câmera apontada para o chão) a imagem
é trocada por vídeos de apoio da Dra atendendo, e o final ("lembrança boa")
vira a equipe comemorando com a criança. Tempos abaixo = montagem final (29,6s).
"""

# (arquivo, início, fim) de cada pedaço de imagem, na ordem
VIDEO_EDIT = [
    ("IMG_1704.MOV", 0.62, 8.55),   # "Se você tem filho pequeno..."
    ("IMG_1707.MOV", 1.02, 6.70),   # "Pode ter sido assim com você..."
    ("IMG_8163.MOV", 0.40, 2.64),   # apoio: atendimento com a luz
    ("IMG_8173.MOV", 0.60, 2.55),   # apoio: carinho no rosto da criança
    ("IMG_8165.MOV", 0.80, 2.73),   # apoio: atendimento
    ("IMG_1710.MOV", 0.75, 5.42),   # "Se você pode escolher..."
    ("IMG_1713.MOV", 0.48, 3.13),   # "Clique no link e marque a avaliação..."
    ("IMG_8176.mp4", 2.20, 4.72),   # apoio: equipe comemorando com a criança
]
# (arquivo, início, fim) da voz, na ordem (o IMG_1709 só entra com o áudio)
AUDIO_EDIT = [
    ("IMG_1704.MOV", 0.62, 8.55),
    ("IMG_1707.MOV", 1.02, 6.70),
    ("IMG_1709.MOV", 0.38, 6.50),
    ("IMG_1710.MOV", 0.75, 5.42),
    ("IMG_1713.MOV", 0.48, 5.65),
]

DYN_ROLE_SIZES = {"n": 62, "s": 52, "b": 118}
DYN_CENTER_Y = 1380

# Legenda dinâmica (Outfit Bold): cada bloco é uma lista de linhas
# (papel, alinhamento, [(início, palavra), ...]). Papéis: "n" normal,
# "s" pequena, "b" grande. Alinhamento dentro do bloco: "l", "c" ou "r".
DYNAMIC_CHUNKS = [
    [("n", "c", [(0.18, "Se"), (0.26, "você"), (0.44, "tem")])],
    [("s", "l", [(0.66, "filho")]),
     ("b", "l", [(0.82, "pequeno,")])],
    [("n", "c", [(1.40, "já"), (1.50, "parou"), (1.72, "pra"), (1.78, "pensar")])],
    [("n", "c", [(2.12, "que"), (2.30, "a"), (2.36, "primeira")])],
    [("s", "l", [(2.56, "consulta"), (3.06, "dele")]),
     ("b", "l", [(3.18, "no"), (3.28, "dentista")])],
    [("n", "c", [(3.82, "pode"), (4.10, "ser"), (4.24, "um")])],
    [("s", "l", [(4.36, "momento"), (4.60, "de")]),
     ("b", "l", [(4.76, "dor")])],
    [("n", "c", [(5.48, "e"), (5.54, "que"), (5.66, "isso")])],
    [("n", "c", [(5.78, "pode"), (5.96, "causar")])],
    [("s", "l", [(6.38, "um")]),
     ("b", "l", [(6.48, "trauma")])],
    [("s", "l", [(6.72, "que"), (6.96, "dure")]),
     ("b", "l", [(7.14, "anos?")])],
    [("n", "c", [(8.14, "Pode"), (8.25, "ter"), (8.45, "sido")])],
    [("n", "c", [(8.57, "assim"), (8.81, "com"), (8.97, "você")])],
    [("n", "c", [(9.29, "e"), (9.59, "até"), (9.79, "hoje")])],
    [("s", "l", [(10.17, "você"), (10.53, "sente")]),
     ("b", "l", [(10.81, "medo")])],
    [("n", "c", [(11.11, "dessa"), (11.43, "cadeira"), (11.83, "aqui")])],
    [("s", "l", [(12.01, "por"), (12.37, "essa"), (12.53, "experiência")]),
     ("b", "l", [(12.97, "ruim.")])],
    [("s", "l", [(13.81, "Aqui"), (13.97, "na")]),
     ("b", "l", [(14.15, "Aura")])],
    [("n", "c", [(14.39, "nós"), (14.59, "temos"), (14.81, "uma"), (15.05, "dentista")])],
    [("n", "c", [(15.45, "que"), (15.59, "cuida"), (15.85, "dos"), (15.95, "pequenos")])],
    [("s", "l", [(16.33, "com")]),
     ("b", "l", [(16.51, "carinho,")])],
    [("b", "c", [(17.15, "paciência,")])],
    [("b", "c", [(17.93, "respeito")])],
    [("s", "l", [(18.49, "e"), (18.61, "ao"), (18.71, "tempo"), (18.87, "de")]),
     ("b", "l", [(19.05, "cada"), (19.21, "criança.")])],
    [("n", "c", [(19.92, "Se"), (20.00, "você"), (20.24, "pode")])],
    [("b", "c", [(20.52, "escolher,")])],
    [("n", "c", [(21.16, "por"), (21.26, "que"), (21.42, "deixar")])],
    [("n", "c", [(21.70, "o"), (21.86, "seu"), (21.94, "filho")])],
    [("s", "l", [(22.20, "conhecer")]),
     ("b", "l", [(22.48, "o"), (22.56, "dentista")])],
    [("s", "l", [(23.12, "só"), (23.36, "no"), (23.46, "momento"), (23.76, "de")]),
     ("b", "l", [(23.90, "dor?")])],
    [("n", "c", [(24.60, "Clique"), (24.78, "no"), (24.90, "link")])],
    [("s", "l", [(25.14, "e"), (25.40, "marque"), (25.62, "a")]),
     ("b", "l", [(25.76, "avaliação")])],
    [("n", "c", [(26.20, "do"), (26.30, "seu"), (26.40, "filho.")])],
    [("n", "c", [(27.14, "Vamos"), (27.28, "fazer")])],
    [("n", "c", [(27.56, "dessa"), (27.72, "experiência")])],
    [("s", "l", [(28.28, "uma")]),
     ("b", "l", [(28.54, "lembrança"), (28.94, "boa.")])],
]

# Câmera: entrada leve em todo corte (inclusive nos vídeos de apoio), zoom lento
# e enquadramentos mais fechados/abertos nas trocas de frase.
CAMERA = {
    "cuts": [7.93, 13.61, 15.85, 17.80, 19.73, 24.40, 27.05],
    "punch_ins": [(3.82, 1.12), (5.48, 1.0), (10.17, 1.12), (21.16, 1.18), (25.14, 1.15)],
    "drift": 0.03,
    "cut_zoom": 0.05,
    "cut_blur": 4,
    "anchor": [(0.0, (0.50, 0.20)), (7.93, (0.50, 0.20)), (13.61, (0.50, 0.40)),
               (19.73, (0.50, 0.22)), (24.40, (0.50, 0.25)), (27.05, (0.50, 0.40))],
}

OUTPUT_SIZE = (1080, 1920)
