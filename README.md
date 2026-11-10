# thesis-tmi

Katalog tesis Teknik dan Manajemen Industri ITB (S2), dikelompokkan per Kelompok Keahlian (KK).
Situs berupa PWA statis; datanya dibangun dari digilib ITB.

Klasifikasi memakai empat sinyal: **dosen pembimbing** (peta dosen -> KK di `config/kk.yaml` dan
`config/dosen_lain.yaml`), **kata kunci resmi** digilib dan **abstrak** (keduanya dipelajari dari
tesis lain yang dosennya ber-KK, leave-one-out), dan **judul** (aturan kata kunci lama, bobot nyaris
nol). Hasilnya skor per KK, jadi satu tesis bisa punya KK utama dan KK kedua.

## Struktur

```
.github/workflows/
  deploy-pages.yml      # menyajikan web/ lewat GitHub Pages (otomatis saat web/ berubah di main)
  update-data.yml       # pembaruan data berkala (2 bulanan) -> membuka Pull Request
  ci.yml                # tes pada tiap push / PR
config/
  halaman_rusak.txt     # halaman Digilib yang rusak (500) dan dilewati saat unduh
  kk.yaml               # KK: label, warna, ketua & anggota resmi (sumber kebenaran dosen -> KK)
  dosen_lain.yaml       # dosen yang KK-nya tidak eksplisit (dgn tingkat 'yakin') & dosen 'tanpa_kk'
  advisor_aliases.yaml  # variasi penulisan nama dosen di digilib -> nama kanonik
scripts/
  crawl_list.py         # 1. list prodi (57 halaman) -> data/list.jsonl
  fetch_detail.py       # 2. unduh halaman detail -> data/raw/ (bisa dilanjutkan)
  parse_detail.py       # 3. parse detail -> data/theses.jsonl
  classify_thesis.py    # 4. klasifikasi -> data/classified.jsonl, data/unmapped_advisors.txt
  build_site.py         # 5. -> web/data/thesis-data.json + abstracts.json
  check_data.py         # pengaman + ringkasan sebelum data baru dipublikasikan
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

## Hosting dan pembaruan otomatis

Situs murni statis (tidak ada langkah build di sisi situs): cukup sajikan folder `web/`. Semua path relatif,
jadi sama persis berjalan di `user.github.io/thesis-tmi/` (sub-path) maupun di root domain.

### GitHub Pages (sekali setup)

1. Push repo ke GitHub (branch `main`).
2. **Settings -> Pages -> Build and deployment -> Source: GitHub Actions**.
3. **Settings -> Actions -> General -> Workflow permissions**: pilih *Read and write permissions* dan
   centang *Allow GitHub Actions to create and approve pull requests* (dibutuhkan `update-data.yml`).
4. Tab **Actions -> Deploy ke GitHub Pages -> Run workflow** untuk deploy pertama. Alamat situs tampil di
   ringkasan job. Setelah itu deploy berjalan sendiri tiap `web/` berubah di `main`.

### Pembaruan data berkala

`update-data.yml` jalan **tanggal 1 tiap 2 bulan** (Jan, Mar, Mei, Jul, Sep, Nov; 09:00 WIB) dan bisa dipicu
manual (**Actions -> Perbarui data tesis -> Run workflow**; centang *refetch_all* untuk mengunduh ulang semua
halaman detail). Alurnya: tes -> `crawl_list --refresh` -> `fetch_detail` -> `parse_detail` -> `classify_thesis`
-> `build_site` -> `check_data` -> **Pull Request** berisi perubahan `web/data/`. Situs baru berubah setelah
PR itu kamu **merge**, yang memicu deploy.

- `check_data.py` memblokir PR bila jumlah tesis turun >2%, abstrak turun >10%, atau ada tesis tanpa judul/URL
  (tanda crawl rusak). Ringkasan (jumlah, tesis baru, dosen yang belum ter-map) ada di isi PR.
- Bila ada dosen baru di daftar "belum ter-map", tambahkan ke `config/kk.yaml` atau `config/dosen_lain.yaml`,
  jalankan pipeline lokal, lalu commit.
- Tanpa perubahan data, tidak ada diff, jadi tidak ada PR (tanggal dan versi cache dipertahankan).
- Cache halaman detail dibuang GitHub bila 7 hari tak dipakai, jadi pada jadwal 2 bulanan biasanya semua halaman
  diunduh ulang (+-45 menit). Itu normal. Halaman di `config/halaman_rusak.txt` dilewati.

Catatan yang perlu diketahui:

- GitHub **menonaktifkan workflow terjadwal di repo publik setelah 60 hari tanpa aktivitas**. Selang antar
  jadwal 2 bulanan adalah 59-62 hari, jadi bila PR tidak segera di-merge dan tidak ada commit lain,
  jadwal bisa mati. GitHub mengirim email peringatan; klik *Enable workflow* di tab Actions, atau jalankan
  manual. Merge PR tepat waktu (atau commit apa pun) mereset hitungan itu.
- Server Digilib bisa saja membatasi/menolak IP datacenter GitHub. Bila `crawl_list` gagal di Actions,
  jalankan pipeline di laptop (`scripts/` berjalan lokal sama persis), commit hasilnya, dan biarkan
  `deploy-pages.yml` yang menyajikannya.
- PR otomatis memakai `GITHUB_TOKEN`, sehingga tidak memicu `ci.yml`; tesnya sudah dijalankan di dalam
  `update-data.yml`.
- Nomor `no` mengikuti urutan Digilib (terbaru di atas), jadi bergeser tiap ada tesis baru; bukan ID permanen.

### Cloudflare Pages

Tidak perlu workflow. Di dashboard Cloudflare: **Workers & Pages -> Create -> Pages -> Connect to Git** ->
pilih repo -> *Framework preset*: **None**, *Build command*: kosong, *Build output directory*: **`web`**,
*Production branch*: `main` -> **Save and Deploy**. Tiap push ke `main` (termasuk merge PR data) otomatis
di-deploy, dan tiap PR mendapat alamat *preview* sehingga hasil pembaruan data bisa dilihat sebelum di-merge.
Boleh memakai GitHub Pages dan Cloudflare Pages berbarengan; keduanya independen.

## Lisensi

CC0 1.0, lihat `LICENSE`.
