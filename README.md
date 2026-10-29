# Gerador de Conteúdo para Instagram

Ferramenta de linha de comando que usa a API da Claude (Anthropic) para gerar
legendas, ideias de posts, calendário de conteúdo, roteiros de Reels e
hashtags — pensada para ajudar no crescimento orgânico de uma conta de
Instagram.

## Instalação

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edite o `.env` e coloque sua chave da API da Anthropic (`ANTHROPIC_API_KEY`).
Você pode gerar uma chave em https://console.anthropic.com/.

## Uso

```bash
# Legendas
python -m content_generator.main caption --topic "rotina matinal produtiva" --tone "inspirador"

# Ideias de conteúdo
python -m content_generator.main ideas --niche "moda sustentável" --count 10

# Calendário de conteúdo (7 dias)
python -m content_generator.main calendar --niche "culinária fit" --days 7

# Roteiro de Reel
python -m content_generator.main reel-script --topic "receita de bolo em 3 passos" --duration 30

# Hashtags
python -m content_generator.main hashtags --topic "viagem mochilão" --count 15
```

Adicione `--output caminho/arquivo.txt` em qualquer comando para salvar o
resultado em um arquivo, além de exibi-lo no terminal.

## Próximo passo: automação real com a API do Instagram

Esta ferramenta gera o *conteúdo*. Para publicar, agendar ou coletar métricas
automaticamente direto no Instagram, você precisa da **Instagram Graph API**
(oficial, da Meta). Resumo do caminho:

1. Transforme seu perfil em conta **Business** ou **Creator** (Configurações
   do Instagram → Conta → Mudar para conta profissional).
2. Vincule essa conta a uma **Página do Facebook** (a Graph API do Instagram
   funciona através de uma Página).
3. Crie um app em https://developers.facebook.com/ (Meta for Developers).
4. No app, adicione o produto **Instagram Graph API** e configure as
   permissões necessárias (`instagram_basic`, `instagram_content_publish`,
   `pages_show_list`, etc.).
5. Gere um token de acesso de longa duração para a Página vinculada.
6. Com o token, é possível publicar posts/Reels agendados, ler métricas de
   posts (alcance, impressões, engajamento) e ler comentários via API.

Isso não é algo que se faz por script — precisa ser feito manualmente no
painel da Meta, pois envolve login, permissões e (para publicar em nome de
terceiros) revisão do app pela Meta. Depois de ter o token, dá para eu
integrar essa parte diretamente aqui na ferramenta (publicação agendada,
puxar métricas para orientar o calendário de conteúdo, etc.).

## Legendas de vídeo (Reels)

`video_captions/` queima no vídeo a legenda normal, a legenda dinâmica e o
motion vinho (requer `ffmpeg` e `Pillow`):

```bash
python -m video_captions.render entrada.mp4 saida.mp4
```

No macOS ele usa Helvetica Neue e Bodoni 72 automaticamente; fora dele cai
para Inter e Bodoni Moda. O roteiro com os tempos fica em
`video_captions/aura_reels4.py`.
