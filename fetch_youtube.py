import feedparser
import json
from datetime import datetime, timezone
import requests
import re

CHANNELS = [
    {"name": "GremioTV Oficial",   "channel_id": "UCHKbUAiKHsWCCZrkDY_PZ8Q"},
    {"name": "Canal do CCD",       "channel_id": "UC-vcAXksTA21wp1iN4ZGv6Q"},
    {"name": "Canal Monumental",   "channel_id": "UCgeVb79_CtAIaGgZq8MHU6A"},
    {"name": "Imortal Tricolor",   "channel_id": "UCtpC1QsVVfCRjjlyMPIppXw"},
    {"name": "Zona Gremista",      "channel_id": "UC2XCTPIqVJBVK4M9-UquacQ"},
    {"name": "MDV Futebol",        "channel_id": "UCbaLsDyl0cehhUvlycX7Mxw"},
    {"name": "Portal do Gremista", "channel_id": "UCaQaFTJzJFSFjRsg5vV6C8Q"},
    {"name": "Bage TV",            "channel_id": "UCg6ONDqJLO_G2kJuxDPxTaA"},
    {"name": "Canal 7 Gremista",   "handle": "@Canal7Gremista"},
    {"name": "Radio Imortal",      "handle": "@rdimortal"},
    {"name": "Gremio Imortal",     "handle": "@gremioimortal"},
    {"name": "Planeta Gremio",     "handle": "@PlanetaGremio"},
    {"name": "Gremio Noticias",    "handle": "@GremioNoticias"},
    {"name": "Gremio HOJE",        "handle": "@GREMIOHJ"},
    {"name": "Gremio Productions", "handle": "@gremioproductions_br"},
]

RSS_BASE = "https://www.youtube.com/feeds/videos.xml?channel_id={}"
VIDEOS_PER_CHANNEL = 5
OUTPUT_FILE = "videos.json"


def resolve_handle(handle):
    try:
        r = requests.get(
            "https://www.youtube.com/" + handle,
            timeout=15,
            headers={"User-Agent":
