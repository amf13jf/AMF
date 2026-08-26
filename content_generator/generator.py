"""Núcleo de geração de conteúdo para Instagram usando a API da Claude."""

import os

from anthropic import Anthropic

MODEL = "claude-sonnet-5"


def _client() -> Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY não encontrada. Copie .env.example para .env "
            "e preencha sua chave da API da Anthropic."
        )
    return Anthropic(api_key=api_key)


def _ask(system: str, prompt: str, max_tokens: int = 1500) -> str:
    client = _client()
    response = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in response.content if block.type == "text")


CAPTION_SYSTEM = (
    "Você é um especialista em growth marketing para Instagram, focado em "
    "aumentar alcance, salvamentos e comentários em contas brasileiras. "
    "Escreva sempre em português do Brasil, com linguagem natural, sem "
    "clichês genéricos de marketing e sem emojis em excesso."
)


def generate_caption(topic: str, tone: str, niche: str | None, cta: str | None) -> str:
    prompt = (
        f"Escreva 3 opções de legenda para um post de Instagram sobre: {topic}.\n"
        f"Tom de voz: {tone}.\n"
    )
    if niche:
        prompt += f"Nicho da conta: {niche}.\n"
    if cta:
        prompt += f"Inclua esta chamada para ação: {cta}.\n"
    prompt += (
        "Cada opção deve ter: uma primeira linha forte (hook) que funcione mesmo "
        "cortada no feed, o corpo da legenda, e uma pergunta final para estimular "
        "comentários. Separe as 3 opções claramente com títulos 'Opção 1', 'Opção 2', "
        "'Opção 3'. Não inclua hashtags aqui."
    )
    return _ask(CAPTION_SYSTEM, prompt)


def generate_ideas(niche: str, count: int, content_format: str | None) -> str:
    prompt = (
        f"Gere {count} ideias de conteúdo para uma conta de Instagram no nicho "
        f"'{niche}'."
    )
    if content_format:
        prompt += f" Formato desejado: {content_format}."
    prompt += (
        " Para cada ideia, dê um título curto e uma linha explicando o ângulo/gancho "
        "que a torna compartilhável ou salvável. Numere as ideias."
    )
    return _ask(CAPTION_SYSTEM, prompt, max_tokens=2000)


def generate_calendar(niche: str, days: int, posts_per_day: int) -> str:
    prompt = (
        f"Monte um calendário de conteúdo de {days} dias para uma conta de "
        f"Instagram no nicho '{niche}', com {posts_per_day} post(s) por dia.\n"
        "Para cada dia, especifique: formato (Reel, Carrossel, Post único ou "
        "Stories), tema/título e objetivo (ex: alcance, autoridade, conversão, "
        "engajamento). Alterne os formatos e objetivos ao longo da semana para "
        "manter a estratégia equilibrada. Apresente em formato de tabela por dia."
    )
    return _ask(CAPTION_SYSTEM, prompt, max_tokens=3000)


def generate_reel_script(topic: str, duration: int) -> str:
    prompt = (
        f"Escreva um roteiro para um Reel de Instagram de aproximadamente "
        f"{duration} segundos sobre: {topic}.\n"
        "Estruture em: Gancho (primeiros 2-3 segundos, texto que aparece na tela), "
        "Desenvolvimento (fala/texto principal, dividido em cenas com tempo "
        "aproximado de cada uma) e Fechamento (call to action). Inclua sugestões "
        "de texto na tela (overlay) para cada cena."
    )
    return _ask(CAPTION_SYSTEM, prompt, max_tokens=1500)


def generate_hashtags(topic: str, count: int) -> str:
    prompt = (
        f"Gere {count} hashtags para um post de Instagram sobre: {topic}.\n"
        "Separe em 3 grupos: 'Alto alcance' (hashtags populares e amplas), "
        "'Nicho' (hashtags específicas do tema, com concorrência moderada) e "
        "'Cauda longa' (hashtags bem específicas, baixa concorrência, alta "
        "intenção). Liste as hashtags prontas para copiar e colar."
    )
    return _ask(CAPTION_SYSTEM, prompt, max_tokens=1000)
