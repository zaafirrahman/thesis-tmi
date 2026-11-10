"""Bangun web/data/thesis-data.json + web/data/abstracts.json dari data/classified.jsonl.

Pakai:  python scripts/build_site.py

thesis-data.json : groups (+ daftar dosen resmi tiap KK) dan theses[] dengan
                   no, judul, url, author, advisors (nama kanonik), year (tahun terbit), angkatan (dari NIM), subject,
                   keywords_official, has_abstract, perlu_review, review_reasons, memberships.
abstracts.json   : {no: teks abstrak}, dimuat web hanya saat abstrak dibuka.
"""
import hashlib
import json
import re
import sys
from datetime import date

from common import DATA, ROOT, angkatan_from_nim, usable_abstract
from names import KK_META, LecturerIndex, load_aliases, load_extra, load_kk, name_key


def short(name):
    """'Prof. Dr. Rajesri Govindaraju, S.T., M.T.' -> 'Prof. Dr. Rajesri Govindaraju' (tanpa gelar belakang)."""
    return ' '.join(name.split(',', 1)[0].split()).strip(' .') or name


def bump_sw_cache(sw_text, data_hash):
    """sw.js: 'katalog-tmi-v5' -> 'katalog-tmi-v5-<hash data>'. Tiap data berubah, nama cache berubah,
    sehingga pengunjung lama otomatis membuang cache lama. Versi 'vN' tetap dinaikkan manual
    bila app.js/CSS berubah."""
    return re.sub(r"const CACHE_NAME = 'katalog-tmi-(v\d+)(?:-[0-9a-f]{8})?';",
                  lambda m: f"const CACHE_NAME = 'katalog-tmi-{m.group(1)}-{data_hash}';", sw_text, count=1)


def main():
    path = DATA / 'classified.jsonl'
    if not path.exists():
        sys.exit('data/classified.jsonl belum ada. Jalankan classify_thesis.py dulu.')
    kk = load_kk()
    idx = LecturerIndex(kk, load_aliases(), load_extra())

    def canonical(raw):
        """Satukan ejaan berbeda dari dosen yang sama ke satu nama tampilan."""
        key, _slugs, method = idx.match(raw)
        if key and method != 'unmapped':
            return short(idx.display.get(key, raw))
        return short(raw)

    abstracts = {}
    tpath = DATA / 'theses.jsonl'
    if tpath.exists():
        for line in open(tpath, encoding='utf-8'):
            t = json.loads(line)
            ab = usable_abstract(t.get('abstract'))   # buang placeholder ('P', '-', ...)
            if ab:
                abstracts[str(t['no'])] = ab

    groups = []
    for slug, spec in kk.items():
        g = {'slug': slug, **{k: spec[k] for k in KK_META}}
        g['ketua'] = short(spec['ketua'])
        g['anggota'] = [short(n) for n in spec.get('anggota', [])]
        groups.append(g)

    theses = []
    for line in open(path, encoding='utf-8'):
        o = json.loads(line)
        advisors = list(dict.fromkeys(canonical(a) for a in o['advisors']))
        theses.append({
            'no': str(o['no']),
            'judul': o['judul'],
            'url': o['url'],
            'author': o['author'],
            'advisors': advisors,
            'year': o['year'],
            'angkatan': angkatan_from_nim(o.get('nim')),
            'subject': o['subject'],
            'keywords_official': o['keywords_official'],
            'has_abstract': str(o['no']) in abstracts,
            'perlu_review': o['perlu_review'],
            'review_reasons': o['review_reasons'],
            'memberships': [
                {'slug': m['slug'], 'role': m['role'], 'score': m['score'],
                 'keywords': m['keywords'], 'advisors': m['advisors']}
                for m in o['memberships']
            ],
        })
    out = ROOT / 'web' / 'data' / 'thesis-data.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    generated = date.today().isoformat()
    if out.exists():                       # isi sama -> pertahankan tanggal lama (tidak ada diff palsu)
        try:
            prev = json.load(open(out, encoding='utf-8'))
            if prev.get('groups') == groups and prev.get('theses') == theses:
                generated = prev.get('generated', generated)
        except (ValueError, OSError):
            pass
    with open(out, 'w', encoding='utf-8') as f:
        json.dump({'generated': generated, 'groups': groups, 'theses': theses},
                  f, ensure_ascii=False, separators=(',', ':'))
    with open(out.parent / 'abstracts.json', 'w', encoding='utf-8') as f:
        json.dump(abstracts, f, ensure_ascii=False, separators=(',', ':'), sort_keys=True)
    h = hashlib.sha1(json.dumps([groups, theses, abstracts], sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()[:8]
    sw = ROOT / 'web' / 'sw.js'
    if sw.exists():
        old = sw.read_text(encoding='utf-8')
        new = bump_sw_cache(old, h)
        if new != old:
            sw.write_text(new, encoding='utf-8')
    print(f'{len(theses)} tesis -> {out}')
    print(f'{len(abstracts)} abstrak -> {out.parent / "abstracts.json"}')


if __name__ == '__main__':
    main()
