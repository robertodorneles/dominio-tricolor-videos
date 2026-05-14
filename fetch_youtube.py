"""
Automacao Dominio Tricolor - Busca o video mais novo de cada canal via RSS
Suporta Channel IDs (UCxxxxxxx) e handles (@nome)
Execucao: python fetch_youtube.py
"""

import json
import re
import urllib.request
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
    {"nome": "A Dupla",          "handle": "@ADuplaYT"},
    {"nome": "LH Benfica",       "handle": "@lhbenfica"},
]

NS       = "http://www.w3.org/2005/Atom"
YT_NS    = "http://www.youtube.com/xml/schemas/2015"
MEDIA_NS = "http://search.yahoo.com/mrss/"
HEADERS  = {"User-Agent": "Mozilla/5.0 (compatible; bot)"}


def resolver_handle(handle):
    url = f"https://www.youtube.com/{handle}"
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=12) as r:
            html = r.read().decode("utf-8", errors="ignore")
        m = re.search(r'"channelId"\s*:\s*"(UC[^"]+)"', html)
        if m:
            return m.group(1)
        m = re.search(r'channel/(UC[^/"]+)', html)
        if m:
            return m.group(1)
    except Exception as e:
        print(f"  Erro ao resolver {handle}: {e}")
    return None


def buscar_ultimo_video(canal_id, canal_nome):
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={canal_id}"
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=12) as resp:
            xml_data = resp.read()

        root  = ET.fromstring(xml_data)
        entry = root.find(f"{{{NS}}}entry")
        if entry is None:
            print(f"  Sem videos: {canal_nome}")
            return None

        def txt(el): return el.text if el is not None else ""

        video_id  = txt(entry.find(f"{{{YT_NS}}}videoId"))
        titulo    = txt(entry.find(f"{{{NS}}}title")) or "Sem titulo"
        link_el   = entry.find(f"{{{NS}}}link")
        link      = link_el.get("href") if link_el is not None else f"https://www.youtube.com/watch?v={video_id}"
        published = txt(entry.find(f"{{{NS}}}published"))[:10]
        thumb_el  = entry.find(f"{{{MEDIA_NS}}}group/{{{MEDIA_NS}}}thumbnail")
        thumbnail = (thumb_el.get("url") if thumb_el is not None
                     else f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg")

        print(f"  OK {canal_nome}: {titulo[:60]}...")
        return {
            "canal":     canal_nome,
            "canal_id":  canal_id,
            "video_id":  video_id,
            "titulo":    titulo,
            "link":      link,
            "embed_url": f"https://www.youtube.com/embed/{video_id}",
            "thumbnail": thumbnail,
            "publicado": published,
        }

    except Exception as exc:
        print(f"  ERRO em {canal_nome}: {exc}")
        return None


def main():
    print(f"\nDominio Tricolor - Atualizando ({datetime.now().strftime('%d/%m/%Y %H:%M')})\n")
    videos = []
    for canal in CANAIS:
        canal_id = canal.get("id")
        if not canal_id:
            handle = canal.get("handle", "")
            print(f"  Resolvendo {handle}...")
            canal_id = resolver_handle(handle)
            if not canal_id:
                print(f"  Nao resolvido: {handle}")
                continue
        resultado = buscar_ultimo_video(canal_id, canal["nome"])
        if resultado:
            videos.append(resultado)

    saida = {
        "atualizado_em": datetime.now().strftime("%d/%m/%Y as %H:%M"),
        "total_canais":  len(videos),
        "videos":        videos,
    }
    with open("videos.json", "w", encoding="utf-8") as f:
        json.dump(saida, f, ensure_ascii=False, indent=2)

    print(f"\nvideos.json salvo - {len(videos)}/{len(CANAIS)} canais.\n")


if __name__ == "__main__":
    main()
"""
Automação Domínio Tricolor — Busca o vídeo mais novo de cada canal via RSS
Sem precisar de API Key do YouTube. Salva em videos.json.

Canais: Alex Bagé · Farid Germano · Diogo Rossi · Duda Garbi
        Canal do Gabardo · Debate Raiz

Execução: python fetch_youtube.py
"""

import json
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime

# ============================================================
# CANAIS — todos com IDs confirmados
# Para adicionar mais: {"nome": "Nome", "id": "UCxxxxxxxx"}
# ============================================================
CANAIS = [
    {"nome": "Alex Bagé",        "id": "UCg6ONDqJLO_G2kJuxDPxTaA"},
    {"nome": "Farid Germano",    "id": "UCBOGYcnvM-9iI-8d-DUEeMw"},
    {"nome": "Diogo Rossi",      "id": "UC7tqZAeQWSfyRhQrFTn0MoA"},
    {"nome": "Duda Garbi",       "id": "UCHeN_p2zTo81Og5rLpUwmlg"},
    {"nome": "Canal do Gabardo", "id": "UCTdrwFad0HRoBq58P91nX1w"},
    {"nome": "Debate Raiz",      "id": "UC4SkxWmVRnERdmdl16SFcCQ"},
]
# ============================================================

NS       = "http://www.w3.org/2005/Atom"
YT_NS    = "http://www.youtube.com/xml/schemas/2015"
MEDIA_NS = "http://search.yahoo.com/mrss/"


def buscar_ultimo_video(canal_id: str, canal_nome: str):
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={canal_id}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=12) as resp:
            xml_data = resp.read()

        root  = ET.fromstring(xml_data)
        entry = root.find(f"{{{NS}}}entry")
        if entry is None:
            print(f"  ⚠️  Sem vídeos: {canal_nome}")
            return None

        def txt(el): return el.text if el is not None else ""

        video_id  = txt(entry.find(f"{{{YT_NS}}}videoId"))
        titulo    = txt(entry.find(f"{{{NS}}}title")) or "Sem título"
        link_el   = entry.find(f"{{{NS}}}link")
        link      = link_el.get("href") if link_el is not None else f"https://www.youtube.com/watch?v={video_id}"
        published = txt(entry.find(f"{{{NS}}}published"))[:10]
        thumb_el  = entry.find(f"{{{MEDIA_NS}}}group/{{{MEDIA_NS}}}thumbnail")
        thumbnail = (thumb_el.get("url") if thumb_el is not None
                     else f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg")

        print(f"  ✅ {canal_nome}: {titulo[:65]}...")
        return {
            "canal":     canal_nome,
            "canal_id":  canal_id,
            "video_id":  video_id,
            "titulo":    titulo,
            "link":      link,
            "embed_url": f"https://www.youtube.com/embed/{video_id}",
            "thumbnail": thumbnail,
            "publicado": published,
        }

    except Exception as exc:
        print(f"  ❌ Erro em {canal_nome}: {exc}")
        return None


def main():
    print(f"\n🔍 Domínio Tricolor — Atualizando vídeos ({datetime.now().strftime('%d/%m/%Y %H:%M')})\n")
    videos = [v for c in CANAIS if (v := buscar_ultimo_video(c["id"], c["nome"]))]

    saida = {
        "atualizado_em": datetime.now().strftime("%d/%m/%Y às %H:%M"),
        "total_canais":  len(videos),
        "videos":        videos,
    }
    with open("videos.json", "w", encoding="utf-8") as f:
        json.dump(saida, f, ensure_ascii=False, indent=2)

    print(f"\n✅ videos.json salvo — {len(videos)}/{len(CANAIS)} canais atualizados.\n")


if __name__ == "__main__":
    main()
