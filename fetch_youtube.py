import json
from datetime import datetime, timezone
import requests

API_KEY = "AIzaSyBUDE6b3twtX6-fJzcqYXq4oKr4kSR0ht0"

CHANNELS = [
    {"name": "A Dupla",               "handle": "@ADuplaYT"},
    {"name": "Bage TV",               "handle": "@BageTvOficial"},
    {"name": "Bruno Soares Reporter", "handle": "@BrunoSoaresReporter"},
    {"name": "Canal do CCD",          "handle": "@cesarcidadedias"},
    {"name": "Canal do Farid",        "handle": "@CanaldoFarid"},
    {"name": "Canal do Gabardo",      "handle": "@CanaldoGabardo"},
    {"name": "Careca de Saber TV",    "handle": "@carecadesabertv"},
    {"name": "Diogo Rossi Reporter",  "handle": "@DiogoRossiReporter"},
    {"name": "Duda Garbi",            "handle": "@dudagarbi"},
    {"name": "GremioTV Oficial",      "handle": "@Gremio"},
    {"name": "GZH Digital",           "handle": "@gzhdigital"},
    {"name": "Jeremias Wernek",       "handle": "@JeremiasWernek"},
    {"name": "LH Benfica",            "handle": "@lhbenfica"},
    {"name": "MDV Futebol",           "channel_id": "UCbaLsDyl0cehhUvlycX7Mxw"},
    {"name": "Radio Grenal",          "handle": "@RadioGrenal"},
    {"name": "Radio Imortal",         "handle": "@rdimortal"},
]

VIDEOS_TARGET = 2
OUTPUT_FILE   = "videos.json"
SESSION       = requests.Session()


def get_channel_id(handle):
    """Resolve handle para channel_id via YouTube API."""
    username = handle.lstrip("@")
    url = "https://www.googleapis.com/youtube/v3/channels"
    params = {"part": "id", "forHandle": handle, "key": API_KEY}
    try:
        r = SESSION.get(url, params=params, timeout=15)
        data = r.json()
        items = data.get("items", [])
        if items:
            return items[0]["id"]
    except Exception as e:
        print("[WARN] handle", handle, str(e))
    return None


def get_uploads_playlist(channel_id):
    """Pega o ID da playlist de uploads do canal."""
    url = "https://www.googleapis.com/youtube/v3/channels"
    params = {"part": "contentDetails", "id": channel_id, "key": API_KEY}
    try:
        r = SESSION.get(url, params=params, timeout=15)
        data = r.json()
        items = data.get("items", [])
        if items:
            return items[0]["contentDetails"]["relatedPlaylists"]["uploads"]
    except Exception as e:
        print("[WARN] uploads playlist", channel_id, str(e))
    return None


def get_videos(playlist_id, name):
    """Busca ultimos videos da playlist de uploads, filtrando Shorts."""
    url = "https://www.googleapis.com/youtube/v3/playlistItems"
    params = {
        "part": "snippet,contentDetails",
        "playlistId": playlist_id,
        "maxResults": 10,
        "key": API_KEY,
    }
    try:
        r = SESSION.get(url, params=params, timeout=15)
        data = r.json()
        items = data.get("items", [])
    except Exception as e:
        print("[ERRO]", name, str(e))
        return []

    if not items:
        return []

    # Pega IDs dos videos para verificar duracao
    video_ids = [i["contentDetails"]["videoId"] for i in items]

    # Busca duracoes
    dur_url = "https://www.googleapis.com/youtube/v3/videos"
    dur_params = {
        "part": "contentDetails",
        "id": ",".join(video_ids),
        "key": API_KEY,
    }
    durations = {}
    try:
        dr = SESSION.get(dur_url, params=dur_params, timeout=15)
        for v in dr.json().get("items", []):
            import re
            dur = v["contentDetails"]["duration"]  # ex: PT1M30S
            m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", dur)
            if m:
                h = int(m.group(1) or 0)
                mn = int(m.group(2) or 0)
                s = int(m.group(3) or 0)
                durations[v["id"]] = h * 3600 + mn * 60 + s
    except Exception as e:
        print("[WARN] durations", str(e))

    videos = []
    for item in items:
        vid = item["contentDetails"]["videoId"]
        secs = durations.get(vid, 999)
        # Filtra Shorts (<=60s)
        if secs > 0 and secs <= 60:
            print("[SHORT]", vid, "ignorado")
            continue
        snippet = item["snippet"]
        title = snippet.get("title", "")
        published = snippet.get("publishedAt", "")
        thumbnail = (
            snippet.get("thumbnails", {})
            .get("medium", {})
            .get("url", f"https://img.youtube.com/vi/{vid}/mqdefault.jpg")
        )
        videos.append({
            "channel":   name,
            "title":     title,
            "videoId":   vid,
            "url":       "https://www.youtube.com/watch?v=" + vid,
            "thumbnail": thumbnail,
            "published": published,
        })
        if len(videos) >= VIDEOS_TARGET:
            break

    print(f"[OK]   {name}: {len(videos)} video(s)")
    return videos


def fetch(ch):
    name = ch["name"]
    cid = ch.get("channel_id")

    if not cid:
        handle = ch.get("handle", "")
        print(f"[INFO] Resolvendo {name} {handle}")
        cid = get_channel_id(handle)
        if cid:
            ch["channel_id"] = cid
            print(f"[OK]   {name} -> {cid}")
        else:
            print(f"[SKIP] {name}")
            return []

    playlist_id = get_uploads_playlist(cid)
    if not playlist_id:
        print(f"[ERRO] Playlist nao encontrada para {name}")
        return []

    return get_videos(playlist_id, name)


def main():
    all_videos = []
    for ch in CHANNELS:
        all_videos.extend(fetch(ch))

    # Ordena por canal alfabetico e data mais recente
    all_videos.sort(key=lambda v: (
        v["channel"].lower(),
        -(datetime.fromisoformat(v["published"].replace("Z", "+00:00")).timestamp() if v["published"] else 0)
    ))

    out = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "total": len(all_videos),
        "videos": all_videos,
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\nOK {len(all_videos)} videos salvos em {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

