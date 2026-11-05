"""Diagnosa: untuk tesis berdetail tapi field kosong, tampilkan baris tabel aslinya.

Pakai:  python scripts/inspect_empty.py [year|subject|keywords] [jumlah]
"""
import json
import sys

from bs4 import BeautifulSoup

from common import DATA, RAW, clean, file_stem


def main(field='year', n=4):
    recs = [json.loads(l) for l in open(DATA / 'theses.jsonl', encoding='utf-8')]
    shown = 0
    label_counts = {}
    for r in recs:
        if not r['has_detail'] or r.get(field):
            continue
        html = (RAW / f"{file_stem(r['id'])}.html").read_text(encoding='utf-8')
        rows = []
        for tr in BeautifulSoup(html, 'html.parser').find_all('tr'):
            cells = tr.find_all('td')
            if len(cells) >= 3:
                rows.append((clean(cells[0].get_text()), clean(cells[-1].get_text(' '))[:60]))
        for lab, _ in rows:
            label_counts[lab] = label_counts.get(lab, 0) + 1
        if shown < n:
            print(f"\n[{r['no']}] {r['title'][:70]}\n    file: data/raw/{file_stem(r['id'])}.html")
            for lab, val in rows:
                print(f'    {lab:34s}: {val!r}')
            shown += 1
    print(f'\nLabel baris yang muncul pada tesis dengan {field} kosong (jumlah tesis):')
    for lab, c in sorted(label_counts.items(), key=lambda x: -x[1]):
        print(f'  {c:5d}  {lab}')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'year', int(sys.argv[2]) if len(sys.argv) > 2 else 4)
