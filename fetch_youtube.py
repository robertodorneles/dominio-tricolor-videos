import feedparser
import json
from datetime import datetime, timezone
import requests
import re

CHANNELS = [
    {"name": "GremioTV Oficial",      "channel_id": "UCHKbUAiKHsWCCZrkDY_PZ8Q"},
    {"name": "Canal do CCD",          "channel_id": "UC-vcAXksTA21wp1iN4ZGv6Q"},
    {"name": "Canal Monumental",      "channel_id": "UCgeVb79_CtAIaGgZq8MHU6A"},
    {"name": "Imortal Tricolor",      "channel_id": "UCtpC1QsVVfCRjjlyMPIppXw"},
    {"name": "Zona Gremista",         "channel_id": "UC2XCTPIqVJBVK4M9-UquacQ"},
    {"name": "MDV Futebol",           "channel_id": "UCbaLsDyl0cehhUvlycX7Mxw"},
    {"name": "Portal do Gremista",    "channel_id": "UCaQaFTJzJFSFjRsg5vV6C8Q"},
    {"name": "Bage TV",               "channel_id": "UCg6ONDqJLO_G2kJuxDPxTaA"},
    {"name": "Canal 7 Gremista",      "handle": "@Canal7Gremista"},
    {"name": "Radio Imortal",         "handle": "@rdimortal"},
    {"name": "Gremio Imortal",        "handle": "@gremioimortal"},
    {"name": "Planeta Gremio",        "handle": "@PlanetaGremio"},
    {"name": "Gremio Noticias",       "handle": "@GremioNoticias"},
    {"name": "Gremio HOJE",           "handle": "@GREMIOHJ"},
    {"name": "Gremio Productions",    "handle": "@gremioproductions_br"},
]

RSS_BASE           = "https://www.youtube.com/feeds/videos.xml?channel_id={}"
VIDEOS_PER_CHANNEL = 5
OUTPUT_FILE        = "videos.json"


def resolve_channel_id_from_handle(handle):
    url = f"https://www.youtube.com/{handle}"
    try:
        resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        resp.encoding = "utf-8"
        html = resp.text
        m = re.search(r'"externalId"\s*:\s*"(UC[a-zA-Z0-9_-]{22})"', html)
        if m:
            return m.group(1)
        m = re.search(r'youtube\.com/channel/(UC[a-zA-Z0-9_-]{22})', html)
        if m:
            return m.group(1)
    except Exception as e:
        print(f"[WARN] {handle}: {e}")
    return None


def safe_text(value):
    if not isinstance(value, str):
        return str(value)
    try:
        return value.encode("latin-1").decode("utf-8")
    except:
        r
