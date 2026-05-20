import feedparser
import json
from datetime import datetime, timezone
import requests
import re

CHANNELS = [
    {'name': 'Bage TV',               'handle': '@BageTvOficial'},
    {'name': 'Canal do CCD',          'handle': '@cesarcidadedias'},
    {'name': 'Careca de Saber TV',    'handle': '@carecadesabertv'},
    {'name': 'GremioTV Oficial',      'handle': '@Gremio'},
    {'name': 'Canal do Gabardo',      'handle': '@CanaldoGabardo'},
    {'name': 'Radio Imortal',         'handle': '@rdimortal'},
    {'name': 'MDV Futebol',           'channel_id': 'UCbaLsDyl0cehhUvlycX7Mxw'},
    {'name': 'A Dupla',               'handle': '@ADuplaYT'},
    {'name': 'Bruno Soares Reporter', 'handle': '@BrunoSoaresReporter'},
    {'name': 'Canal do Farid',        'handle': '@CanaldoFarid'},
    {'name': 'Diogo Rossi Reporter',  'handle': '@DiogoRossiReporter'},
    {'name': 'Radio Grenal',          'handle': '@RadioGrenal'},
    {'name': 'Jeremias Wernek',       'handle': '@JeremiasWernek'},
    {'name': 'LH Benfica',            'handle': '@lhbenfica'},
    {'name': 'Duda Garbi',            'handle': '@dudagarbi'},
]

RSS_BASE       = 'https://www.youtube.com/feeds/videos.xml?channel_id={}'
VIDEOS_TARGET  = 2
FETCH_EXTRA    = 10  # busca mais para compensar os shorts filtrados
OUTPUT_FILE    = 'videos.json'
SESSION        = requests.Session()
SESSION.headers.update({'User-Agent': 'Mozilla/5.0'})


def resolve_handle(handle):
    try:
        r = SESSION.get('https://www.youtube.com/' + handle, timeout=15)
        r.encoding = 'utf-8'
        m = re.search(r'"externalId":"(UC[\w-]{22})"', r.text)
        if m:
            return m.group(1)
        m = re.search(r'youtube\.com/channel/(UC[\w-]{22})', r.text)
        if m:
            return m.group(1)
    except Exception as e:
        print('[WARN]', handle, str(e))
    return None


def is_short(video_id):
    url = 'https://www.youtube.com/shorts/' + video_id
    try:
        r = SESSION.head(url, timeout=8, allow_redirects=True)
        # Se a URL final ainda contem /shorts/ eh um short
        return '/shorts/' in r.url
    except Exception:
        return False


def safe(v):
    if not isinstance(v, str):
        return str(v)
    try:
        return v.encode('latin-1').decode('utf-8')
    except Exception:
        return v


def fetch(ch):
    cid = ch.get('channel_id')
    name = ch['name']
    if not cid:
        handle = ch.get('handle', '')
        print('[INFO] Resolvendo', name, handle)
        cid = resolve_handle(handle)
        if cid:
            ch['channel_id'] = cid
            print('[OK]  ', name, '->', cid)
        else:
            print('[SKIP]', name)
            return []
    try:
        r = SESSION.get(RSS_BASE.format(cid), timeout=15)
        r.encoding = 'utf-8'
        feed = feedparser.parse(r.text)
    except Exception as e:
        print('[ERRO]', name, str(e))
        return []

    videos = []
    for entry in feed.entries[:FETCH_EXTRA]:
        vid = entry.get('yt_videoid', '')
        if not vid:
            continue
        # Filtra Shorts
        if is_short(vid):
            print('[SHORT]', vid, 'ignorado')
            continue
        videos.append({
            'channel':   safe(name),
            'title':     safe(entry.get('title', '')),
            'videoId':   vid,
            'url':       'https://www.youtube.com/watch?v=' + vid,
            'thumbnail': 'https://img.youtube.com/vi/' + vid + '/mqdefault.jpg',
            'published': entry.get('published', ''),
        })
        if len(videos) >= VIDEOS_TARGET:
            break

    print('[OK]  ', name + ':', len(videos), 'video(s)')
    return videos


def main():
    all_videos = []
    for ch in CHANNELS:
        all_videos.extend(fetch(ch))

    def dt(v):
        try:
            return datetime.fromisoformat(v['published'].replace('Z', '+00:00'))
        except Exception:
            return datetime.min.replace(tzinfo=timezone.utc)

    all_videos.sort(key=dt, reverse=True)
    out = {
        'updated_at': datetime.now(timezone.utc).isoformat(),
        'total': len(all_videos),
        'videos': all_videos,
    }
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print('OK', len(all_videos), 'videos salvos em', OUTPUT_FILE)


if __name__ == '__main__':
    main()

