import feedparser
import json
from datetime import datetime, timezone
import requests
import re

CHANNELS = [
    {'name': 'A Dupla',               'handle': '@ADuplaYT'},
    {'name': 'Bage TV',               'handle': '@BageTvOficial'},
    {'name': 'Bruno Soares Reporter', 'handle': '@BrunoSoaresReporter'},
    {'name': 'Canal do CCD',          'handle': '@cesarcidadedias'},
    {'name': 'Canal do Farid',        'handle': '@CanaldoFarid'},
    {'name': 'Canal do Gabardo',      'handle': '@CanaldoGabardo'},
    {'name': 'Careca de Saber TV',    'handle': '@carecadesabertv'},
    {'name': 'Diogo Rossi Reporter',  'handle': '@DiogoRossiReporter'},
    {'name': 'Duda Garbi',            'handle': '@dudagarbi'},
    {'name': 'GremioTV Oficial',      'handle': '@Gremio'},
    {'name': 'GZH Digital',           'handle': '@gzhdigital'},
    {'name': 'Jeremias Wernek',       'handle': '@JeremiasWernek'},
    {'name': 'LH Benfica',            'handle': '@lhbenfica'},
    {'name': 'MDV Futebol',           'channel_id': 'UCbaLsDyl0cehhUvlycX7Mxw'},
    {'name': 'Radio Grenal',          'handle': '@RadioGrenal'},
    {'name': 'Radio Imortal',         'handle': '@rdimortal'},
]

RSS_BASE = 'https://www.youtube.com/feeds/videos.xml?channel_id={}'
VIDEOS_TARGET  = 2
FETCH_EXTRA    = 10
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
    try:
        r = SESSION.head('https://www.youtube.com/shorts/' + video_id, timeout=8, allow_redirects=True)
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
    # CHANNELS jÃ¡ estÃ¡ em ordem alfabÃ©tica â€” processa nessa ordem
    for ch in CHANNELS:
        all_videos.extend(fetch(ch))

    # Ordena por canal (alfabÃ©tico) e dentro de cada canal por data (mais recente primeiro)
    all_videos.sort(key=lambda v: (
        v['channel'].lower(),
        -(datetime.fromisoformat(v['published'].replace('Z', '+00:00')) if v['published'] else datetime.min.replace(tzinfo=timezone.utc)).timestamp()
    ))

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

