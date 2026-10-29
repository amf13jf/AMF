"""Roteiro com tempos (segundos) do vídeo "Aura - Reels 4 Ads".

Transcrito com Whisper (palavra a palavra) e revisado à mão.
"""

# Corte de cena: até aqui as duas pessoas conversam juntas (legenda normal);
# a partir daqui a Dra aparece de jaleco (legenda dinâmica).
SCENE_CUT = 17.033

# Legenda normal da cena com as duas pessoas: (início, fim, texto)
STATIC_SUBS = [
    (0.00, 0.94, "Menina, você acredita"),
    (0.94, 1.92, "que eu escovei meus dentes"),
    (1.92, 2.98, "e quando cuspi na pia"),
    (2.98, 4.48, "saiu sangue?"),
    (4.54, 5.80, "Ah, não deve ser nada demais!"),
    (5.98, 7.54, "E pior, tomei um copo"),
    (7.54, 8.10, "de água gelada,"),
    (8.14, 9.70, "senti uma dor aqui atrás."),
    (10.18, 11.70, "Que bobagem, logo passa."),
    (12.10, 13.12, "Será que é cárie?"),
    (13.20, 14.40, "Só acha quem procura."),
    (14.58, 15.90, "Se não dói, então tá tudo bem."),
    (16.24, SCENE_CUT, "Será?"),
]

# Legenda dinâmica (Outfit Bold): cada bloco é uma lista de linhas
# (papel, alinhamento, [(início, palavra), ...]). Papéis: "n" normal,
# "s" pequena, "b" grande.
# Alinhamento dentro do bloco: "l", "c" ou "r".
DYNAMIC_CHUNKS = [
    [("n", "c", [(17.08, "Você"), (17.26, "também")])],
    [("n", "c", [(17.56, "pensa"), (17.82, "assim?")])],
    [("b", "c", [(18.38, "Cuidado,")])],
    [("n", "c", [(19.04, "esses"), (19.22, "sinais")])],
    [("s", "l", [(19.54, "não"), (19.68, "podem"), (19.94, "ser")]),
     ("b", "l", [(20.12, "ignorados.")])],
    # 20,75s - 25,15s: motion (ver MOTION abaixo)
    [("s", "l", [(25.16, "E"), (25.26, "uma")]),
     ("b", "l", [(25.38, "avaliação")])],
    [("n", "c", [(25.94, "pode"), (26.20, "identificar")])],
    [("n", "c", [(26.82, "o"), (27.12, "que"), (27.20, "está")])],
    [("n", "c", [(27.38, "acontecendo")])],
    [("n", "c", [(27.84, "antes"), (28.26, "que"), (28.40, "o")])],
    [("n", "c", [(28.48, "problema")])],
    [("s", "l", [(28.66, "se")]),
     ("b", "l", [(28.84, "agrave.")])],
    [("n", "c", [(29.14, "Não"), (29.48, "espere")])],
    [("s", "l", [(29.94, "um"), (30.10, "pequeno")]),
     ("b", "l", [(30.54, "incômodo")])],
    [("s", "l", [(31.00, "virar"), (31.26, "um")]),
     ("b", "l", [(31.36, "problemão.")])],
    # 32,15s - 34,20s: "Clique no link e agende sua consulta." (removido, ver CUTS)
    [("n", "c", [(34.26, "Quanto"), (34.46, "antes")])],
    [("n", "c", [(34.74, "você"), (34.98, "cuidar,")])],
    [("s", "l", [(35.60, "menos"), (35.88, "você")]),
     ("b", "l", [(36.22, "gasta.")])],
]

# Trechos removidos do vídeo final: (início, fim)
CUTS = [(32.15, 34.20)]

# Motion "Uma cárie pode começar sem dor ... até o sangramento de gengiva
# não deve ser ignorado."
MOTION = {
    "start": 20.75,
    "end": 25.15,
    "switch": 22.50,  # troca do sinal 01 (cárie) para o sinal 02 (gengiva)
    "phase1": {
        "label": "SINAL 01",
        "line": [(20.86, "Uma"), (21.02, "*cárie"), (21.32, "pode"), (21.46, "começar")],
        "big": (21.74, "sem dor."),
    },
    "phase2": {
        "label": "SINAL 02",
        "line": [(22.66, "Até"), (22.82, "o"), (22.88, "sangramento"), (23.18, "de"),
                 (23.52, "*gengiva")],
        "line2": [(23.90, "não"), (24.12, "deve"), (24.26, "ser")],
        "big": (24.44, "ignorado."),
    },
}
