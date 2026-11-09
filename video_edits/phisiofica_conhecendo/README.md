# Phisiofica – "Conhecendo" (edição)

Scripts usados na edição do vídeo de apresentação (o vídeo bruto e o final não ficam no repositório).

- `transcribe.py` – transcrição com faster-whisper (modelo small) → `transcript.json`
- `build.py` – correções do texto, legendas em uma linha (Montserrat ExtraBold, sombra preta 65%) → `subs.ass`, e as curvas de zoom in/out suaves → `persp.txt`
- `music.py` – trilha original sintetizada (leve, 92 BPM) → `music.wav`
- `graph.txt` – filtro do ffmpeg (zoom + legendas + mixagem com ducking da trilha sob a voz)

```bash
python3 transcribe.py model/small audio16k.wav transcript.json
python3 build.py && python3 music.py 106 music.wav
ffmpeg -i bruto.mp4 -i music.wav -filter_complex_script graph.txt -map "[v]" -map "[a]" -c:v libx264 -crf 19 -c:a aac -b:a 192k final.mp4
```
