"""Bangun web/data/thesis-data.json dari data/classified.jsonl + config/kk.yaml.

Pakai:  python scripts/build_site.py
Skema kompatibel dengan web/js/app.js (groups, theses[].no/judul/memberships/perlu_review)
plus field baru: url, author, advisors, year, subject, keywords_official.
"""
import json
import sys
from datetime import date

from common import DATA, ROOT
from names import KK_META, load_kk


def main():
    path = DATA / 'classified.jsonl'
    if not path.exists():
        sys.exit('data/classified.jsonl belum ada. Jalankan classify_thesis.py dulu.')
    abstracts = {}
    tpath = DATA / 'theses.jsonl'
    if tpath.exists():
        for line in open(tpath, encoding='utf-8'):
            t = json.loads(line)
            if t.get('abstract'):
                abstracts[str(t['no'])] = t['abstract']
    kk = load_kk()
    groups = [{'slug': s, **{k: spec[k] for k in KK_META}} for s, spec in kk.items()]
    theses = []
    for line in open(path, encoding='utf-8'):
        o = json.loads(line)
        theses.append({
            'no': str(o['no']),
            'judul': o['judul'],
            'url': o['url'],
            'author': o['author'],
            'advisors': o['advisors'],
            'year': o['year'],
            'subject': o['subject'],
            'keywords_official': o['keywords_official'],
            'has_abstract': str(o['no']) in abstracts,
            'perlu_review': o['perlu_review'],
            'memberships': [
                {'slug': m['slug'], 'role': m['role'], 'score': m['score'],
                 'keywords': m['keywords'], 'advisors': m['advisors']}
                for m in o['memberships']
            ],
        })
    out = ROOT / 'web' / 'data' / 'thesis-data.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, 'w', encoding='utf-8') as f:
        json.dump({'generated': date.today().isoformat(), 'groups': groups, 'theses': theses},
                  f, ensure_ascii=False, separators=(',', ':'))
    # abstrak dipisah dari JSON utama: ~1-2 MB, dimuat web hanya saat dibutuhkan
    with open(out.parent / 'abstracts.json', 'w', encoding='utf-8') as f:
        json.dump(abstracts, f, ensure_ascii=False, separators=(',', ':'))
    print(f'{len(theses)} tesis -> {out}')
    print(f'{len(abstracts)} abstrak -> {out.parent / "abstracts.json"}')


if __name__ == '__main__':
    main()
