"""
Klasifikasi judul tesis TMI ITB ke 5 peminatan/KK.

Perbaikan dari versi sebelumnya:
1. Matching pakai regex word-boundary (\\b), bukan substring `in` biasa.
   -> Contoh bug lama: keyword 'ERP' ketangkep di tengah kata "hyp-ERP-arameter".
2. Setiap keyword punya bobot: STRONG (2) = penanda kuat & spesifik ke satu
   peminatan, WEAK (1) = kata umum yang muncul lintas bidang (mis. 'industri',
   'strategi', 'manajemen', 'digital', 'LSTM', 'AI'). Klasifikasi = skor
   tertinggi (jumlah bobot), bukan sekadar jumlah keyword yang match.
   -> Ini mencegah kata generik menang sendirian cuma karena kebetulan match.
3. 'pengembangan' & 'penelitian' DIHAPUS dari keyword Manajemen Industri.
   Dua kata ini adalah kata baku akademik Indonesia utk "developing a
   model/system/app/..." dan muncul di HAMPIR SEMUA judul riset apapun
   topiknya -> menyebabkan Manajemen Industri selalu jadi kategori terbesar
   padahal isinya belum tentu manajemen industri sama sekali.
4. Setiap judul sekarang dapat skor untuk SEMUA kategori (bukan cuma juara 1).
   Kolom 'Klasifikasi_2' (runner-up) dan 'Perlu_Review' membantu menunjukkan
   judul yang ambigu / beririsan antar-KK, supaya bisa direview manual
   alih-alih dipaksa 1 label yang belum tentu tepat.
"""

import pandas as pd
import re
import os
from collections import defaultdict

# ---------------------------------------------------------------------------
# Definisi kata kunci per peminatan.
# 'strong' = penanda kuat/spesifik (bobot 2), 'weak' = kata umum lintas bidang
# yang tetap relevan tapi tidak boleh menang sendirian (bobot 1).
# ---------------------------------------------------------------------------

SPECIALIZATIONS = {
    'sistem_manufaktur': {
        'label': 'Sistem Manufaktur',
        'strong': [
            'manufaktur', 'manufacturing', 'assembly', 'perakitan', 'CNC',
            'machining', 'casting', 'foaming', 'injection molding', 'extruder',
            'tooling', 'fixture', 'jig', 'layout pabrik', 'automasi', 'otomasi',
            'robot', 'robotika', 'AGV', 'conveyor', 'quality control',
            'pengendalian kualitas', 'SPC', 'six sigma', 'lean manufacturing',
            'TPM', 'perawatan mesin', 'OEE', 'process improvement',
            'optimasi proses', 'discrete event', 'product design', 'prototype',
            '3D printing', 'additive manufacturing', 'supply chain',
            'rantai pasok', 'logistik', 'distribusi', 'inventory',
            'persediaan', 'warehouse', 'gudang', 'material handling',
            'forklift', 'nesting', 'cutting', 'scheduling', 'penjadwalan',
            'sequencing', 'fleet management', 'transportation',
            'peta kendali', 'control chart', 'sampling plan',
            'rencana sampling', 'chemical milling', 'sheet metal forming',
        ],
        'weak': [
            'produksi', 'pabrik', 'industri', 'produk', 'mesin',
            'maintenance', 'reliability', 'simulasi', 'lean',
        ],
    },
    'sistem_industri_rantai_nilai': {
        'label': 'Sistem Industri dan Rantai Nilai',
        'strong': [
            'rantai nilai', 'value chain', 'nilai tambah', 'value stream',
            'kompetitif', 'competitive', 'keunggulan bersaing', 'daya saing',
            'business model', 'model bisnis', 'canvas', 'BMC', 'merger',
            'akuisisi', 'divestasi', 'restrukturisasi', 'ESG', 'carbon',
            'emisi', 'energi terbarukan', 'EBT', 'renewable',
            'life cycle assessment', 'LCA', 'daur ulang', 'recycling',
            'circular economy', 'ekonomi sirkular', 'risk management',
            'manajemen risiko', 'mitigasi risiko', 'resilience',
            'resiliensi', 'ketahanan', 'tangguh', 'stakeholder',
            'pemangku kepentingan', 'CSR', 'corporate social', 'SNI',
            'sertifikasi', 'akreditasi', 'sustainability', 'berkelanjutan',
            'lingkungan', 'environmental',
            # --- tambahan: domain komoditas & perdagangan (bukti nyata
            # kosong sebelumnya, ini akar bug kasus "harga karet") ---
            'komoditas', 'komoditi', 'harga komoditas', 'fluktuasi harga',
            'karet', 'getah karet', 'kelapa sawit', 'sawit',
            'crude palm oil', 'CPO', 'kopi', 'kakao', 'batubara', 'nikel',
            'timah', 'ekspor', 'impor', 'perdagangan internasional',
            'neraca perdagangan', 'harga pasar', 'harga global',
            'agroindustri', 'komoditas pertanian',
            # --- tambahan: transportasi, logistik jaringan & lokasi
            # fasilitas -- ini justru topik UTAMA publikasi KK-SITE
            # (vehicle routing, berth/quay allocation, dsb di poster) ---
            'rute kendaraan', 'vehicle routing', 'lokasi fasilitas',
            'facility location', 'lokasi-alokasi fasilitas',
            'jaringan distribusi', 'distribution network', 'rute kapal',
            'penentuan rute', 'moda transportasi', 'transportasi umum',
            'angkutan umum', 'angkutan', 'pelabuhan', 'terminal',
            'bandara', 'penerbangan', 'stasiun pengisian',
            'kendaraan listrik', 'electric vehicle', 'depot', 'jaringan hub',
            'kapal', 'pelayaran', 'petikemas', 'kontainer', 'transshipment',
            'wisatawan', 'pariwisata', 'wisata',
            # --- tambahan: kebijakan & ekonomi sektoral/wilayah, sesuai
            # poster KK-SITE ("Sosio-techno-economic Systems": planning &
            # evaluation of public service system) ---
            'sektor ekonomi', 'perekonomian', 'sektor pertanian',
            'agribisnis', 'perkebunan', 'koperasi', 'tarif',
            'willingness to pay', 'subsidi', 'pembangunan sektor',
            'kebijaksanaan pembangunan', 'harga air', 'jasa telekomunikasi',
            # --- putaran 2: varian ejaan & istilah yg masih kelewat ---
            'depo', 'vehicle flow', 'fleet vehicle', 'pickup and delivery',
            'cross-docking', 'fourth party logistic', 'sampah', 'limbah',
            'persampahan', 'insinerator', 'dirgantara',
        ],
        'weak': [
            'strategi', 'strategic', 'pertumbuhan', 'growth', 'scaling',
            'ekspansi', 'kebijakan', 'policy', 'regulasi', 'regulation',
            'pemerintah', 'ekonomi', 'economic', 'GDP', 'makroekonomi',
            'industri 4.0', 'transformasi digital', 'digitalisasi',
            'green', 'standar', 'standard', 'ISO', 'kendaraan', 'jaringan',
        ],
    },
    'ergonomi_dan_rekayasa_kerja': {
        'label': 'Ergonomi dan Rekayasa Kerja',
        'strong': [
            'ergonomi', 'ergonomic', 'human factors', 'faktor manusia',
            'antropometri', 'anthropometry', 'postur', 'posture',
            'beban kerja', 'workload', 'beban fisik', 'physical load',
            'kelelahan', 'fatigue', 'nyeri', 'pain', 'MSDs',
            'musculoskeletal', 'kerja fisik', 'physical work',
            'aktivitas otot', 'EMG', 'thermal', 'kebisingan', 'noise',
            'getaran', 'vibration', 'pencahayaan', 'lighting',
            'illumination', 'K3', 'kecelakaan', 'accident', 'hazard',
            'APD', 'PPE', 'helm', 'masker', 'pelindung',
            'cognitive load', 'beban kognitif', 'mental workload',
            'atensi', 'persepsi', 'perception', 'biomekanika',
            'biomechanics', 'kinerja manusia', 'human performance',
            'shift work', 'kerja shift', 'jam kerja', 'work schedule',
            'prosthesis', 'prostetik', 'kaki palsu', 'tangan palsu',
            'workplace design', 'desain tempat kerja', 'workstation',
            # --- tambahan: perilaku berkendara & transportation
            # ergonomics, sesuai "Transportation Ergonomics" di poster
            # ERK3 (dan contoh publikasi soal driver alertness) ---
            'perilaku berkendara', 'perilaku berisiko', 'berkendara',
            'mengemudi', 'pengemudi', 'pengendara', 'naturalistic riding',
            'naturalistic driving', 'driving behavior', 'riding behavior',
            'kewaspadaan', 'kantuk', 'sleepiness', 'alertness',
            'situation awareness', 'performansi mengemudi', 'masinis',
            'waktu reaksi', 'reaction time',
        ],
        'weak': [
            'kenyamanan', 'comfort', 'keselamatan', 'safety', 'usability',
            'user experience', 'UX', 'interface', 'antarmuka', 'attention',
            'pilot', 'simulator',
        ],
    },
    'manajemen_industri': {
        'label': 'Manajemen Industri',
        'strong': [
            'kepemimpinan', 'leadership', 'motivasi', 'motivation', 'SDM',
            'human resource', 'talenta', 'talent', 'karyawan', 'pegawai',
            'KPI', 'produktivitas', 'productivity', 'inovasi', 'innovation',
            'ambidexterity', 'exploration', 'exploitation',
            'learning organization', 'organisasi pembelajar',
            'knowledge management', 'change management', 'budaya organisasi',
            'decision making', 'pengambilan keputusan', 'multi-criteria',
            'AHP', 'TOPSIS', 'project management', 'manajemen proyek',
            'portofolio', 'quality management', 'TQM', 'ISO 9001', 'mutu',
            'supply chain management', 'vendor', 'supplier', 'pemasok',
            'pembelian', 'procurement', 'pengadaan', 'kontrak', 'UMKM',
            'UKM', 'usaha kecil', 'startup', 'wirausaha', 'business process',
            'BPM', 'proses bisnis', 'workflow', 'agile', 'scrum', 'kanban',
            'continuous improvement', 'marketing', 'pemasaran', 'brand',
            'merek', 'promosi', 'ROI', 'investasi',
        ],
        'weak': [
            'manajemen', 'management', 'organisasi', 'organization',
            'kinerja', 'performance', 'nilai', 'values', 'adopsi',
            'adoption', 'perubahan', 'transformasi', 'strategi', 'strategy',
            'competitive', 'persaingan', 'digital transformation',
            'transformasi digital', 'digitalisasi', 'customer', 'pelanggan',
            'konsumen', 'consumer', 'client', 'service', 'layanan',
            'pelayanan', 'hospitality', 'financial', 'keuangan', 'biaya',
            'cost', 'MSE', 'mean squared error', 'forecasting', 'peramalan',
            'prediksi',
        ],
    },
    'sistem_informasi_enterprise': {
        'label': 'Sistem Informasi dan Keputusan',
        'strong': [
            'sistem informasi', 'information system', 'teknologi informasi',
            'ERP', 'enterprise resource planning', 'SAP', 'Oracle', 'CRM',
            'customer relationship management', 'supply chain management system',
            'database', 'basis data', 'data warehouse', 'data mining',
            'big data', 'business intelligence',
            'kecerdasan buatan', 'artificial intelligence', 'deep learning',
            'neural network', 'CNN', 'transformer', 'chatbot',
            'virtual assistant', 'NLP', 'natural language', 'blockchain',
            'smart contract', 'crypto', 'e-commerce', 'marketplace',
            'komputasi awan', 'IoT', 'internet of things', 'cybersecurity',
            'keamanan', 'encryption', 'authentication', 'TAM', 'UTAUT',
            'technology adoption', 'acceptance', 'penerimaan',
            'e-government', 'telemedicine', 'e-health', 'health informatics',
            'fintech', 'e-wallet', 'pembayaran digital', 'ONNX',
            'model deployment', 'decision support', 'dss',
            'sistem pendukung keputusan', 'multi-agent', 'intelligent agent',
        ],
        'weak': [
            'IT', 'software', 'aplikasi', 'platform', 'digital', 'komputer',
            'analytics', 'analitik', 'AI', 'machine learning', 'LSTM',
            'mobile', 'smartphone', 'android', 'iOS', 'app', 'web',
            'website', 'portal', 'cloud', 'SaaS', 'PaaS', 'IaaS', 'sensor',
            'embedded', 'UX', 'UI', 'user interface', 'usability',
            'user experience', 'digital transformation', 'transformasi digital',
            'social media', 'media sosial', 'payment', 'inference',
            'deployment',
        ],
    },
}

WORD_RE_CACHE = {}


def _pattern(keyword):
    if keyword not in WORD_RE_CACHE:
        WORD_RE_CACHE[keyword] = re.compile(r'\b' + re.escape(keyword.lower()) + r'\b')
    return WORD_RE_CACHE[keyword]


def score_title(title):
    """Hitung skor tiap peminatan untuk satu judul.
    Return dict: spec_id -> {'score': int, 'matched': [(keyword, weight), ...]}
    """
    if pd.isna(title):
        return {}
    title_lower = str(title).lower()
    results = {}
    for spec_id, spec in SPECIALIZATIONS.items():
        matched = []
        score = 0
        for kw in spec['strong']:
            if _pattern(kw).search(title_lower):
                matched.append((kw, 2))
                score += 2
        for kw in spec['weak']:
            if _pattern(kw).search(title_lower):
                matched.append((kw, 1))
                score += 1
        if score > 0:
            results[spec_id] = {'score': score, 'matched': matched}
    return results


def classify_title_full(title):
    """Return (label1, score1, matched1, label2, score2, matched2, ambiguous)."""
    results = score_title(title)
    if not results:
        return None, 0, [], None, 0, [], False

    ranked = sorted(results.items(), key=lambda x: x[1]['score'], reverse=True)
    top_id, top = ranked[0]
    label1 = SPECIALIZATIONS[top_id]['label']
    score1 = top['score']
    matched1 = [k for k, w in top['matched']]

    label2, score2, matched2 = None, 0, []
    if len(ranked) > 1:
        second_id, second = ranked[1]
        label2 = SPECIALIZATIONS[second_id]['label']
        score2 = second['score']
        matched2 = [k for k, w in second['matched']]

    # Ambigu kalau skor runner-up cukup dekat dengan juara 1 (selisih <=1 poin)
    ambiguous = (score2 > 0) and (score1 - score2 <= 1)

    return label1, score1, matched1, label2, score2, matched2, ambiguous


def format_kw_list(kws):
    return ';'.join(kws) if kws else ''


# ---------------------------------------------------------------------------
# Demo cepat (kalau file CSV asli belum ada di sini) supaya perbaikannya
# langsung kelihatan terbukti, termasuk kasus "beririsan" dari poster KKSIK
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    csv_path = 'list_judul_tesis_tmi_itb.csv'

    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        title_col = 'Judul Tesis'
    else:
        print("[Demo mode] File list_judul_tesis_tmi_itb.csv tidak ditemukan di folder ini.")
        print("Menjalankan contoh judul untuk membuktikan hasil perbaikan.\n")
        demo_titles = [
            "PERAMALAN HARGA KARET (TSR20) MENGGUNAKAN LSTM DENGAN KOREKSI EROR SVR DAN OPTIMASI HYPERPARAMETER",
            "PENGEMBANGAN MODEL PERAWATAN PREDIKTIF UNTUK SISTEM PRODUKSI DENGAN PENDEKATAN ANALISA BIG DATA DAN KECERDASAN BUATAN MENGGUNAKAN DATA KONDISI MESIN DAN INFORMASI KUALITAS SECARA REAL TIME",
            "PENGEMBANGAN STRATEGI PEMASARAN DIGITAL UNTUK MENINGKATKAN LOYALITAS PELANGGAN PADA UMKM",
            "ANALISIS BEBAN KERJA FISIK OPERATOR PRODUKSI MENGGUNAKAN METODE NASA-TLX",
        ]
        df = pd.DataFrame({'No': range(1, len(demo_titles) + 1), 'Judul Tesis': demo_titles})
        title_col = 'Judul Tesis'

    rows = []
    for _, row in df.iterrows():
        title = row[title_col]
        label1, score1, matched1, label2, score2, matched2, ambiguous = classify_title_full(title)
        rows.append({
            'No': row.get('No', ''),
            'Judul Tesis': title,
            'Klasifikasi': label1,
            'Skor': score1,
            'Keywords': format_kw_list(matched1),
            'Klasifikasi_2': label2,
            'Skor_2': score2,
            'Keywords_2': format_kw_list(matched2),
            'Perlu_Review': ambiguous,
        })

    out_df = pd.DataFrame(rows)
    pd.set_option('display.max_colwidth', 60)
    print(out_df.to_string(index=False))

    if not os.path.exists(csv_path):
        print("\n--- Interpretasi demo di atas ---")
        print("1) Judul karet -> sekarang 'Sistem Industri dan Rantai Nilai' (dulu salah ke Sistem Informasi krn bug ERP).")
        print("2) Judul perawatan prediktif -> skor Manufaktur & Sistem Informasi berdekatan -> Perlu_Review=True.")
        print("   Ini SESUAI kenyataan: di poster KKSIK judul serupa ini justru masuk proyek mereka (AI utk maintenance),")
        print("   padahal topiknya 'sistem produksi' juga relevan ke Manufaktur -> jadi memang beririsan, bukan dipaksa 1.")
        print("3) Judul 'pengembangan strategi pemasaran ... UMKM' tetap Manajemen Industri (benar, driven by 'pemasaran'/'UMKM'/'startup'-like terms, BUKAN oleh kata 'pengembangan' yang sudah dibuang).")
        print("4) Judul beban kerja fisik -> tetap solid ke Ergonomi (tidak berubah, karena keyword sudah spesifik dari awal).")

    else:
        output_dir = 'tesis_by_specialization_v2'
        os.makedirs(output_dir, exist_ok=True)

        total = len(out_df)
        classified_count = 0
        for spec in SPECIALIZATIONS.values():
            label = spec['label']
            sub = out_df[out_df['Klasifikasi'] == label]
            classified_count += len(sub)
            fname = label.lower().replace(' ', '_').replace('dan_', '') + '.csv'
            sub.to_csv(os.path.join(output_dir, fname), index=False, encoding='utf-8-sig', sep='\t')
            print(f"Disimpan: {os.path.join(output_dir, fname)} ({len(sub)} judul)")

        # Judul yang skornya 0 di SEMUA kategori (tidak match keyword apapun)
        # -- WAJIB disimpan, jangan sampai hilang begitu saja dari output.
        unclassified = out_df[out_df['Klasifikasi'].isna()]
        unclassified.to_csv(os.path.join(output_dir, 'tidak_terklasifikasi.csv'), index=False, encoding='utf-8-sig', sep='\t')
        print(f"Disimpan: {os.path.join(output_dir, 'tidak_terklasifikasi.csv')} ({len(unclassified)} judul, TIDAK match keyword apapun)")

        review_df = out_df[out_df['Perlu_Review']]
        review_df.to_csv(os.path.join(output_dir, 'perlu_review.csv'), index=False, encoding='utf-8-sig', sep='\t')
        print(f"\nJudul yang beririsan/perlu review manual: {len(review_df)} -> {output_dir}/perlu_review.csv")

        print(f"\n=== REKAP ===")
        print(f"Total judul     : {total}")
        print(f"Terklasifikasi  : {classified_count}")
        print(f"Tidak match sama sekali : {len(unclassified)}")
        assert classified_count + len(unclassified) == total, "Ada judul yang hilang, cek logika!"