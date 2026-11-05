"""Tahap A: crawl halaman list prodi -> data/list.jsonl

Pagination berbasis URL (bukan klik 'Next'):
  halaman 1 : /prodi/index/2820
  halaman n : /prodi/index/2820?rows=<total>&per_page=<offset>   (offset 20, 40, ...)
Dari tiap item list diambil: judul, URL detail asli, penulis+NIM, dospem.

Pakai:  python scripts/crawl_list.py [--refresh]
"""
import argparse
import hashlib
import json
import math
import re
import sys
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup

from common import (DATA, PRODI_URL, RAW_LIST, canonical_url, clean, fix_href,
                    http_get, item_id, new_session)


def _split_sup(sup):
    """Teks setelah ikon 'bi-person' = penulis, setelah 'bi-people' = dospem."""
    author, adv, cur = '', '', None
    for node in sup.children:
        name = getattr(node, 'name', None)
        if name == 'i':
            cls = node.get('class', [])
            if 'bi-person' in cls:
                cur = 'author'
            elif 'bi-people' in cls:
                cur = 'adv'
        elif name is None:  # NavigableString
            if cur == 'author':
                author += str(node)
            elif cur == 'adv':
                adv += str(node)
    return clean(author), clean(adv)


def parse_list_page(html):
    """Return (items, total_records). total_records None kalau tidak ditemukan."""
    soup = BeautifulSoup(html, 'html.parser')
    m = re.search(r'([\d.]+)\s*records', soup.get_text(' '))
    total = int(m.group(1).replace('.', '')) if m else None

    items = []
    for box in soup.select('div.col-lg-11'):
        a = box.select_one("a[href*='view_data']")
        if not a:
            continue
        href_raw = a['href']
        href = fix_href(href_raw)
        qs = parse_qs(urlparse(href).query)
        rank = int(qs['per_page'][0]) if qs.get('per_page', [''])[0].isdigit() else None
        sups = box.find_all('sup')
        author_raw, adv_raw = _split_sup(sups[-1]) if sups else ('', '')
        am = re.match(r'^(.*?)\s*\[([^\]]*)\]\s*$', author_raw)  # NIM bisa kosong / 'S2-758403'
        author, nim = (clean(am.group(1)), clean(am.group(2)) or None) if am else (author_raw, None)
        advisors = [clean(x) for x in adv_raw.split(';') if clean(x)]
        url = canonical_url(href)
        items.append({
            'id': item_id(url),
            'url': url,
            'href': href,
            'href_raw': href_raw,
            'rank': rank,
            'title': clean(a.get_text()),
            'author': author,
            'nim': nim,
            'advisors': advisors,
        })
    return items, total


def assign_ids(items):
    """Beberapa tesis lama (tanpa NIM di URL) punya judul -> slug SAMA padahal record
    berbeda. Anggota grup kembar diberi id unik (slug~hash penulis+judul) dan ditandai
    ambiguous_url, karena halaman detailnya mungkin tidak bisa dibedakan lewat URL.
    Bila judul DAN penulis juga sama (entri ganda persis di digilib), anggota berikutnya
    diberi akhiran .2/.3 dan duplicate_of = id pertama. Tidak ada yang dibuang di sini."""
    groups = {}
    for it in items:
        it.setdefault('duplicate_of', None)
        groups.setdefault(it['id'], []).append(it)
    for slug, members in groups.items():
        if len(members) > 1:
            used = {}
            for it in members:
                h = hashlib.sha1((it['title'] + '|' + (it['author'] or '')).encode('utf-8')).hexdigest()[:6]
                base = f'{slug}~{h}'
                used[base] = used.get(base, 0) + 1
                it['id'] = base if used[base] == 1 else f'{base}.{used[base]}'
                it['ambiguous_url'] = True
                if used[base] > 1:
                    it['duplicate_of'] = base
    return items


def page_url(offset, total):
    return PRODI_URL if offset == 0 else f'{PRODI_URL}?rows={total}&per_page={offset}'


def crawl(refresh=False):
    RAW_LIST.mkdir(parents=True, exist_ok=True)
    session = new_session()

    def load(offset, total):
        cache = RAW_LIST / f'page_{offset}.html'
        if cache.exists() and not refresh:
            return cache.read_text(encoding='utf-8')
        html = http_get(session, page_url(offset, total))
        if html is None:
            raise RuntimeError(f'halaman offset {offset} 404')
        cache.write_text(html, encoding='utf-8')
        return html

    items, total = parse_list_page(load(0, None))
    if not total or not items:
        sys.exit('Gagal membaca halaman pertama (total records / item kosong).')
    per_page = len(items)
    pages = math.ceil(total / per_page)
    print(f'Total {total} records, {per_page}/halaman -> {pages} halaman')

    all_items = list(items)
    for p in range(1, pages):
        offset = p * per_page
        page_items, _ = parse_list_page(load(offset, total))
        print(f'  offset {offset}: {len(page_items)} item')
        if not page_items:
            break
        all_items.extend(page_items)

    # nomor urut = rank di situs. Dedup HANYA untuk item yang tampil dua kali karena
    # halaman tumpang tindih (rank sama); entri ganda di situs (rank beda) tetap disimpan.
    seen, unique = set(), []
    for it in all_items:
        key = it['rank'] if it['rank'] is not None else it['id']
        if key in seen:
            continue
        seen.add(key)
        it['no'] = it['rank'] or len(unique) + 1
        it['ambiguous_url'] = False
        unique.append(it)
    assign_ids(unique)  # setelah dedup-rank, supaya halaman tumpang tindih tak dikira kembar
    n_amb = sum(1 for it in unique if it['ambiguous_url'])
    n_dup = sum(1 for it in unique if it['duplicate_of'])
    if n_amb:
        print(f'{n_amb} record berbagi slug URL dengan record lain (diberi id unik).')
    if n_dup:
        print(f'{n_dup} di antaranya entri ganda persis (judul+penulis sama): disimpan di '
              'list.jsonl tapi dilewati di tahap berikutnya.')

    DATA.mkdir(parents=True, exist_ok=True)
    with open(DATA / 'list.jsonl', 'w', encoding='utf-8') as f:
        for it in unique:
            f.write(json.dumps(it, ensure_ascii=False) + '\n')
    print(f'Tersimpan {len(unique)} item unik -> {DATA / "list.jsonl"}')
    if len(unique) != total:
        print(f'PERINGATAN: dapat {len(unique)} item, situs menyebut {total}.')
        sys.exit(1)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--refresh', action='store_true', help='abaikan cache halaman list')
    crawl(ap.parse_args().refresh)
