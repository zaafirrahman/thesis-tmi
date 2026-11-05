"""Tahap C: parse halaman detail (data/raw/*.html) + info list -> data/theses.jsonl

Pakai:  python scripts/parse_detail.py
"""
import json
import re
import sys

from bs4 import BeautifulSoup

from common import DATA, RAW, canonical_url, clean, file_stem

LABELS = {
    'penulis': 'author',
    'kontributor / dosen pembimbing': 'advisors',
    'jenis koleksi': 'collection',
    'tahun terbit': 'year',
    'penerbit': 'publisher',
    'subjek': 'subject',
    'kata kunci': 'keywords',
}


def split_keywords(s):
    # titik penutup ('... System.') dibuang agar sama dengan tesis lain yang menulisnya tanpa titik
    out = [clean(k).rstrip('. ') for k in re.split(r'[,;\n]', s or '')]
    return [k for k in out if k]


def parse_detail(html):
    soup = BeautifulSoup(html, 'html.parser')
    rec = {'title': None, 'url': None, 'author': None, 'nim': None, 'advisors': [],
           'year': None, 'subject': None, 'keywords': [], 'collection': None,
           'publisher': None, 'abstract': None}

    og = soup.find('meta', property='og:title')
    h2 = soup.find('h2')
    rec['title'] = clean(og['content']) if og and og.get('content') else (clean(h2.get_text('')) if h2 else None)
    can = soup.find('link', rel='canonical')
    if can and can.get('href'):
        rec['url'] = canonical_url(can['href'])

    for tr in soup.find_all('tr'):
        cells = tr.find_all('td')
        if len(cells) < 3:
            continue
        key = LABELS.get(clean(cells[0].get_text()).lower())
        if not key:
            continue
        cell = cells[-1]
        text = clean(cell.get_text(' '))
        if key == 'author':
            m = re.match(r'^(.*?)\s*\[([^\]]*)\]\s*$', text)
            rec['author'], rec['nim'] = ((clean(m.group(1)) or None, clean(m.group(2)) or None)
                                        if m else (text or None, None))
        elif key == 'advisors':
            names = [clean(s.get_text()) for s in cell.select('.contributor-name')]
            if not names:
                names = [clean(x) for x in re.split(r'[;\n]', cell.get_text('\n')) if clean(x)]
            rec['advisors'] = names
        elif key == 'year':
            m = re.search(r'\d{4}', text)
            rec['year'] = int(m.group()) if m else None
        elif key == 'keywords':
            rec['keywords'] = split_keywords(cell.get_text('\n'))
        else:
            rec[key] = text or None

    pane = soup.select_one('#pills1-tab2')
    ab = clean(pane.get_text(' ')) if pane else ''
    if not ab:
        d = soup.find('meta', property='og:description')
        ab = clean(d['content']) if d and d.get('content') else ''
    rec['abstract'] = ab or None
    return rec


def _tok(s):
    return set(re.findall(r'[a-z]+', (s or '').lower()))


def author_matches(a, b, threshold=0.4):
    """Kemiripan token nama penulis (untuk memastikan detail = record yang dimaksud)."""
    ta, tb = _tok(a), _tok(b)
    return bool(ta and tb) and len(ta & tb) / len(ta | tb) >= threshold


def main():
    list_path = DATA / 'list.jsonl'
    if not list_path.exists():
        sys.exit('data/list.jsonl belum ada. Jalankan crawl_list.py dulu.')
    all_items = [json.loads(l) for l in open(list_path, encoding='utf-8')]
    items = [it for it in all_items if not it.get('duplicate_of')]
    n_dup = len(all_items) - len(items)
    out, no_detail, mismatch = [], 0, 0
    empty = {k: 0 for k in ('author', 'advisors', 'year', 'subject', 'keywords', 'abstract')}
    for it in items:
        path = RAW / f"{file_stem(it['id'])}.html"
        d = parse_detail(path.read_text(encoding='utf-8')) if path.exists() else None
        # slug kembar: detail mungkin milik record lain -> pakai hanya bila penulisnya cocok
        if d and it.get('ambiguous_url') and not author_matches(d['author'], it['author']):
            d, mismatch = None, mismatch + 1
        if d is None:
            no_detail += 1
        rec = {
            'id': it['id'], 'no': it['no'], 'url': (d or {}).get('url') or it['url'],
            'title': (d or {}).get('title') or it['title'],
            'author': (d or {}).get('author') or it['author'],
            'nim': (d or {}).get('nim') or it['nim'],
            # dospem: detail lebih bersih; list sebagai cadangan
            'advisors': (d or {}).get('advisors') or it['advisors'],
            'year': (d or {}).get('year'), 'subject': (d or {}).get('subject'),
            'keywords': (d or {}).get('keywords') or [],
            'collection': (d or {}).get('collection'), 'abstract': (d or {}).get('abstract'),
            'has_detail': d is not None,
        }
        for k in empty:
            if not rec[k]:
                empty[k] += 1
        out.append(rec)
    with open(DATA / 'theses.jsonl', 'w', encoding='utf-8') as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    print(f'{len(out)} tesis -> {DATA / "theses.jsonl"} (tanpa detail: {no_detail}, '
          f'detail tidak cocok & diabaikan: {mismatch}, entri ganda dilewati: {n_dup})')
    print('Field kosong:', ', '.join(f'{k}={v}' for k, v in empty.items()))


if __name__ == '__main__':
    main()
