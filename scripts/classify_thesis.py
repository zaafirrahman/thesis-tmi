"""Klasifikasi tesis ke Kelompok Keahlian (KK) dari tiga sinyal:

  1. dosen   : KK dosen pembimbing (config/kk.yaml)             -> bobot 0.50
  2. keyword : kata kunci resmi digilib; tiap kata kunci dipetakan ke KK dari
               tesis LAIN (leave-one-out) yang dibimbing dosen ber-KK   -> 0.35
  3. judul   : kecocokan kata kunci pada judul (aturan v2 lama)   -> 0.15

Sinyal yang tidak tersedia dibuang & bobot sisanya dinormalisasi ulang. Hasil
akhir berupa skor per KK (jumlah 1). KK utama = skor tertinggi; KK kedua muncul
bila skornya >= SECOND_MIN, walau berbeda dari KK dosen.

Pakai:  python scripts/classify_thesis.py [--explain KATA_DI_JUDUL]
Output: data/classified.jsonl, data/unmapped_advisors.txt
"""
import argparse
import json
import math
import re
import sys
from collections import Counter, defaultdict

from common import DATA
from names import LecturerIndex, extract_advisor_names, load_aliases, load_kk, name_key
from title_keywords import score_title

# ---- konfigurasi (silakan di-tuning) --------------------------------------
WEIGHTS = {'dosen': 0.50, 'keyword': 0.35, 'title': 0.15}
SECOND_MIN = 0.25        # skor minimum KK kedua
REVIEW_MARGIN = 0.15     # selisih skor 1-2 di bawah ini -> perlu_review
KW_MIN_SUPPORT = 1.0     # minimal "dukungan" dari tesis lain agar keyword dipakai
KW_PRIOR = 2.0           # kekuatan prior (distribusi KK global) pada estimasi keyword
PHRASE_W, TOKEN_W = 1.0, 0.6
STOPWORDS = {
    'dan', 'yang', 'di', 'dengan', 'untuk', 'pada', 'dalam', 'studi', 'kasus',
    'model', 'sistem', 'analisis', 'penelitian', 'pengembangan', 'metode',
    'the', 'of', 'and', 'for', 'in', 'based', 'using', 'analysis', 'system',
    'systems', 'case', 'study', 'design', 'approach', 'pt',
}
# ---------------------------------------------------------------------------


def norm_kw(k):
    return ' '.join(k.lower().split()).rstrip('. ;')


def units_of(keyword):
    """Satu kata kunci -> [(unit, bobot)]: frasa utuh + kata penyusunnya."""
    phrase = norm_kw(keyword)
    out = [('p:' + phrase, PHRASE_W)]
    for w in re.findall(r'[a-z0-9]+', phrase):
        if len(w) > 2 and w not in STOPWORDS:
            out.append(('w:' + w, TOKEN_W))
    return out


def normalize(vec):
    tot = sum(vec.values())
    return {k: v / tot for k, v in vec.items()} if tot > 0 else {}


def advisor_vector(adv_matches):
    """adv_matches: [(raw, key, [slug], metode)] -> vektor KK (jumlah 1) atau None."""
    vec = defaultdict(float)
    n = 0
    for _raw, _key, slugs, _m in adv_matches:
        if not slugs:
            continue
        n += 1
        for s in slugs:
            vec[s] += 1.0 / len(slugs)
    if n == 0:
        return None
    return {k: v / n for k, v in vec.items()}


class Profiles:
    def __init__(self, recs, slugs):
        self.slugs = slugs
        self.N = len(recs)
        self.counts = defaultdict(lambda: defaultdict(float))
        self.df = Counter()
        prior = defaultdict(float)
        for r in recs:
            for u in r['units']:
                self.df[u] += 1
                if r['D']:
                    for k, v in r['D'].items():
                        self.counts[u][k] += v
            if r['D']:
                for k, v in r['D'].items():
                    prior[k] += v
        tot = sum(prior.values()) or 1.0
        self.prior = {s: (prior.get(s, 0.0) / tot) or 1e-6 for s in slugs}

    def idf(self, u):
        return max(0.0, math.log(self.N / self.df[u])) if self.df[u] else 0.0

    def unit_stats(self, rec):
        """Estimasi P(KK|unit) leave-one-out untuk tiap unit milik tesis ini."""
        stats = {}
        for u in rec['units']:
            other = {s: self.counts[u].get(s, 0.0) for s in self.slugs}
            if rec['D']:
                for k, v in rec['D'].items():
                    other[k] = max(0.0, other[k] - v)
            n = sum(other.values())
            if n < KW_MIN_SUPPORT:
                continue
            p = {s: (other[s] + KW_PRIOR * self.prior[s]) / (n + KW_PRIOR) for s in self.slugs}
            w = self.idf(u) * rec['units'][u] * n / (n + KW_PRIOR)
            if w > 0:
                stats[u] = (p, w)
        return stats


def keyword_signal(rec, prof):
    """Return (vektor KK atau None, {slug:[keyword]})."""
    stats = prof.unit_stats(rec)
    if not stats:
        return None, {}
    agg = defaultdict(float)
    wsum = sum(w for _, w in stats.values())
    for p, w in stats.values():
        for s, v in p.items():
            agg[s] += w * v / wsum
    # keyword mana yang condong ke KK mana (untuk chip di UI)
    by_kk = defaultdict(list)
    for kw in rec['keywords']:
        kv, kw_w = defaultdict(float), 0.0
        for u, _uw in units_of(kw):
            if u in stats:
                p, w = stats[u]
                kw_w += w
                for s, v in p.items():
                    kv[s] += w * v
        if kw_w > 0:
            best = max(kv, key=kv.get)
            by_kk[best].append(kw)
    return normalize(agg), by_kk


def prepare(records, lecturers):
    recs = []
    for r in records:
        advisors = extract_advisor_names(r['advisors'])
        matches = [(raw,) + lecturers.match(raw) for raw in advisors]
        units = {}
        for kw in r['keywords']:
            for u, w in units_of(kw):
                units[u] = max(w, units.get(u, 0))
        recs.append({**r, 'advisors': advisors, 'matches': matches, 'D': advisor_vector(matches), 'units': units})
    return recs


def classify_one(rec, prof):
    sig = {}
    if rec['D']:
        sig['dosen'] = rec['D']
    kvec, kw_by_kk = keyword_signal(rec, prof)
    if kvec:
        sig['keyword'] = kvec
    title = {s: sc for s, (sc, _h) in score_title(rec['title']).items()}
    title_hits = {s: h for s, (_sc, h) in score_title(rec['title']).items()}
    if title:
        sig['title'] = normalize(title)

    reasons = []
    if rec['advisors'] and not rec['D']:
        reasons.append('dospem belum ter-map ke KK')
    if not rec['advisors']:
        reasons.append('tidak ada data dospem')
    if not rec['keywords']:
        reasons.append('kata kunci kosong')

    # skor berbasis KONTEN saja (kata kunci + judul, tanpa dosen): dipakai untuk menyarankan
    # KK dosen yang belum ter-map
    cw = {k: WEIGHTS[k] for k in ('keyword', 'title') if k in sig}
    content = {}
    if cw:
        ctot = sum(cw.values())
        for sname, w in cw.items():
            for k, v in sig[sname].items():
                content[k] = content.get(k, 0.0) + w / ctot * v

    if not sig:
        return [], True, reasons + ['tidak ada sinyal sama sekali'], content

    wsum = sum(WEIGHTS[s] for s in sig)
    score = defaultdict(float)
    for s, vec in sig.items():
        for k, v in vec.items():
            score[k] += WEIGHTS[s] / wsum * v
    ranked = sorted(score.items(), key=lambda x: x[1], reverse=True)

    chosen = [ranked[0]]
    if len(ranked) > 1 and ranked[1][1] >= SECOND_MIN:
        chosen.append(ranked[1])
    margin = ranked[0][1] - (ranked[1][1] if len(ranked) > 1 else 0.0)
    if margin < REVIEW_MARGIN:
        reasons.append('skor KK 1 dan 2 berdekatan')
    if set(sig) == {'title'}:
        reasons.append('hanya sinyal judul')

    adv_by_kk = defaultdict(list)
    for raw, _key, slugs, _m in rec['matches']:
        for s in slugs:
            adv_by_kk[s].append(raw)
    memberships = []
    for i, (slug, sc) in enumerate(chosen):
        kws = list(dict.fromkeys(kw_by_kk.get(slug, []) + title_hits.get(slug, [])))
        memberships.append({
            'slug': slug,
            'role': 'utama' if i == 0 else 'sekunder',
            'score': round(sc * 100),
            'keywords': kws,
            'advisors': adv_by_kk.get(slug, []),
            'signals': {s: round(sig[s].get(slug, 0.0), 3) for s in sig},
        })
    return memberships, bool(reasons), reasons, content


def run(records, kk, aliases=None):
    lect = LecturerIndex(kk, aliases)
    recs = prepare(records, lect)
    prof = Profiles(recs, list(kk))
    out = []
    for r in recs:
        m, review, reasons, content = classify_one(r, prof)
        out.append({
            'id': r['id'], 'no': r['no'], 'url': r['url'], 'judul': r['title'],
            'author': r['author'], 'nim': r['nim'], 'advisors': r['advisors'],
            'year': r['year'], 'subject': r['subject'],
            'keywords_official': r['keywords'],
            'memberships': m, 'perlu_review': review, 'review_reasons': reasons,
            'content': {k: round(v, 3) for k, v in content.items()},
        })
    return out, recs, lect


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--explain', help='tampilkan rincian tesis yang judulnya mengandung teks ini')
    args = ap.parse_args()
    path = DATA / 'theses.jsonl'
    if not path.exists():
        sys.exit('data/theses.jsonl belum ada. Jalankan parse_detail.py dulu.')
    records = [json.loads(l) for l in open(path, encoding='utf-8')]
    kk = load_kk()
    out, recs, lect = run(records, kk, load_aliases())

    with open(DATA / 'classified.jsonl', 'w', encoding='utf-8') as f:
        for o in out:
            f.write(json.dumps(o, ensure_ascii=False) + '\n')

    # ---- laporan dosen: belum ter-map digabung PER ORANG (ejaan berbeda -> satu baris) ----
    groups = {}   # (token pertama, token terakhir) -> {'theses': set(id), 'variants': Counter}
    fuzzy = Counter()
    for r in recs:
        for raw, key, slugs, method in r['matches']:
            if method == 'unmapped':
                toks = name_key(raw).split()
                g = groups.setdefault((toks[0][0], toks[-1]) if toks else ('', ''),   # inisial depan + nama belakang
                                      {'theses': set(), 'variants': Counter()})
                g['theses'].add(r['id'])
                g['variants'][raw] += 1
            elif method in ('subset', 'fuzzy'):
                fuzzy[f'{raw}  ->  {lect.display[key]}  [{method}]'] += 1
    people = sorted(groups.values(), key=lambda g: -len(g['theses']))
    content_by_id = {o['id']: o['content'] for o in out}

    def suggest(g):
        tot, n = Counter(), 0
        for tid in g['theses']:
            c = content_by_id.get(tid)
            if c:
                n += 1
                for k, v in c.items():
                    tot[k] += v
        if not n:
            return 'tanpa sinyal konten'
        top = [(k, v) for k, v in tot.most_common(2) if v > 0]
        s_all = sum(tot.values()) or 1.0
        return 'saran dari konten tesis: ' + ', '.join(f"{kk[k]['abbr']} {v / s_all:.0%}" for k, v in top) + f' (n={n})'

    lines = ['# 1. Dosen BELUM ada di config/kk.yaml, digabung per orang (jumlah tesis)',
             '#    Salin baris yang sesuai ke KK yang benar di kk.yaml (kolom anggota).',
             '#    "saran" = KK yang dipilih sistem untuk tesis-tesisnya dari kata kunci+judul (BUKAN dari dosen);',
             '#    pakai sebagai petunjuk, putuskan sendiri.']
    for g in people:
        disp = max(g['variants'], key=lambda v: (len(v), v))
        lines.append(f'{len(g["theses"]):4d}  - "{disp}"   # {len(g["variants"])} ejaan | {suggest(g)}')
    lines += ['', '# 2. Dicocokkan otomatis (subset/fuzzy) - pastikan benar; kalau salah tambahkan ke advisor_aliases.yaml']
    lines += [f'{n:4d}  {name}' for name, n in fuzzy.most_common()]
    (DATA / 'unmapped_advisors.txt').write_text('\n'.join(lines), encoding='utf-8')

    reasons = Counter(x for o in out for x in o['review_reasons'])
    combos = Counter('+'.join(sorted(o['memberships'][0]['signals'])) for o in out if o['memberships'])

    n = len(out)
    cls = sum(1 for o in out if o['memberships'])
    multi = sum(1 for o in out if len(o['memberships']) > 1)
    rev = sum(1 for o in out if o['perlu_review'])
    with_adv = sum(1 for r in recs if r['D'])
    print(f'{n} tesis | terklasifikasi {cls} | 2 KK {multi} | perlu review {rev}')
    print(f'Tesis dgn dospem ter-map: {with_adv}/{n} | dosen belum ter-map: {len(people)} orang')
    print('Per KK (utama):', dict(Counter(o['memberships'][0]['slug'] for o in out if o['memberships'])))
    print('Alasan perlu_review:', dict(reasons.most_common()))
    print('Kombinasi sinyal (KK utama):', dict(combos.most_common()))
    print('Dosen belum ter-map teratas:', [(max(g['variants'], key=len)[:32], len(g['theses'])) for g in people[:8]])
    print('Detail: data/unmapped_advisors.txt, data/classified.jsonl')

    if args.explain:
        q = args.explain.lower()
        for o in out:
            if q in (o['judul'] or '').lower():
                print('\n' + o['judul'])
                print('  dospem:', o['advisors'], '| keyword:', o['keywords_official'])
                for m in o['memberships']:
                    print(f"  {m['role']:6s} {m['slug']} skor={m['score']} sinyal={m['signals']} kw={m['keywords']}")
                print('  review:', o['review_reasons'])


if __name__ == '__main__':
    main()
