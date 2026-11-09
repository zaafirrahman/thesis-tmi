"""Evaluasi sinyal KONTEN (kata kunci, abstrak, judul) terhadap KK dosen resmi.

Pseudo-kebenaran: tesis yang semua dospemnya dosen resmi (yakin=1) di SATU KK. Statistik
kata kunci/abstrak dihitung leave-one-out, jadi tesis yang dinilai tidak ikut "mengajari".
Dipakai untuk menentukan bobot di classify_thesis.py. Jalankan ulang setelah data/KK berubah.

Pakai:  python scripts/evaluate_signals.py
"""
import collections
import json
import random

import classify_thesis as ct
from common import DATA
from names import LecturerIndex, load_aliases, load_extra, load_kk
from title_keywords import score_title


def main():
    records = [json.loads(l) for l in open(DATA / 'theses.jsonl', encoding='utf-8')]
    kk = load_kk()
    lect = LecturerIndex(kk, load_aliases(), load_extra())
    recs = ct.prepare(records, lect)
    prof = ct.Profiles(recs, list(kk))

    def lift(v):
        return ct.normalize({k: x / prof.prior[k] for k, x in v.items()}) if v else None

    S = {}
    for r in recs:
        D = r['D']
        if not D or r['R'] < 1.0:
            continue
        t = max(D, key=D.get)
        if D[t] != 1.0:
            continue
        kv, _ = ct.keyword_signal(r, prof)
        av = ct.abstract_signal(r, prof)          # sudah ternormalisasi-lift
        ti = score_title(r['title'])
        S[r['id']] = dict(t=t, k=kv, a=av,
                          ti=ct.normalize({s: sc for s, (sc, _) in ti.items()}) if ti else None)

    def accuracy(parts, ids):
        n = c = 0
        for i in ids:
            d, agg, w = S[i], collections.defaultdict(float), 0
            for key, wt in parts:
                if d[key]:
                    w += wt
                    for k, x in d[key].items():
                        agg[k] += wt * x
            if w:
                n += 1
                c += max(agg, key=agg.get) == d['t']
        return (c / n if n else 0.0), n

    ids = list(S)
    random.Random(3).shuffle(ids)
    A, B = ids[:len(ids) // 2], ids[len(ids) // 2:]
    print(f'Tesis evaluasi (dosen resmi, 1 KK): {len(ids)}')
    print(f'{"kombinasi (bobot kw : abstrak : judul)":44s} {"semua":>7s} {"lipat A":>8s} {"lipat B":>8s}')
    cases = [('kata kunci saja', [('k', 1)]), ('abstrak saja', [('a', 1)]), ('judul saja', [('ti', 1)]),
             ('LAMA   (kw .35 + judul .15, tanpa abstrak)', [('k', .35), ('ti', .15)]),
             ('BARU   (1 : 2.5 : 0.05)', [('k', 1), ('a', 2.5), ('ti', .05)])]
    cases += [(f'grid   (1 : {a} : {t})', [('k', 1), ('a', a), ('ti', t)])
              for a in (1, 2, 2.5, 3) for t in (0, .05, .1, .3)]
    for name, parts in cases:
        al, n = accuracy(parts, ids)
        print(f'{name:44s} {al:7.1%} {accuracy(parts, A)[0]:8.1%} {accuracy(parts, B)[0]:8.1%}   (n={n})')


if __name__ == '__main__':
    main()
