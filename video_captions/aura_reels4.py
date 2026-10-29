"""Roteiro com tempos (segundos) do vídeo "Aura - Reels 4 Ads".

Transcrito com Whisper (palavra a palavra) e revisado à mão.
"""

# Corte de cena: até aqui as duas pessoas conversam juntas (legenda normal);
# a partir daqui a Dra aparece de jaleco (legenda dinâmica).
SCENE_CUT = 17.033

# Legenda normal da cena com as duas pessoas: (início, fim, texto)
STATIC_SUBS = [
    (0.00, 1.92, "Menina, você acredita que eu escovei meus dentes"),
    (1.92, 4.48, "e quando cuspi na pia saiu sangue?"),
    (4.54, 5.80, "Ah, não deve ser nada demais!"),
    (5.98, 8.10, "E pior, tomei um copo de água gelada,"),
    (8.14, 9.70, "senti uma dor aqui atrás."),
    (10.18, 11.70, "Que bobagem, logo passa."),
    (12.10, 13.12, "Será que é cárie?"),
    (13.20, 14.40, "Só acha quem procura."),
    (14.58, 15.90, "Se não dói, então tá tudo bem."),
    (16.24, SCENE_CUT, "Será?"),
]

# Legenda dinâmica: cada bloco é uma lista de (início, fim, palavra).
# Palavra com "*" na frente vira destaque em Bodoni itálico com fundo vinho.
DYNAMIC_CHUNKS = [
    [(17.08, 17.26, "Você"), (17.26, 17.56, "também")],
    [(17.56, 17.82, "pensa"), (17.82, 18.20, "*assim?")],
    [(18.38, 18.90, "*Cuidado,")],
    [(19.04, 19.22, "esses"), (19.22, 19.54, "sinais")],
    [(19.54, 19.68, "não"), (19.68, 19.94, "podem"), (19.94, 20.12, "ser")],
    [(20.12, 20.70, "*ignorados.")],
    # 20,8s - 25,1s: motion (ver MOTION abaixo)
    [(25.16, 25.26, "E"), (25.26, 25.38, "uma"), (25.38, 25.94, "*avaliação")],
    [(25.94, 26.20, "pode"), (26.20, 26.82, "identificar")],
    [(26.82, 27.12, "o"), (27.12, 27.20, "que"), (27.20, 27.38, "está"),
     (27.38, 27.84, "acontecendo")],
    [(27.84, 28.26, "antes"), (28.26, 28.40, "que"), (28.40, 28.48, "o"),
     (28.48, 28.66, "problema")],
    [(28.66, 28.84, "se"), (28.84, 29.14, "*agrave.")],
    [(29.14, 29.48, "Não"), (29.48, 29.94, "espere")],
    [(29.94, 30.10, "um"), (30.10, 30.54, "pequeno"), (30.54, 31.00, "*incômodo")],
    [(31.00, 31.26, "virar"), (31.26, 31.36, "um"), (31.36, 31.98, "*problemão.")],
    [(32.32, 32.82, "Clique"), (32.82, 32.90, "no"), (32.90, 33.08, "*link")],
    [(33.08, 33.24, "e"), (33.24, 33.60, "agende")],
    [(33.60, 33.72, "sua"), (33.72, 34.18, "*consulta.")],
    [(34.26, 34.46, "Quanto"), (34.46, 34.74, "antes")],
    [(34.74, 34.98, "você"), (34.98, 35.56, "*cuidar,")],
    [(35.60, 35.88, "menos"), (35.88, 36.22, "você")],
    [(36.22, 37.03, "*gasta.")],
]

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
