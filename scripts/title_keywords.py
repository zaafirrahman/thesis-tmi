"""Sinyal cadangan: kecocokan kata kunci pada JUDUL (diwarisi dari classify_thesis_v2).

Bobot strong/weak tidak diubah; slug disamakan dengan config/kk.yaml.
"""
import re

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
    'ergonomi_rekayasa_kerja': {
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
    'sistem_informasi_keputusan': {
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

STRONG_WEIGHT = 2
WEAK_WEIGHT = 1

_PATTERNS = {}


def _pattern(kw):
    p = _PATTERNS.get(kw)
    if p is None:
        p = re.compile(r'\b' + re.escape(kw.lower()) + r'\b')
        _PATTERNS[kw] = p
    return p


def score_title(title):
    """Return {slug: (skor:int, [kata kunci cocok])}, hanya KK yang punya kecocokan.
    Aturan identik dengan classify_thesis_v2: strong=2, weak=1, word-boundary."""
    t = str(title or '').lower()
    out = {}
    for slug, spec in SPECIALIZATIONS.items():
        score, hits = 0, []
        for kw in spec['strong']:
            if _pattern(kw).search(t):
                score += STRONG_WEIGHT
                hits.append(kw)
        for kw in spec['weak']:
            if _pattern(kw).search(t):
                score += WEAK_WEIGHT
                hits.append(kw)
        if score:
            out[slug] = (score, hits)
    return out
