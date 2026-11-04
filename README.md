# thesis-tmi

Katalog tesis Teknik dan Manajemen Industri ITB, dikelompokkan per kelompok keilmuan (KK). Berupa PWA statis.

## Struktur

```
scripts/
  scrape_titles.py      # scrape daftar judul dari digilib.itb.ac.id -> data/*.csv
  classify_thesis.py    # klasifikasi judul ke KK -> data/tesis_by_specialization_v2/
web/                    # situs statis (deploy folder ini)
  index.html
  css/style.css
  js/app.js             # render katalog
  js/register-sw.js     # registrasi service worker
  data/thesis-data.json # data yang dibaca situs
  img/                  # ikon PWA & logo
  manifest.json
  sw.js
```

## Menjalankan

Situs (dari root repo):

```
python -m http.server 8000 --directory web
```

Scraping & klasifikasi (jalankan dari root repo; hasil masuk ke `data/`, tidak di-commit):

```
pip install -r requirements.txt
python scripts/scrape_titles.py
python scripts/classify_thesis.py
```

## Lisensi

CC0 1.0, lihat `LICENSE`.
