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
    {"nome": "A Dupla",          "id": "UCRbfE8wK0_f5BPXtH424G_Q"},
    {"nome": "LH Benfica",       "handle": "@lhbenfica"},
]

NS       = "http://www.w3.org/2005/Atom"
YT_NS    = "http://www.youtube.com/xml/schemas/2015"
MEDIA_NS = "http://search.yahoo.com/mrss/"
HEADERS  = {"User-Agent": "Mozilla/5.0 (compatible; bot)"}
MAX_FEED = 20  # quantos videos verificar no feed por canal

# Palavras que indicam AO VIVO no titulo
LIVE_KEYWORDS = ["ao vivo", "ao-vivo", "live", "direto", "jornada", "transmissao", "transmissão"]

# Palavras que indicam Short (alem de verificar redirect)
SHORT_KEYWORDS = ["#shorts", "#short", "shorts"]


def resolver_handle(handle):
    url = f"https://www.youtube.com/{handle}"
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=12) as r:
            html = r.read().decode("utf-8", errors="ignore")
        m = re.search(r'"channelId"\s*:\s*"(UC[^"]+)"', html)
        if m: return m.group(1)
        m = re.search(r'channel/(UC[^/"]+)', html)
        if m: return m.group(1)
    except Exception as e:
        print(f"  Erro ao resolver {handle}: {e}")
    return None


def titulo_tem_live(titulo):
    t = titulo.lower()
    return any(kw in t for kw in LIVE_KEYWORDS)


def titulo_tem_short(titulo):
    t = titulo.lower()
    return any(kw in t for kw in SHORT_KEYWORDS)


def is_short_por_redirect(video_id):
    """Verifica via HEAD request se o video e um Short."""
    url = f"https://www.youtube.com/shorts/{video_id}"
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        req.get_method = lambda: "HEAD"
        with urllib.request.urlopen(req, timeout=8) as r:
            return "/shorts/" in r.url
    except Exception:
        return False


def get_duracao_segundos(video_id):
    """Busca duracao via oEmbed + pagina do video para detectar Shorts."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10) as r:
            html = r.read().decode("utf-8", errors="ignore")
        # Busca "lengthSeconds" no JSON embutido na pagina
        m = re.search(r'"lengthSeconds"\s*:\s*"(\d+)"', html)
        if m:
            return int(m.group(1))
    except Exception:
        pass
    return None


def classificar_video(video_id, titulo):
    """
    Retorna: 'short', 'live', 'video' ou None (se nao conseguir verificar).
    Prioridade: exclui shorts, depois prefere live, depois video longo.
    """
    # 1. Titulo ja denuncia Short
    if titulo_tem_short(titulo):
        return "short"

    # 2. Verifica redirect para /shorts/
    if is_short_por_redirect(video_id):
        return "short"

    # 3. Busca duracao: Short = menos de 61 segundos
    dur = get_duracao_segundos(video_id)
    if dur is not None and dur < 61:
        return "short"

    # 4. Titulo indica live?
    if titulo_tem_live(titulo):
        return "live"

    return "video"


def buscar_melhor_video(canal_id, canal_nome):
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={canal_id}"
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=12) as resp:
            xml_data = resp.read()
        root    = ET.fromstring(xml_data)
        entries = root.findall(f"{{{NS}}}entry")
    except Exception as exc:
        print(f"  ERRO feed {canal_nome}: {exc}")
        return None

    candidatos_live  = []
    candidatos_video = []

    for entry in entries[:MAX_FEED]:
        def txt(el): return el.text if el is not None else ""

        video_id  = txt(entry.find(f"{{{YT_NS}}}videoId"))
        if not video_id:
            continue

        titulo    = txt(entry.find(f"{{{NS}}}title")) or "Sem titulo"
        link_el   = entry.find(f"{{{NS}}}link")
        link      = link_el.get("href") if link_el is not None else f"https://www.youtube.com/watch?v={video_id}"
        published = txt(entry.find(f"{{{NS}}}published"))[:10]
        thumb_el  = entry.find(f"{{{MEDIA_NS}}}group/{{{MEDIA_NS}}}thumbnail")
        thumbnail = (thumb_el.get("url") if thumb_el is not None
                     else f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg")

        tipo = classificar_video(video_id, titulo)

        if tipo == "short":
            print(f"  SHORT ignorado: {titulo[:50]}")
            continue

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
            candidatos_live.append(dados)
            print(f"  LIVE: {titulo[:60]}")
        else:
            candidatos_video.append(dados)
            print(f"  VIDEO: {titulo[:60]}")

        # Se ja temos uma live, podemos parar
        if candidatos_live:
            break

    # Retorna: prefere live, senao primeiro video longo
    if candidatos_live:
        return candidatos_live[0]
    if candidatos_video:
        return candidatos_video[0]

    print(f"  Nenhum video valido: {canal_nome}")
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
    print(f"\nvideos.json salvo - {len(videos)}/{len(CANAIS)} canais.\n")


if __name__ == "__main__":
    main()
