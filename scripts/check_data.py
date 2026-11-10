"""Pengaman + ringkasan sebelum data baru dipublikasikan.

Membandingkan web/data/thesis-data.json (hasil build) dengan versi di git HEAD:
 - GAGAL (exit 1) bila jumlah tesis turun >2%, abstrak turun >10%, atau ada tesis tanpa judul/url
   (tanda crawl rusak, mis. Digilib sedang error atau struktur HTML berubah);
 - menulis ringkasan Markdown ke data/pr_body.md dan $GITHUB_STEP_SUMMARY.

Pakai:  python scripts/check_data.py
"""
import json
import os
import subprocess
import sys

from common import DATA, ROOT


def compare(new, old):
    nt, ot = new['theses'], (old or {}).get('theses', [])
    nu, ou = {t['url'] for t in nt}, {t['url'] for t in ot}
    return {
        'total_new': len(nt), 'total_old': len(ot),
        'added': [t for t in nt if t['url'] not in ou] if old else [],
        'removed': [t for t in ot if t['url'] not in nu],
        'abs_new': sum(1 for t in nt if t['has_abstract']), 'abs_old': sum(1 for t in ot if t['has_abstract']),
        'review': sum(1 for t in nt if t['perlu_review']),
    }


def problems(new, c, have_old=True):
    out = []
    bad = [t for t in new['theses'] if not t.get('judul') or not t.get('url')]
    if bad:
        out.append(f'{len(bad)} tesis tanpa judul/url')
    if have_old and c['total_new'] < 0.98 * c['total_old']:
        out.append(f"jumlah tesis turun {c['total_old']} -> {c['total_new']} (>2%)")
    if have_old and c['abs_new'] < 0.90 * c['abs_old']:
        out.append(f"jumlah abstrak turun {c['abs_old']} -> {c['abs_new']} (>10%)")
    if c['total_new'] == 0:
        out.append('tidak ada tesis')
    return out


def summary(c, probs, unmapped_top):
    L = ['## Pembaruan data katalog tesis TMI', '',
         f"- Tesis: **{c['total_new']}** (sebelumnya {c['total_old']}, **+{len(c['added'])}** baru, -{len(c['removed'])} hilang)",
         f"- Abstrak layak baca: {c['abs_new']} (sebelumnya {c['abs_old']})",
         f"- Perlu ditinjau ulang: {c['review']}"]
    if probs:
        L += ['', '### PERINGATAN (pembaruan diblokir)'] + [f'- {p}' for p in probs]
    if c['added']:
        L += ['', '### Tesis baru (maks. 15)'] + [f"- {t['judul'][:95]}" for t in c['added'][:15]]
    if unmapped_top:
        L += ['', '### Dosen BELUM ada di config/kk.yaml / dosen_lain.yaml (tambahkan lalu jalankan ulang bila perlu)'] + [f'- {u}' for u in unmapped_top]
    L += ['', 'Periksa diff `web/data/` lalu merge agar situs diperbarui.']
    return '\n'.join(L) + '\n'


def main():
    path = ROOT / 'web' / 'data' / 'thesis-data.json'
    new = json.load(open(path, encoding='utf-8'))
    try:
        old = json.loads(subprocess.run(['git', 'show', 'HEAD:web/data/thesis-data.json'], cwd=ROOT, check=True,
                                        capture_output=True, text=True, encoding='utf-8').stdout)
    except Exception:  # noqa: BLE001  (belum ada di git / bukan repo git)
        old = None
    c = compare(new, old)
    probs = problems(new, c, have_old=old is not None)
    unmapped = []
    up = DATA / 'unmapped_advisors.txt'
    if up.exists():
        for line in up.read_text(encoding='utf-8').splitlines():
            if line.startswith('# 2.'):
                break
            if line.strip() and not line.startswith('#'):
                unmapped.append(line.strip())
    md = summary(c, probs, unmapped[:8])
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / 'pr_body.md').write_text(md, encoding='utf-8')
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as f:
            f.write(md)
    print(md)
    if probs:
        sys.exit('DIBLOKIR: ' + '; '.join(probs))


if __name__ == '__main__':
    main()
