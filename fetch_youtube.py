import feedparser
import json
import os
from datetime import datetime, timezone
import requests
import re

# =============================================================================
# CANAIS GREMISTAS — 15 canais
# MDV Futebol: channel ID obtido via scraping (sem ID direto na documentação)
# =============================================================================
CHANNELS = [
    {"name": "GrêmioTV",           "channel_id": "UCdC9uw08aLQHSETVxDzpDEQ"},
    {"name": "Canal do Grêmio",    "channel_id": "UC5_UIQR5m4-t7l8w5TxzwXA"},
    {"name": "Grêmio Rádio",       "channel_id": "UCNifW-6HoGkB7z9FJVtGhAA"},
    {"name": "Gremista.com.br",    "channel_id": "UC7ZbXzxBPPMIaJkV0eFIoVg"},
    {"name": "Tricolor Gaúcho",    "channel_id": "UC9MRPlUAj6bJjNRbkmRqjFQ"},
    {"name": "Arena Grêmio",       "channel_id": "UCXRlIK3Cw_OJBxq1R6wK3Kw"},
    {"name": "Planeta Grêmio",     "channel_id": "UCQaE1IdbwTzxvyU92YSQQSA"},
    {"name": "Grêmio Esporte",     "channel_id": "UC2b8H5Bl9EIaJpxJYlV7M7w"},
    {"name": "GaúchoTV",           "channel_id": "UCf4aNWjLyYn1F75m3Wk1uDQ"},
    {"name": "Imortal Tricolor",   "channel_id": "UCkJr8t7tFb81H9UYWH7W6Kw"},
    {"name": "Arquibancada Gremista", "channel_id": "UCbJm7NMrwxr3VDR62LFqndA"},
    {"name": "Grêmio Notícias",    "channel_id": "UCvzE4TLpU8kPJbq3Ru7n3nQ"},
    {"name": "Trivela Gaúcha",     "channel_id": "UCHoS2D5QNJH2sT5HHVZ6LDw"},
    {"name": "SouTricolor",        "channel_id": "UCpMy8X7n6GEaJlRZo3kD2Yw"},
    # MDV Futebol — channel_id resolvido via scraping abaixo
    {"name": "MDV Futebol",        "channel_id": None, "handle": "@MDVFutebol"},
]

RSS_BASE = "https://www.youtube.com/feeds/videos.xml?channel_id={}"
VIDEOS_PER_CHANNEL = 5
OUTPUT_FILE = "videos.json"


def resolve_channel_id_from_handle(handle: str) -> str | None:
    """
    Dado um handle YouTube (@MDVFutebol), busca o channel_id real
    fazendo GET na página e extraindo o externalId do HTML/meta.
    """
    url = f"https://www.youtube.com/{handle}"
    try:
        resp = requests.get(
            url,
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0 (compatible; bot/1.0)"},
        )
        resp.encoding = "utf-8"
        html = resp.text

        # Padrão 1: "externalId":"UCxxxxxxxx"
        m = re.search(r'"externalId"\s*:\s*"(UC[a-zA-Z0-9_-]{22})"', html)
        if m:
            return m.group(1)

        # Padrão 2: channel_id em og:url ou canonical
        m = re.search(r'youtube\.com/channel/(UC[a-zA-Z0-9_-]{22})', html)
        if m:
            return m.group(1)

    except Exception as e:
        print(f"[WARN] Falha ao resolver handle {handle}: {e}")

    return None


def safe_text(value: str) -> str:
    """
    Garante que a string está decodificada corretamente como UTF-8.
    feedparser já retorna str unicode — mas em caso de mojibake duplo,
    tenta re-encode latin-1 → decode utf-8.
    """
    if not isinstance(value, str):
        return str(value)
    try:
        # Se veio corrompido (ex: "GrÃªmio"), conserta
        fixed = value.encode("latin-1").decode("utf-8")
        return fixed
    except (UnicodeEncodeError, UnicodeDecodeError):
        # Já estava correto
        return value


def fetch_channel_videos(channel: dict) -> list:
    channel_id = channel.get("channel_id")
    name = channel["name"]

    # Resolve handle se necessário
    if not channel_id:
        handle = channel.get("handle")
        if handle:
            print(f"[INFO] Resolvendo channel_id para {name} ({handle})…")
            channel_id = resolve_channel_id_from_handle(handle)
            if channel_id:
                print(f"[OK]   {name} → {channel_id}")
                channel["channel_id"] = channel_id  # cache para próximas execuções
            else:
                print(f"[ERRO] Não foi possível resolver channel_id para {name}")
                return []
        else:
            print(f"[ERRO] Canal '{name}' sem channel_id e sem handle. Pulando.")
            return []

    url = RSS_BASE.format(channel_id)
    try:
        # Força encoding correto no download do feed
        resp = requests.get(url, timeout=15)
        resp.encoding = "utf-8"
        feed = feedparser.parse(resp.text)
    except Exception as e:
        print(f"[ERRO] Falha ao buscar feed de {name}: {e}")
        return []

    videos = []
    for entry in feed.entries[:VIDEOS_PER_CHANNEL]:
        title = safe_text(entry.get("title", ""))
        video_id = entry.get("yt_videoid", "")
        published = entry.get("published", "")
        thumbnail = f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"
        url_video = f"https://www.youtube.com/watch?v={video_id}"

        videos.append({
            "channel": safe_text(name),
            "title": title,
            "videoId": video_id,
            "url": url_video,
            "thumbnail": thumbnail,
            "published": published,
        })

    print(f"[OK]   {name}: {len(videos)} vídeo(s)")
    return videos


def main():
    all_videos = []

    for channel in CHANNELS:
        videos = fetch_channel_videos(channel)
        all_videos.extend(videos)

    # Ordena por data de publicação (mais recente primeiro)
    def parse_date(v):
        try:
            return datetime.fromisoformat(
                v["published"].replace("Z", "+00:00")
            )
        except Exception:
            return datetime.min.replace(tzinfo=timezone.utc)

    all_videos.sort(key=parse_date, reverse=True)

    output = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "total": len(all_videos),
        "videos": all_videos,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✅ {len(all_videos)} vídeos salvos em {OUTPUT_FILE}")

    # Imprime o channel_id resolvido do MDV para você poder fixar no código
    for ch in CHANNELS:
        if ch["name"] == "MDV Futebol" and ch.get("channel_id"):
            print(f"\n📌 MDV Futebol channel_id resolvido: {ch['channel_id']}")
            print("   Cole esse valor em CHANNELS para evitar scraping a cada execução.")


if __name__ == "__main__":
    main()
