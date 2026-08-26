"""CLI do gerador de conteúdo para Instagram.

Exemplos:
    python -m content_generator.main caption --topic "rotina matinal produtiva" --tone "inspirador"
    python -m content_generator.main ideas --niche "moda sustentável" --count 10
    python -m content_generator.main calendar --niche "culinária fit" --days 7
    python -m content_generator.main reel-script --topic "receita de bolo em 3 passos"
    python -m content_generator.main hashtags --topic "viagem mochilão" --count 15
"""

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

from content_generator import generator


def _save_if_requested(text: str, output: str | None) -> None:
    print(text)
    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        print(f"\n[Salvo em {path}]")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Gerador de conteúdo para Instagram")
    parser.add_argument("--output", "-o", help="Arquivo para salvar o resultado")
    sub = parser.add_subparsers(dest="command", required=True)

    p_caption = sub.add_parser("caption", help="Gera opções de legenda")
    p_caption.add_argument("--topic", required=True, help="Assunto do post")
    p_caption.add_argument("--tone", default="envolvente e autêntico", help="Tom de voz")
    p_caption.add_argument("--niche", help="Nicho da conta")
    p_caption.add_argument("--cta", help="Chamada para ação desejada")

    p_ideas = sub.add_parser("ideas", help="Gera ideias de conteúdo")
    p_ideas.add_argument("--niche", required=True, help="Nicho da conta")
    p_ideas.add_argument("--count", type=int, default=10, help="Quantidade de ideias")
    p_ideas.add_argument("--format", dest="content_format", help="Reel, Carrossel, etc.")

    p_calendar = sub.add_parser("calendar", help="Gera calendário de conteúdo")
    p_calendar.add_argument("--niche", required=True, help="Nicho da conta")
    p_calendar.add_argument("--days", type=int, default=7, help="Número de dias")
    p_calendar.add_argument("--posts-per-day", type=int, default=1, help="Posts por dia")

    p_reel = sub.add_parser("reel-script", help="Gera roteiro de Reel")
    p_reel.add_argument("--topic", required=True, help="Assunto do Reel")
    p_reel.add_argument("--duration", type=int, default=30, help="Duração em segundos")

    p_hashtags = sub.add_parser("hashtags", help="Gera hashtags")
    p_hashtags.add_argument("--topic", required=True, help="Assunto do post")
    p_hashtags.add_argument("--count", type=int, default=20, help="Quantidade de hashtags")

    return parser


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "caption":
            result = generator.generate_caption(args.topic, args.tone, args.niche, args.cta)
        elif args.command == "ideas":
            result = generator.generate_ideas(args.niche, args.count, args.content_format)
        elif args.command == "calendar":
            result = generator.generate_calendar(args.niche, args.days, args.posts_per_day)
        elif args.command == "reel-script":
            result = generator.generate_reel_script(args.topic, args.duration)
        elif args.command == "hashtags":
            result = generator.generate_hashtags(args.topic, args.count)
        else:
            parser.error(f"Comando desconhecido: {args.command}")
            return 2
    except RuntimeError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1

    _save_if_requested(result, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
