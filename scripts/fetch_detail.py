"""Tahap B: unduh halaman detail tiap tesis -> data/raw/ (bisa dilanjutkan).

Tiap tesis dicoba lewat beberapa varian URL (asli dari list, kanonik, trailing slash,
dan versi ter-encode) karena sebagian tesis lama hanya terbuka lewat salah satunya.
Entri ganda persis (duplicate_of) dilewati.

Pakai:  python scripts/fetch_detail.py [--limit N] [--retry-bad]
"""
import argparse
import json
import re
import sys
import time

from common import CONFIG, DATA, RAW, file_stem, new_session, safe_url, try_get


def slug_variants(url):
    """Slug alternatif: tanpa karakter khusus, atau karakter khusus -> '-'."""
    base, _, slug = url.rpartition('/')
    v1 = re.sub(r"['’`·\[\]]", '', slug)
    v2 = re.sub(r'-{2,}', '-', re.sub(r'[^A-Za-z0-9~._-]+', '-', slug))
    return [f'{base}/{v}' for v in (v1, v2) if v and v != slug]


def candidates(it):
    """Urutan percobaan URL; duplikat dibuang. Varian eksperimen di belakang."""
    base = [it['href'], it['url']] if it.get('ambiguous_url') else [it['url'], it['href']]
    base.append(it['url'] + '/')
    cands = base + [safe_url(x) for x in base]
    raw = it.get('href_raw') or ''
    if re.search(r'[\t\n\r]', raw):          # newline/tab dikirim sebagai %0A/%09, bukan dibuang
        cands.append(safe_url(raw))
        cands.append(safe_url(raw.split('?', 1)[0]))
    for v in slug_variants(it['url']):
        cands += [v, safe_url(v)]
    out = []
    for u in cands:
        if u not in out:
            out.append(u)
    return out


def load_known_bad(path=None):
    """Id halaman yang diketahui rusak di Digilib (config/halaman_rusak.txt)."""
    p = path or CONFIG / 'halaman_rusak.txt'
    try:
        lines = open(p, encoding='utf-8').read().splitlines()
    except FileNotFoundError:
        return set()
    return {l.split('#', 1)[0].strip() for l in lines if l.split('#', 1)[0].strip()}


def looks_like_detail(html):
    return bool(html) and 'og:title' in html


def fetch_one(session, it, delay=1.0):
    """Return (html|None, laporan 'status per URL')."""
    log = []
    for url in candidates(it):
        html, status = try_get(session, url, delay)
        if status.startswith('ERR'):          # gangguan jaringan: ulangi sekali
            time.sleep(2)
            html, status = try_get(session, url, delay)
        if html is not None and not looks_like_detail(html):
            html, status = None, '200-bukan-detail'
        log.append(status)
        if html is not None:
            return html, log
    return None, log


def main(limit=None, retry_bad=False):
    list_path = DATA / 'list.jsonl'
    if not list_path.exists():
        sys.exit('data/list.jsonl belum ada. Jalankan crawl_list.py dulu.')
    items = [json.loads(l) for l in open(list_path, encoding='utf-8')]
    items = [it for it in items if not it.get('duplicate_of')]
    bad = set() if retry_bad else load_known_bad()
    skipped_bad = sum(1 for it in items if it['id'] in bad)
    items = [it for it in items if it['id'] not in bad]
    RAW.mkdir(parents=True, exist_ok=True)
    session = new_session()
    failed, done = [], 0
    for it in items:
        out = RAW / f"{file_stem(it['id'])}.html"
        if out.exists() and out.stat().st_size > 0:
            continue
        if limit is not None and done >= limit:
            break
        html, log = fetch_one(session, it)
        if html is None:
            failed.append((it['id'], it['href'], ','.join(log)))
            print(f"GAGAL [{it['no']}] {it['id'][:60]}  (status per varian URL: {','.join(log)})")
            continue
        out.write_text(html, encoding='utf-8')
        done += 1
        note = '' if log == ['200'] else f'  (berhasil di varian ke-{len(log)})'
        print(f"[{it['no']}/{len(items)}] {it['id'][:60]}{note}")
    cached = sum(1 for it in items if (RAW / f"{file_stem(it['id'])}.html").exists())
    print(f'Selesai. Terunduh baru: {done}. Total di cache: {cached}/{len(items)}.'
          + (f' Dilewati (diketahui rusak, config/halaman_rusak.txt): {skipped_bad}.' if skipped_bad else ''))
    fp = DATA / 'failed.txt'
    if failed:
        fp.write_text('\n'.join('\t'.join(row) for row in failed), encoding='utf-8')
        print(f'{len(failed)} gagal di semua varian URL -> data/failed.txt (id, href asli, status).')
        print('Kalau konsisten 500, salin id-nya ke config/halaman_rusak.txt agar dilewati lain kali.')
    elif fp.exists():
        fp.unlink()  # jangan menyisakan daftar gagal yang sudah basi


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int, default=None, help='unduh maksimal N halaman baru')
    ap.add_argument('--retry-bad', action='store_true', help='coba lagi halaman di config/halaman_rusak.txt')
    a = ap.parse_args()
    main(a.limit, a.retry_bad)
