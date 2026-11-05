# thesis-tmi

Katalog tesis Teknik dan Manajemen Industri ITB (S2), dikelompokkan per Kelompok Keahlian (KK).
Situs berupa PWA statis; datanya dibangun dari digilib ITB.

Klasifikasi memakai tiga sinyal: **dosen pembimbing** (peta dosen -> KK di `config/kk.yaml`),
**kata kunci resmi** digilib (dipelajari dari tesis lain yang dosennya ber-KK), dan **judul**
(aturan kata kunci lama, sebagai sinyal cadangan). Hasilnya skor per KK, jadi satu tesis
bisa punya KK utama dan KK kedua.

## Struktur

```
config/
  kk.yaml               # KK: label, warna, ketua & anggota (sumber kebenaran dosen -> KK)
  advisor_aliases.yaml  # variasi penulisan nama dosen di digilib -> nama kanonik
scripts/
  crawl_list.py         # 1. list prodi (57 halaman) -> data/list.jsonl
  fetch_detail.py       # 2. unduh halaman detail -> data/raw/ (bisa dilanjutkan)
  parse_detail.py       # 3. parse detail -> data/theses.jsonl
  classify_thesis.py    # 4. klasifikasi -> data/classified.jsonl, data/unmapped_advisors.txt
  build_site.py         # 5. -> web/data/thesis-data.json
  names.py, title_keywords.py, common.py   # modul pendukung
tests/                  # python -m unittest discover -s tests
web/                    # situs statis (deploy folder ini)
data/                   # hasil scraping/klasifikasi (tidak di-commit)
```

## Menjalankan pipeline (dari root repo)

```
pip install -r requirements.txt
python scripts/crawl_list.py
python scripts/fetch_detail.py
python scripts/parse_detail.py
python scripts/classify_thesis.py
python scripts/build_site.py
```

Setelah `classify_thesis.py`, cek `data/unmapped_advisors.txt`: dosen yang belum ada di
`config/kk.yaml` (tambahkan) dan pencocokan nama otomatis yang perlu dipastikan (tambahkan
ke `advisor_aliases.yaml` bila salah). Bobot dan ambang ada di bagian konfigurasi
`scripts/classify_thesis.py`. Untuk melihat alasan klasifikasi satu tesis:
`python scripts/classify_thesis.py --explain "sebagian judul"`.

Situs lokal: `python -m http.server 8000 --directory web`

## Lisensi

CC0 1.0, lihat `LICENSE`.
