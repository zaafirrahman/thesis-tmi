# thesis-tmi

Katalog tesis Teknik dan Manajemen Industri ITB (S2), dikelompokkan per Kelompok Keahlian (KK).
Situs berupa PWA statis; datanya dibangun dari digilib ITB.

Klasifikasi memakai empat sinyal: **dosen pembimbing** (peta dosen -> KK di `config/kk.yaml` dan
`config/dosen_lain.yaml`), **kata kunci resmi** digilib dan **abstrak** (keduanya dipelajari dari
tesis lain yang dosennya ber-KK, leave-one-out), dan **judul** (aturan kata kunci lama, bobot nyaris
nol). Hasilnya skor per KK, jadi satu tesis bisa punya KK utama dan KK kedua.

## Struktur

```
config/
  kk.yaml               # KK: label, warna, ketua & anggota resmi (sumber kebenaran dosen -> KK)
  dosen_lain.yaml       # dosen yang KK-nya tidak eksplisit (dgn tingkat 'yakin') & dosen 'tanpa_kk'
  advisor_aliases.yaml  # variasi penulisan nama dosen di digilib -> nama kanonik
scripts/
  crawl_list.py         # 1. list prodi (57 halaman) -> data/list.jsonl
  fetch_detail.py       # 2. unduh halaman detail -> data/raw/ (bisa dilanjutkan)
  parse_detail.py       # 3. parse detail -> data/theses.jsonl
  classify_thesis.py    # 4. klasifikasi -> data/classified.jsonl, data/unmapped_advisors.txt
  build_site.py         # 5. -> web/data/thesis-data.json + abstracts.json
  evaluate_signals.py   # mengukur akurasi tiap sinyal (dasar bobot di classify_thesis.py)
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

## Kalibrasi bobot

`python scripts/evaluate_signals.py` menilai sinyal konten (tanpa dosen) terhadap KK dosen resmi,
memakai tesis yang semua dospemnya dosen resmi di satu KK (n = 852; statistik dihitung
leave-one-out; uji silang 2-lipat). Hasil terakhir:

| sinyal | akurasi |
|---|---|
| judul saja | 54,9% |
| abstrak saja (dengan normalisasi kelas) | 65,3% |
| kata kunci saja | 69,2% |
| lama: kata kunci .35 + judul .15 | 64,1% |
| **baru: kata kunci : abstrak : judul = 1 : 2,5 : 0,05** | **75,5%** (lipat A 75,8%, lipat B 75,2%) |

Temuan: sinyal judul justru merusak campuran, dan normalisasi bias ukuran kelas (bagi dengan prior KK)
menolong abstrak tetapi merugikan kata kunci. Ambang KK kedua diturunkan ke 0,20 setelah judul
dikecilkan. Ini akurasi terhadap *KK dosen*, bukan terhadap penilaian KK atas tesisnya.
Jalankan ulang skrip itu setiap data atau daftar dosen berubah.

Situs lokal: `python -m http.server 8000 --directory web`

## Lisensi

CC0 1.0, lihat `LICENSE`.
