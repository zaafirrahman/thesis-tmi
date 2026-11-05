"""Konfigurasi & helper bersama untuk semua skrip."""
import os
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = Path(os.environ.get('THESIS_DATA_DIR', ROOT / 'data'))
RAW = DATA / 'raw'            # cache HTML halaman detail
RAW_LIST = DATA / 'raw_list'  # cache HTML halaman list
CONFIG = ROOT / 'config'

BASE = 'https://digilib.itb.ac.id'
PRODI_URL = BASE + '/prodi/index/2820'   # Teknik dan Manajemen Industri - S2
USER_AGENT = 'thesis-tmi-catalog/1.0 (riset akademik; scraping pelan-pelan)'


def clean(text):
    """Rapikan whitespace (judul di digilib dipecah per huruf lewat <span>)."""
    return re.sub(r'\s+', ' ', text or '').strip()


def fix_href(href):
    """Browser membuang \\t \\n \\r di dalam URL; di HTML digilib ada href yang
    kebetulan memuatnya. Spasi sisa di-encode."""
    return re.sub(r'[\t\n\r]', '', href).strip().replace(' ', '%20')


def canonical_url(href):
    """Buang query (?rows=..&per_page=..) dan trailing slash."""
    return fix_href(href).split('?', 1)[0].rstrip('/')


def safe_url(u):
    """Percent-encode path secara ketat ('  [ ] ’ dst) - server digilib menolak
    apostrof mentah dengan 400. Query dibiarkan."""
    from urllib.parse import quote, unquote, urlsplit, urlunsplit
    # urlsplit() Python membuang \t \n \r diam-diam; encode dulu supaya tidak hilang
    u = re.sub(r'[\t\r\n]', lambda m: '%%%02X' % ord(m.group()), u)
    p = urlsplit(u)
    return urlunsplit((p.scheme, p.netloc, quote(unquote(p.path), safe='/-._~'), p.query, ''))


def file_stem(item_id):
    """Nama file cache yang aman & pendek (batas path Windows 260 karakter)."""
    import hashlib
    safe = re.sub(r'[^A-Za-z0-9._-]', '_', item_id)[:80]
    return f"{safe}~{hashlib.sha1(item_id.encode('utf-8')).hexdigest()[:8]}"


def item_id(url):
    return canonical_url(url).rsplit('/', 1)[-1]


def http_get(session, url, retries=4, delay=1.0):
    """GET sopan dengan retry + backoff. Return teks HTML, atau None kalau 404.
    Raise RuntimeError kalau tetap gagal setelah semua percobaan."""
    last = None
    for attempt in range(retries):
        try:
            r = session.get(url, timeout=30)
            if r.status_code == 404:
                return None
            r.raise_for_status()
            time.sleep(delay)
            return r.text
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(delay * (2 ** attempt))
    raise RuntimeError(f'gagal GET {url}: {last}')


def try_get(session, url, delay=1.0):
    """Satu percobaan GET. Return (html|None, status) - status '200', '500', 'ERR Timeout', ..."""
    try:
        r = session.get(url, timeout=30)
    except Exception as e:  # noqa: BLE001
        return None, f'ERR {type(e).__name__}'
    time.sleep(delay)
    return (r.text, '200') if r.status_code == 200 else (None, str(r.status_code))


def new_session():
    import requests
    s = requests.Session()
    s.headers['User-Agent'] = USER_AGENT
    return s
