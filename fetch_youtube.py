import json
import re
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime

CANAIS = [
    {"nome": "Alex Bage",        "id": "UCg6ONDqJLO_G2kJuxDPxTaA"},
    {"nome": "Farid Germano",    "id": "UCBOGYcnvM-9iI-8d-DUEeMw"},
    {"nome": "Diogo Rossi",      "id": "UC7tqZAeQWSfyRhQrFTn0MoA"},
    {"nome": "Duda Garbi",       "id": "UCHeN_p2zTo81Og5rLpUwmlg"},
    {"nome": "Canal do Gabardo", "id": "UCTdrwFad0HRoBq58P91nX1w"},
    {"nome": "Debate Raiz",      "id": "UC4SkxWmVRnERdmdl16SFcCQ"},
    {"nome": "Canal do CCD",     "id": "UC-vcAXksTA21wp1iN4ZGv6Q"},
    {"nome": "Careca de Saber",  "id": "UCUaNjDcaVliZyWd-MgsDAzw"},
    {"nome": "Gremio TV",        "id": "UCHKbUAiKHsWCCZrkDY_PZ8Q"},
    {"nome": "MDV Futebol",      "handle": "@mdvfutebol"},
    {"nome": "A Dupla",          "id": "UCRbfE8wK0_f5BPXtH424G_Q"},
    {"nome": "LH Benfica",       "handle": "@lhbenfica"},
]

NS       = "http://www.w3.org/2005/Atom"
YT_NS    = "http://www.youtube.com/xml/schemas/2015"
MEDIA_NS = "http://search.yahoo.com/mrss/"
HEADERS  = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
MAX_FEED = 15

LIVE_KW  = ["ao vivo", "ao-vivo", " live", "direto", "jornada", "transmissao",
            "transmissão", "| live", "- live", "#live"]
SHORT_KW = ["#shorts", "#short", " shorts", "shorts "]


def is_short_titulo(titulo):
    t = titulo.lower()
    return any(k in t for k in SHORT_KW)


def is_live_titulo(titulo):
    t = titulo.lower()
    return any(k in t for k in LIVE_KW)


def is_short_redirect(video_id):
    try:
        req = urllib.request.Request(
            f"https://www.youtube.com/shorts/{video_id}",
            headers=HEADERS
        )
        req.get_method = lambda: "HEAD"
        with urllib.request.urlopen(req, timeout=5) as r:
            return "/shorts/" in r.url
    except Exception:
        return False


def resolver_handle(handle):
    try:
        req = urllib.request.Request(
            f"https://www.youtube.com/{handle}",
            headers=HEADERS
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            html = r.read().decode("utf-8", errors="ignore")
        m = re.search(r'"channelId"\s*:\s*"(UC[^"]+)"', html)
        if m:
            return m.group(1)
    except Exception as e:
        print(f"  Erro resolver {handle}: {e}")
    return None


def buscar_feed(canal_id, canal_nome):
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={canal_id}"
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            xml_data = resp.read()
        root = ET.fromstring(xml_data)
        return root.findall(f"{{{NS}}}entry")
    except Exception as e:
        print(f"  ERRO feed {canal_nome}: {e}")
        return []


def extrair_dados(entry, canal_id, canal_nome):
    def txt(el): return el.text if el is not None else ""
    video_id  = txt(entry.find(f"{{{YT_NS}}}videoId"))
    titulo    = txt(entry.find(f"{{{NS}}}title")) or "Sem titulo"
    link_el   = entry.find(f"{{{NS}}}link")
    link      = link_el.get("href") if link_el is not None else f"https://www.youtube.com/watch?v={video_id}"
    published = txt(entry.find(f"{{{NS}}}published"))[:10]
    thumb_el  = entry.find(f"{{{MEDIA_NS}}}group/{{{MEDIA_NS}}}thumbnail")
    thumbnail = (thumb_el.get("url") if thumb_el is not None
                 else f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg")
    return video_id, titulo, link, published, thumbnail


def buscar_melhor_video(canal_id, canal_nome):
    entries = buscar_feed(canal_id, canal_nome)
    if not entries:
        return None

    melhor_live  = None
    melhor_video = None

    for entry in entries[:MAX_FEED]:
        video_id, titulo, link, published, thumbnail = extrair_dados(
            entry, canal_id, canal_nome
        )
        if not video_id:
            continue

        if is_short_titulo(titulo):
            print(f"  SHORT(titulo): {titulo[:55]}")
            continue

        if is_short_redirect(video_id):
            print(f"  SHORT(redirect): {titulo[:55]}")
            continue

        tipo = "live" if is_live_titulo(titulo) else "video"
        dados = {
            "canal":     canal_nome,
            "canal_id":  canal_id,
            "video_id":  video_id,
            "titulo":    titulo,
            "link":      link,
            "embed_url": f"https://www.youtube.com/embed/{video_id}",
            "thumbnail": thumbnail,
            "publicado": published,
            "tipo":      tipo,
        }

        if tipo == "live":
            print(f"  LIVE: {titulo[:60]}")
            melhor_live = dados
            break
        else:
            print(f"  VIDEO: {titulo[:60]}")
            if melhor_video is None:
                melhor_video = dados

    resultado = melhor_live or melhor_video
    if not resultado:
        print(f"  Sem video valido: {canal_nome}")
    return resultado


def main():
    print(f"\nDominio Tricolor — {datetime.now().strftime('%d/%m/%Y %H:%M')}\n")
    videos = []

    for canal in CANAIS:
        canal_id = canal.get("id")
        if not canal_id:
            handle = canal.get("handle", "")
            print(f"Resolvendo {handle}...")
            canal_id = resolver_handle(handle)
            if not canal_id:
                print(f"  Nao resolvido: {handle}")
                continue

        resultado = buscar_melhor_video(canal_id, canal["nome"])
        if resultado:
            videos.append(resultado)

    saida = {
        "atualizado_em": datetime.now().strftime("%d/%m/%Y as %H:%M"),
        "total_canais":  len(videos),
        "videos":        videos,
    }
    with open("videos.json", "w", encoding="utf-8") as f:
        json.dump(saida, f, ensure_ascii=False, indent=2)

    print(f"\nSalvo: {len(videos)}/{len(CANAIS)} canais | {saida['atualizado_em']}\n")


if __name__ == "__main__":
    main()
