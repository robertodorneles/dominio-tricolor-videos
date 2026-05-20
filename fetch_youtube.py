import feedparser
import json
from datetime import datetime, timezone
import requests
import re

# =============================================================================
# CANAIS GREMISTAS — 15 canais com handles @
# O script resolve o channel_id automaticamente via scraping do handle
# MDV Futebol já tem channel_id fixo (resolvido na primeira execução)
# =============================================================================
CHANNELS = [
    {"name": "GrêmioTV (Oficial)",      "handle": "@gremiotv"},
    {"name": "Canal do CCD",            "handle": "@CanalCCD"},
    {"name": "Canal 7 Gremista",        "handle": "@Canal7Gremista"},
    {"name": "Canal Monumental",        "handle": "@canalmonumentalRS"},
    {"name": "Imortal Tricolor",        "handle": "@imortaltricolarnews"},
    {"name": "Portal do Gremista",      "handle": "@PortaldoGremista"},
    {"name": "Zona Gremista",           "handle": "@ZonaGremista"},
    {"name": "Rádio Imortal",           "handle": "@rdimortal"},
    {"name": "Grêmio Imortal",          "handle": "@gremioimortal"},
    {"name": "MDV Futebol",             "channel_id": "UCbaLsDyl0cehhUvlycX7Mxw"},
    {"name": "Planeta Grêmio",          "handle": "@PlanetaGremio"},
    {"name": "Trivela Gaúcha",          "handle": "@TrivelaGaucha"},
    {"name": "Arquibancada Gremista",   "handle": "@ArquibancadaGremista"},
    {"name": "SouTricolor",             "handle": "@SouTricolor"},
    {"name": "Grêmio Notícias",         "handle": "@GremioNoticias"},
]

RSS_BASE           = "https://www.youtube.com/feeds/videos.xml?channel_id={}"
VIDEOS_PER_CHANNEL = 5
OUTPUT_FILE        = "videos.json"


def resolve_channel_id_from_handle(handle: str) -> str | None:
    url = f"https://www.youtube.com/{handle}"
    try:
        resp = requests.get(url, timeout=15,
                            headers={"User-Agent": "Mozilla/5.0 (compatible; bot/1.0)"})
        resp.encoding = "utf-8"
        html = resp.text
        m = re.search(r'\"externalId\"\s*:\s*\"(UC[a-zA-Z0-9_-]{22})\"', html)
        if m:
            return m.group(1)
        m = re.search(r'youtube\.com/channel/(UC[a-zA-Z0-9_-]{22})', html)
        if m:
            return m.group(1)
    except Exception as e:
        print(f"[WARN] Falha ao resolver handle {handle}: {e}")
    return None


def safe_text(value: str) -> str:
    if not isinstance(value, str):
        return str(value)
    try:
        return value.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value


def fetch_channel_videos(channel: dict) -> list:
    channel_id = channel.get("channel_id")
    name = channel["name"]

    if not channel_id:
        handle = channel.get("handle")
        if handle:
            print(f"[INFO] Resolvendo {name} ({handle})...")
            channel_id = resolve_channel_id_from_handle(handle)
            if channel_id:
                channel["channel_id"] = channel_id
                print(f"[OK]   {name} -> {channel_id}")
            else:
                print(f"[ERRO] Nao resolveu channel_id para {name}")
                return []
        else:
            print(f"[ERRO] Canal {name} sem handle nem channel_id")
            return []

    url = RSS_BASE.format(channel_id)
    try:
        resp = requests.get(url, timeout=15)
        resp.encoding = "utf-8"
        feed = feedparser.parse(resp.text)
    except Exception as e:
        print(f"[ERRO] Feed {name}: {e}")
        return []

    videos = []
    for entry in feed.entries[:VIDEOS_PER_CHANNEL]:
        video_id  = entry.get("yt_videoid", "")
        videos.append({
            "channel":   safe_text(name),
            "title":     safe_text(entry.get("title", "")),
            "videoId":   video_id,
            "url":       f"https://www.youtube.com/watch?v={video_id}",
            "thumbnail": f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg",
            "published": entry.get("published", ""),
        })

    print(f"[OK]   {name}: {len(videos)} video(s)")
    return videos


def main():
    all_videos = []
    for channel in CHANNELS:
        all_videos.extend(fetch_channel_videos(channel))

    def parse_date(v):
        try:
            return datetime.fromisoformat(v["published"].replace("Z", "+00:00"))
        except Exception:
            return datetime.min.replace(tzinfo=timezone.utc)

    all_videos.sort(key=parse_date, reverse=True)

    output = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "total":      len(all_videos),
        "videos":     all_videos,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✅ {len(all_videos)} videos salvos em {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
