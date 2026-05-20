import feedparser
import json
from datetime import datetime, timezone
import requests
import re

# =============================================================================
# CANAIS GREMISTAS — 15 canais
# Usando channel_id direto onde disponivel, handle @ onde necessario
# =============================================================================
CHANNELS = [
    # Channel IDs diretos (mais confiavel)
    {"name": "GremioTV Oficial",        "channel_id": "UCHKbUAiKHsWCCZrkDY_PZ8Q"},
    {"name": "Canal do CCD",            "channel_id": "UC-vcAXksTA21wp1iN4ZGv6Q"},
    {"name": "Canal Monumental",        "channel_id": "UCgeVb79_CtAIaGgZq8MHU6A"},
    {"name": "Imortal Tricolor",        "channel_id": "UCtpC1QsVVfCRjjlyMPIppXw"},
    {"name": "Zona Gremista",           "channel_id": "UC2XCTPIqVJBVK4M9-UquacQ"},
    {"name": "MDV Futebol",             "channel_id": "UCbaLsDyl0cehhUvlycX7Mxw"},
    # Handles @ (resolvidos automaticamente)
    {"name": "Canal 7 Gremista",        "handle": "@Canal7Gremista"},
    {"name": "Portal do Gremista",      "handle": "@PortaldoGremista"},
    {"name": "Radio Imortal",           "handle": "@rdimortal"},
    {"name": "Gremio Imortal",          "handle": "@gremioimortal"},
    {"name": "Planeta Gremio",          "handle": "@PlanetaGremio"},
    {"name": "Trivela Gaucha",          "handle": "@TrivelaGaucha"},
    {"name": "Arquibancada Gremista",   "handle": "@ArquibancadaGremista"},
    {"name": "SouTricolor",             "handle": "@SouTricolor"},
    {"name": "Gremio Noticias",         "handle": "@GremioNoticias"},
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
        video_id = entry.get("yt_videoid", "")
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
