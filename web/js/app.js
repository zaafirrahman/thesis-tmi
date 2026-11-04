(async function () {
  "use strict";

  // 1. Ambil data dari file JSON eksternal
  var raw;
  try {
    var res = await fetch('./data/thesis-data.json');
    if (!res.ok) throw new Error('Gagal memuat thesis-data.json');
    raw = await res.json();
  } catch (err) {
    console.error('Error loading thesis data:', err);
    return;
  }

  // 2. Ke bawahnya kodenya SAMA PERSIS kayak punya kamu
  var GROUPS = raw.groups;
  var THESES = raw.theses;
  var UNCLASSIFIED = { slug: 'tidak_terklasifikasi', label: 'Tidak Terklasifikasi', abbr: 'Unclassified' };
GROUPS.push(UNCLASSIFIED);
var groupBySlug = {};
GROUPS.forEach(g => { groupBySlug[g.slug] = g; });
var TABS_GROUPS = GROUPS;

  // ---------- KK overview (diringkas dari profil KK TMI-ITB) ----------
  var KK_OVERVIEW = {
    sistem_industri_rantai_nilai: {
      fullName: 'Sistem Industri dan Teknoekonomi (KK-SITE)',
      chair: 'Suprayogi, S.T., M.T., Ph.D.',
      lead: 'Menerapkan pendekatan Teknik Industri untuk meningkatkan produktivitas dan daya saing sistem terintegrasi — tenaga kerja, bahan baku, energi, informasi, teknologi, dan infrastruktur — dalam interaksinya dengan dunia usaha, industri, masyarakat, dan pemerintah.',
      topics: [
        'Metodologi pemodelan sistem skala besar, perencanaan &amp; analisis sistem, proses pengambilan keputusan, sistem penilaian',
        'Sistem Industri — struktur &amp; daya saing industri, kebutuhan sumber daya, strategi dan kebijakan industri',
        'Sistem Rantai Nilai — sourcing, distribusi, infrastruktur rantai nilai',
        'Sistem sosio-teknoekonomi — perencanaan &amp; evaluasi sistem pelayanan publik'
      ]
    },
    sistem_manufaktur: {
      fullName: 'Sistem Manufaktur (KKSM)',
      chair: 'Dr. Ir. Iwan Inrawan Wiratmadja',
      lead: 'Berfokus pada perancangan, perencanaan, dan pengendalian sistem manufaktur secara menyeluruh, mulai dari desain sistem produksi hingga evaluasi kinerjanya. Peta risetnya bergerak dari Collaborative Manufacturing Systems menuju Green-Collaborative Manufacturing Systems selaras era Industri 4.0.',
      topics: [
        'Perancangan sistem manufaktur',
        'Perencanaan &amp; pengendalian manufaktur',
        'Sistem kualitas &amp; keandalan (reliability)',
        'Sistem manufaktur cerdas',
        'Jaringan sistem produksi'
      ]
    },
    manajemen_industri: {
      fullName: 'Manajemen Industri (KKMI)',
      chair: 'Prof. Dr. Ir. Joko Siswanto, MPA',
      lead: 'Mengkaji perancangan, pengembangan, implementasi, dan penyempurnaan sistem korporasi industri yang melibatkan manusia, mesin, material, informasi, energi, dan lingkungan, dengan memanfaatkan matematika, statistika, akuntansi, ekonomi, perilaku organisasi, dan psikologi.',
      topics: [
        'Inovasi, pengembangan &amp; akuisisi bisnis — kewirausahaan, rantai nilai bisnis, strategi pemasaran, blockchain, pasar modal',
        'Manajemen fungsional &amp; terintegrasi — sistem informasi, SDM untuk Industri 4.0, pemasaran digital, analisis keuangan',
        'Perbaikan berkelanjutan — manajemen pengetahuan, perubahan organisasi, big/text/web/mobile analytics, gamifikasi'
      ]
    },
    ergonomi_rekayasa_kerja: {
      fullName: 'Ergonomi, Rekayasa Kerja, dan Keselamatan Kerja (ERK3)',
      chair: 'Ir. Hardianto Iridiastadi, MSIE., Ph.D.',
      lead: 'Mengkaji kapasitas &amp; kapabilitas manusia dalam berinteraksi dengan sistem kerja (ergonomi); merancang aktivitas, stasiun, dan lingkungan kerja (rekayasa kerja); serta mengidentifikasi dan mengendalikan sumber bahaya pada sistem kerja (keselamatan kerja).',
      topics: [
        'Ergonomi industri, kognitif, &amp; transportasi',
        'Makroergonomi &amp; ergonomi pada sistem lanjut',
        'Human error &amp; sistem manajemen keselamatan',
        'Sistem berbasis perilaku — beban kerja, kelelahan, kewaspadaan pengemudi'
      ]
    },
    sistem_informasi_keputusan: {
      fullName: 'Sistem Informasi dan Keputusan (KKSIK)',
      chair: 'Prof. Dr. Rajesri Govindaraju, S.T., M.T.',
      lead: 'Menjembatani perkembangan Sistem Informasi (IS) dan Sistem Pendukung Keputusan (DSS) dengan kebutuhan manusia dan organisasi — dari perspektif rekayasa (perancangan &amp; evaluasi solusi perangkat lunak) maupun perspektif sosial (adopsi, implementasi, dampak).',
      topics: [
        'Sistem Informasi — sociotechnical systems design, design science, transformasi digital',
        'Sistem Pendukung Keputusan — model matematis &amp; AI, DSS adaptif real-time, sistem multi-agen',
        'Arah riset: digital health, sistem informasi hijau, IoT, business analytics berbasis AI'
      ]
    }
  };

  // ---------- keyword classifier reference (dari SPECIALIZATIONS di script Python) ----------
  // slug di sini disesuaikan dengan slug yang dipakai di data (raw.groups), bukan slug internal script.
  var KEYWORD_MAP = {
    sistem_manufaktur: {
      strong: ['manufaktur', 'manufacturing', 'assembly', 'perakitan', 'CNC', 'machining', 'casting', 'foaming', 'injection molding', 'extruder', 'tooling', 'fixture', 'jig', 'layout pabrik', 'automasi', 'otomasi', 'robot', 'robotika', 'AGV', 'conveyor', 'quality control', 'pengendalian kualitas', 'SPC', 'six sigma', 'lean manufacturing', 'TPM', 'perawatan mesin', 'OEE', 'process improvement', 'optimasi proses', 'discrete event', 'product design', 'prototype', '3D printing', 'additive manufacturing', 'supply chain', 'rantai pasok', 'logistik', 'distribusi', 'inventory', 'persediaan', 'warehouse', 'gudang', 'material handling', 'forklift', 'nesting', 'cutting', 'scheduling', 'penjadwalan', 'sequencing', 'fleet management', 'transportation', 'peta kendali', 'control chart', 'sampling plan', 'rencana sampling', 'chemical milling', 'sheet metal forming'],
      weak: ['produksi', 'pabrik', 'industri', 'produk', 'mesin', 'maintenance', 'reliability', 'simulasi', 'lean']
    },
    sistem_industri_rantai_nilai: {
      strong: ['rantai nilai', 'value chain', 'nilai tambah', 'value stream', 'kompetitif', 'competitive', 'keunggulan bersaing', 'daya saing', 'business model', 'model bisnis', 'canvas', 'BMC', 'merger', 'akuisisi', 'divestasi', 'restrukturisasi', 'ESG', 'carbon', 'emisi', 'energi terbarukan', 'EBT', 'renewable', 'life cycle assessment', 'LCA', 'daur ulang', 'recycling', 'circular economy', 'ekonomi sirkular', 'risk management', 'manajemen risiko', 'mitigasi risiko', 'resilience', 'resiliensi', 'ketahanan', 'tangguh', 'stakeholder', 'pemangku kepentingan', 'CSR', 'corporate social', 'SNI', 'sertifikasi', 'akreditasi', 'sustainability', 'berkelanjutan', 'lingkungan', 'environmental', 'komoditas', 'komoditi', 'harga komoditas', 'fluktuasi harga', 'karet', 'getah karet', 'kelapa sawit', 'sawit', 'crude palm oil', 'CPO', 'kopi', 'kakao', 'batubara', 'nikel', 'timah', 'ekspor', 'impor', 'perdagangan internasional', 'neraca perdagangan', 'harga pasar', 'harga global', 'agroindustri', 'komoditas pertanian', 'rute kendaraan', 'vehicle routing', 'lokasi fasilitas', 'facility location', 'lokasi-alokasi fasilitas', 'jaringan distribusi', 'distribution network', 'rute kapal', 'penentuan rute', 'moda transportasi', 'transportasi umum', 'angkutan umum', 'angkutan', 'pelabuhan', 'terminal', 'bandara', 'penerbangan', 'stasiun pengisian', 'kendaraan listrik', 'electric vehicle', 'depot', 'jaringan hub', 'kapal', 'pelayaran', 'petikemas', 'kontainer', 'transshipment', 'wisatawan', 'pariwisata', 'wisata', 'sektor ekonomi', 'perekonomian', 'sektor pertanian', 'agribisnis', 'perkebunan', 'koperasi', 'tarif', 'willingness to pay', 'subsidi', 'pembangunan sektor', 'kebijaksanaan pembangunan', 'harga air', 'jasa telekomunikasi', 'depo', 'vehicle flow', 'fleet vehicle', 'pickup and delivery', 'cross-docking', 'fourth party logistic', 'sampah', 'limbah', 'persampahan', 'insinerator', 'dirgantara'],
      weak: ['strategi', 'strategic', 'pertumbuhan', 'growth', 'scaling', 'ekspansi', 'kebijakan', 'policy', 'regulasi', 'regulation', 'pemerintah', 'ekonomi', 'economic', 'GDP', 'makroekonomi', 'industri 4.0', 'transformasi digital', 'digitalisasi', 'green', 'standar', 'standard', 'ISO', 'kendaraan', 'jaringan']
    },
    ergonomi_rekayasa_kerja: {
      strong: ['ergonomi', 'ergonomic', 'human factors', 'faktor manusia', 'antropometri', 'anthropometry', 'postur', 'posture', 'beban kerja', 'workload', 'beban fisik', 'physical load', 'kelelahan', 'fatigue', 'nyeri', 'pain', 'MSDs', 'musculoskeletal', 'kerja fisik', 'physical work', 'aktivitas otot', 'EMG', 'thermal', 'kebisingan', 'noise', 'getaran', 'vibration', 'pencahayaan', 'lighting', 'illumination', 'K3', 'kecelakaan', 'accident', 'hazard', 'APD', 'PPE', 'helm', 'masker', 'pelindung', 'cognitive load', 'beban kognitif', 'mental workload', 'atensi', 'persepsi', 'perception', 'biomekanika', 'biomechanics', 'kinerja manusia', 'human performance', 'shift work', 'kerja shift', 'jam kerja', 'work schedule', 'prosthesis', 'prostetik', 'kaki palsu', 'tangan palsu', 'workplace design', 'desain tempat kerja', 'workstation', 'perilaku berkendara', 'perilaku berisiko', 'berkendara', 'mengemudi', 'pengemudi', 'pengendara', 'naturalistic riding', 'naturalistic driving', 'driving behavior', 'riding behavior', 'kewaspadaan', 'kantuk', 'sleepiness', 'alertness', 'situation awareness', 'performansi mengemudi', 'masinis', 'waktu reaksi', 'reaction time'],
      weak: ['kenyamanan', 'comfort', 'keselamatan', 'safety', 'usability', 'user experience', 'UX', 'interface', 'antarmuka', 'attention', 'pilot', 'simulator']
    },
    manajemen_industri: {
      strong: ['kepemimpinan', 'leadership', 'motivasi', 'motivation', 'SDM', 'human resource', 'talenta', 'talent', 'karyawan', 'pegawai', 'KPI', 'produktivitas', 'productivity', 'inovasi', 'innovation', 'ambidexterity', 'exploration', 'exploitation', 'learning organization', 'organisasi pembelajar', 'knowledge management', 'change management', 'budaya organisasi', 'decision making', 'pengambilan keputusan', 'multi-criteria', 'AHP', 'TOPSIS', 'project management', 'manajemen proyek', 'portofolio', 'quality management', 'TQM', 'ISO 9001', 'mutu', 'supply chain management', 'vendor', 'supplier', 'pemasok', 'pembelian', 'procurement', 'pengadaan', 'kontrak', 'UMKM', 'UKM', 'usaha kecil', 'startup', 'wirausaha', 'business process', 'BPM', 'proses bisnis', 'workflow', 'agile', 'scrum', 'kanban', 'continuous improvement', 'marketing', 'pemasaran', 'brand', 'merek', 'promosi', 'ROI', 'investasi'],
      weak: ['manajemen', 'management', 'organisasi', 'organization', 'kinerja', 'performance', 'nilai', 'values', 'adopsi', 'adoption', 'perubahan', 'transformasi', 'strategi', 'strategy', 'competitive', 'persaingan', 'digital transformation', 'transformasi digital', 'digitalisasi', 'customer', 'pelanggan', 'konsumen', 'consumer', 'client', 'service', 'layanan', 'pelayanan', 'hospitality', 'financial', 'keuangan', 'biaya', 'cost', 'MSE', 'mean squared error', 'forecasting', 'peramalan', 'prediksi']
    },
    sistem_informasi_keputusan: {
      strong: ['sistem informasi', 'information system', 'teknologi informasi', 'ERP', 'enterprise resource planning', 'SAP', 'Oracle', 'CRM', 'customer relationship management', 'supply chain management system', 'database', 'basis data', 'data warehouse', 'data mining', 'big data', 'business intelligence', 'kecerdasan buatan', 'artificial intelligence', 'deep learning', 'neural network', 'CNN', 'transformer', 'chatbot', 'virtual assistant', 'NLP', 'natural language', 'blockchain', 'smart contract', 'crypto', 'e-commerce', 'marketplace', 'komputasi awan', 'IoT', 'internet of things', 'cybersecurity', 'keamanan', 'encryption', 'authentication', 'TAM', 'UTAUT', 'technology adoption', 'acceptance', 'penerimaan', 'e-government', 'telemedicine', 'e-health', 'health informatics', 'fintech', 'e-wallet', 'pembayaran digital', 'ONNX', 'model deployment', 'decision support', 'dss', 'sistem pendukung keputusan', 'multi-agent', 'intelligent agent'],
      weak: ['IT', 'software', 'aplikasi', 'platform', 'digital', 'komputer', 'analytics', 'analitik', 'AI', 'machine learning', 'LSTM', 'mobile', 'smartphone', 'android', 'iOS', 'app', 'web', 'website', 'portal', 'cloud', 'SaaS', 'PaaS', 'IaaS', 'sensor', 'embedded', 'UX', 'UI', 'user interface', 'usability', 'user experience', 'digital transformation', 'transformasi digital', 'social media', 'media sosial', 'payment', 'inference', 'deployment']
    }
  };

  // filterType: 'all' | 'group' | 'multi' | 'pair'
  var state = { filterType: 'all', groupSlug: null, pairSlugs: null, query: '', sort: 'no', reviewOnly: false, visible: 60 };

  var totalCount = document.getElementById('totalCount');
  var multiCountEl = document.getElementById('multiCount');
  totalCount.textContent = THESES.length.toLocaleString('id-ID');
  var multiTotal = THESES.filter(function (t) { return t.memberships.length > 1; }).length;
  multiCountEl.textContent = multiTotal.toLocaleString('id-ID') + ' judul';

  // ---------- membership counts (utama + sekunder) ----------
  var counts = {}, utamaCounts = {}, sekunderCounts = {};
  GROUPS.forEach(function (g) { counts[g.slug] = 0; utamaCounts[g.slug] = 0; sekunderCounts[g.slug] = 0; });
  THESES.forEach(function (t) {
    t.memberships.forEach(function (m) {
      counts[m.slug] = (counts[m.slug] || 0) + 1;
      if (m.role === 'utama') utamaCounts[m.slug]++; else sekunderCounts[m.slug]++;
    });
  });
  var unclassCount = THESES.filter(function (t) { return t.memberships.length === 0; }).length;
  counts[UNCLASSIFIED.slug] = unclassCount;
  utamaCounts[UNCLASSIFIED.slug] = unclassCount;

  // ---------- spectrum bar (based on kelompok utama, sums to total) ----------
  var spectrum = document.getElementById('spectrum');
  var caption = document.getElementById('spectrumCaption');
  TABS_GROUPS.forEach(function (g) {
    var btn = document.createElement('button');
    btn.style.background = 'var(--g-' + g.slug + ')';
    btn.style.flexGrow = String(Math.max(utamaCounts[g.slug], 1));
    btn.title = g.label + ' — ' + utamaCounts[g.slug] + ' judul';
    btn.dataset.slug = g.slug;
    btn.addEventListener('click', function () {
      setFilter(state.filterType === 'group' && state.groupSlug === g.slug ? { filterType: 'all' } : { filterType: 'group', groupSlug: g.slug });
    });
    spectrum.appendChild(btn);
  });
  caption.innerHTML =
    '<span class="caption-legend">' + TABS_GROUPS.map(function (g) {
      return '<span class="lg"><span class="sw" style="background:var(--g-' + g.slug + ')"></span>' + g.abbr + '</span>';
    }).join('') + '</span>' +
    '<span>' + THESES.length.toLocaleString('id-ID') + ' judul · Proporsi KK utama</span>';

  // ---------- top pairs ----------
  var pairCounts = {};
  THESES.forEach(function (t) {
    var slugs = Array.from(new Set(t.memberships.map(function (m) { return m.slug; }))).sort();
    if (slugs.length === 2) {
      var key = slugs.join('|');
      pairCounts[key] = (pairCounts[key] || 0) + 1;
    }
  });
  var pairList = Object.keys(pairCounts).map(function (key) {
    var slugs = key.split('|');
    return { slugs: slugs, count: pairCounts[key] };
  }).sort(function (a, b) { return b.count - a.count; }).slice(0, 8);

  var pairRow = document.getElementById('pairRow');
  function buildPairRow() {
    pairRow.innerHTML = '';
    pairList.forEach(function (p) {
      var isActive = state.filterType === 'pair' && state.pairSlugs && state.pairSlugs[0] === p.slugs[0] && state.pairSlugs[1] === p.slugs[1];
      var el = document.createElement('button');
      el.type = 'button';
      el.className = 'pair-chip' + (isActive ? ' active' : '');
      var gA = groupBySlug[p.slugs[0]], gB = groupBySlug[p.slugs[1]];
      el.title = gA.label + ' × ' + gB.label;
      el.innerHTML =
        '<span class="sw" style="background:var(--g-' + gA.slug + ')"></span>' +
        '<span>' + gA.abbr + '</span>' +
        '<span class="cross">×</span>' +
        '<span class="sw" style="background:var(--g-' + gB.slug + ')"></span>' +
        '<span>' + gB.abbr + '</span>' +
        '<span class="n">' + p.count + '</span>';
      el.addEventListener('click', function () {
        setFilter(isActive ? { filterType: 'all' } : { filterType: 'pair', pairSlugs: p.slugs });
      });
      pairRow.appendChild(el);
    });
  }

  // ---------- tabs ----------
  var tabsEl = document.getElementById('tabs');
  function buildTabs() {
    tabsEl.innerHTML = '';
    tabsEl.appendChild(makeTab('Semua', THESES.length, null, state.filterType === 'all', function () { setFilter({ filterType: 'all' }); }, null));
    TABS_GROUPS.forEach(function (g) {
      var active = state.filterType === 'group' && state.groupSlug === g.slug;
      tabsEl.appendChild(makeTab(g.abbr, counts[g.slug], g.slug, active, function () {
        setFilter(active ? { filterType: 'all' } : { filterType: 'group', groupSlug: g.slug });
      }, g.label));
    });
    var multiActive = state.filterType === 'multi';
    tabsEl.appendChild(makeTab('Intersected', multiTotal, null, multiActive, function () {
      setFilter(multiActive ? { filterType: 'all' } : { filterType: 'multi' });
    }, null));
  }
  function makeTab(label, count, colorSlug, active, onClick, fullLabel) {
    var el = document.createElement('button');
    el.type = 'button';
    el.className = 'tab' + (active ? ' active' : '');
    if (colorSlug) el.style.setProperty('--tab-color', 'var(--g-' + colorSlug + ')');
    if (fullLabel) el.title = fullLabel;
    var dot = colorSlug ? '<span class="dot" style="background:var(--g-' + colorSlug + ')"></span>' : '';
    el.innerHTML = dot + '<span>' + label + '</span><span class="n">' + count + '</span>';
    el.addEventListener('click', onClick);
    return el;
  }

  function setFilter(next) {
    state.filterType = next.filterType;
    state.groupSlug = next.groupSlug || null;
    state.pairSlugs = next.pairSlugs || null;
    state.visible = 60;
    render();
  }

  // ---------- search / sort / review toggle ----------
  var searchInput = document.getElementById('searchInput');
  searchInput.addEventListener('input', function () {
    state.query = searchInput.value.trim().toLowerCase();
    state.visible = 60;
    render();
  });
  var sortSelect = document.getElementById('sortSelect');
  sortSelect.addEventListener('change', function () {
    state.sort = sortSelect.value;
    render();
  });
  var reviewToggle = document.getElementById('reviewToggle');
  reviewToggle.addEventListener('change', function () {
    state.reviewOnly = reviewToggle.checked;
    state.visible = 60;
    render();
  });

  function maxScore(t) {
    return t.memberships.reduce(function (m, x) { return Math.max(m, x.score); }, 0);
  }
  function utamaScore(t) {
    var u = t.memberships.filter(function (m) { return m.role === 'utama'; })[0];
    return u ? u.score : 0;
  }

  // ---------- filtering ----------
  function getFiltered() {
    var list = THESES;
    if (state.filterType === 'group') {
      if (state.groupSlug === UNCLASSIFIED.slug) {
        list = list.filter(function (t) { return t.memberships.length === 0; });
      } else {
        list = list.filter(function (t) { return t.memberships.some(function (m) { return m.slug === state.groupSlug; }); });
      }
    } else if (state.filterType === 'multi') {
      list = list.filter(function (t) { return t.memberships.length > 1; });
    } else if (state.filterType === 'pair') {
      var a = state.pairSlugs[0], b = state.pairSlugs[1];
      list = list.filter(function (t) {
        var slugs = t.memberships.map(function (m) { return m.slug; });
        return slugs.indexOf(a) !== -1 && slugs.indexOf(b) !== -1;
      });
    }
    if (state.reviewOnly) {
      list = list.filter(function (t) { return t.perlu_review; });
    }
    if (state.query) {
      var q = state.query;
      list = list.filter(function (t) {
        if (t.judul.toLowerCase().indexOf(q) !== -1) return true;
        for (var i = 0; i < t.memberships.length; i++) {
          var kws = t.memberships[i].keywords;
          for (var j = 0; j < kws.length; j++) {
            if (kws[j].toLowerCase().indexOf(q) !== -1) return true;
          }
        }
        return false;
      });
    }
    list = list.slice();
    if (state.sort === 'conf') {
      list.sort(function (a, b) { return utamaScore(b) - utamaScore(a); });
    } else if (state.sort === 'az') {
      list.sort(function (a, b) { return a.judul.localeCompare(b.judul, 'id'); });
    } else {
      list.sort(function (a, b) { return (parseInt(a.no, 10) || 0) - (parseInt(b.no, 10) || 0); });
    }
    return list;
  }

  // ---------- keyword insight ----------
  function relevantKeywords(t) {
    if (state.filterType === 'group') {
      return t.memberships.filter(function (m) { return m.slug === state.groupSlug; })
        .reduce(function (acc, m) { return acc.concat(m.keywords); }, []);
    }
    if (state.filterType === 'pair') {
      return t.memberships.filter(function (m) { return state.pairSlugs.indexOf(m.slug) !== -1; })
        .reduce(function (acc, m) { return acc.concat(m.keywords); }, []);
    }
    return t.memberships.reduce(function (acc, m) { return acc.concat(m.keywords); }, []);
  }
  function topKeywords(list, n) {
    var freq = {};
    list.forEach(function (t) {
      relevantKeywords(t).forEach(function (k) {
        var key = k.toLowerCase();
        freq[key] = (freq[key] || 0) + 1;
      });
    });
    var arr = Object.keys(freq).map(function (k) { return { k: k, c: freq[k] }; });
    arr.sort(function (a, b) { return b.c - a.c; });
    return arr.slice(0, n);
  }

  function escapeHtml(s) {
    return s.replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  // ---------- digilib link helpers ----------
  function digilibSlug(title) {
    return title
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '');
  }
  function digilibDirectUrl(title) {
    return 'https://digilib.itb.ac.id/gdl/view_data/' + digilibSlug(title);
  }
  function digilibFallbackUrl(title) {
    return 'https://www.google.com/search?q=' + encodeURIComponent('site:digilib.itb.ac.id "' + title + '"');
  }

  // ---------- group info panel ----------
  var groupInfo = document.getElementById('groupInfo');
  var kwList = document.getElementById('kwList');
  var kkOverviewOpen = false;
  var kwMatchOpen = false;

  function kkOverviewHtml(slug) {
    var ov = KK_OVERVIEW[slug];
    if (!ov) return '';
    return '<div class="kk-overview' + (kkOverviewOpen ? ' open' : '') + '">' +
      '<p class="kko-lead">' + ov.lead + '</p>' +
      '<p class="kko-chair">Ketua KK: ' + escapeHtml(ov.chair) + '</p>' +
      '<button type="button" class="kko-toggle" data-slug="' + slug + '">' +
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 6 15 12 9 18"/></svg>' +
        (kkOverviewOpen ? 'Sembunyikan bidang kajian' : 'Lihat bidang kajian') +
      '</button>' +
      '<div class="kko-body"><ul>' + ov.topics.map(function (t) { return '<li>' + t + '</li>'; }).join('') + '</ul></div>' +
    '</div>';
  }

  function kwMatchHtml(slug) {
    var km = KEYWORD_MAP[slug];
    if (!km) return '';
    var strongChips = km.strong.map(function (k) {
      return '<span class="kwm-chip strong">' + escapeHtml(k) + '</span>';
    }).join('');
    var weakChips = km.weak.map(function (k) {
      return '<span class="kwm-chip weak">' + escapeHtml(k) + '</span>';
    }).join('');
    return '<div class="kwm-panel' + (kwMatchOpen ? ' open' : '') + '">' +
      '<button type="button" class="kwm-toggle" data-slug="' + slug + '">' +
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 6 15 12 9 18"/></svg>' +
        (kwMatchOpen ? 'Sembunyikan kata kunci pencocokan' : 'Lihat kata kunci pencocokan') +
      '</button>' +
      '<div class="kwm-body">' +
        '<p class="kwm-note">Ini bukan definisi resmi kelompok keilmuan &mdash; classifier otomatis cuma mencocokkan kata-kata di bawah ini yang muncul di judul. Penanda kuat lebih spesifik ke KK ini; penanda lemah lebih umum dan sering nyerempet ke kelompok lain, jadi kontribusinya ke skor lebih kecil.</p>' +
        '<p class="kwm-section-label">Penanda kuat</p>' +
        '<div class="kwm-chips">' + strongChips + '</div>' +
        '<p class="kwm-section-label">Penanda lemah</p>' +
        '<div class="kwm-chips">' + weakChips + '</div>' +
      '</div>' +
    '</div>';
  }

  groupInfo.addEventListener('click', function (e) {
    var kkoBtn = e.target.closest('.kko-toggle');
    if (kkoBtn) {
      kkOverviewOpen = !kkOverviewOpen;
      renderPanel(getFiltered());
      return;
    }
    var kwmBtn = e.target.closest('.kwm-toggle');
    if (kwmBtn) {
      kwMatchOpen = !kwMatchOpen;
      renderPanel(getFiltered());
      return;
    }
  });

  function renderPanel(filteredList) {
    if (state.filterType === 'group') {
      var g = groupBySlug[state.groupSlug];
      if (g.slug === UNCLASSIFIED.slug) {
        groupInfo.innerHTML =
          '<h2><span class="sw" style="background:var(--g-tidak_terklasifikasi)"></span>' + g.label + '</h2>' +
          '<p class="desc">' + counts[g.slug].toLocaleString('id-ID') + ' judul belum berhasil dicocokkan ke kelompok manapun oleh classifier &mdash; skornya nol di semua kelompok.</p>' +
          '<div class="legend-note">Cocok buat dicek manual: mungkin butuh kata kunci baru di classifier, atau memang topiknya lintas-disiplin di luar 5 kelompok yang ada.</div>';
      } else {
        groupInfo.innerHTML =
          '<h2><span class="sw" style="background:var(--g-' + g.slug + ')"></span>' + g.label + ' <span style="font-family:\'IBM Plex Mono\',monospace;font-size:0.72rem;color:var(--ink-faint);font-weight:400;">(' + g.abbr + ')</span></h2>' +
          kkOverviewHtml(g.slug) +
          '<p class="desc">' + counts[g.slug].toLocaleString('id-ID') + ' judul menyentuh kelompok ini.</p>' +
          '<div class="role-split">' +
            '<div class="rs"><b>' + utamaCounts[g.slug] + '</b><span>sebagai utama</span></div>' +
            '<div class="rs"><b>' + sekunderCounts[g.slug] + '</b><span>sebagai kedua</span></div>' +
          '</div>' +
          kwMatchHtml(g.slug) +
          '<div class="legend-note">Klik tab &ldquo;Semua&rdquo; untuk kembali melihat seluruh koleksi.</div>';
      }
    } else if (state.filterType === 'multi') {
      groupInfo.innerHTML =
        '<h2><span class="sw" style="background:var(--ink-faint)"></span>Intersected</h2>' +
        '<p class="desc">' + multiTotal.toLocaleString('id-ID') + ' dari ' + THESES.length.toLocaleString('id-ID') + ' judul (' + Math.round(multiTotal / THESES.length * 100) + '%) tercatat punya kelompok utama sekaligus kelompok kedua.</p>' +
        '<div class="legend-note">Lihat blok &ldquo;kelompok yang paling sering beririsan&rdquo; di atas untuk pasangan spesifik.</div>';
    } else if (state.filterType === 'pair') {
      var gA = groupBySlug[state.pairSlugs[0]], gB = groupBySlug[state.pairSlugs[1]];
      groupInfo.innerHTML =
        '<h2><span class="sw" style="background:var(--g-' + gA.slug + ')"></span>' + gA.label + '</h2>' +
        '<p class="desc">Beririsan dengan <strong>' + gB.label + '</strong> &mdash; ' + filteredList.length.toLocaleString('id-ID') + ' judul menyentuh keduanya, entah sebagai utama atau kedua.</p>' +
        '<div class="legend-note">Klik chip pasangan yang sama sekali lagi untuk melepas filter.</div>';
    } else {
      groupInfo.innerHTML =
        '<h2><span class="sw" style="background:var(--ink-faint)"></span>Semua kelompok</h2>' +
        '<p class="desc">' + THESES.length.toLocaleString('id-ID') + ' judul dari 5 kelompok keilmuan, ' + multiTotal.toLocaleString('id-ID') + ' di antaranya beririsan dua kelompok, dan ' + unclassCount.toLocaleString('id-ID') + ' belum terklasifikasi sama sekali.</p>' +
        '<div class="legend-note">Pilih tab, klik segmen spektrum, atau klik pasangan kelompok untuk menelusuri lebih spesifik.</div>';
    }
    var tk = topKeywords(filteredList, 10);
    if (!tk.length) {
      kwList.innerHTML = '<p class="desc" style="margin:0;">Tidak ada kata kunci tercatat untuk seleksi ini.</p>';
    } else {
      var max = tk[0].c;
      var color = (state.filterType === 'group') ? 'var(--g-' + state.groupSlug + ')' :
                  (state.filterType === 'pair') ? 'var(--g-' + state.pairSlugs[0] + ')' : 'var(--accent)';
      kwList.innerHTML = tk.map(function (item) {
        var pct = Math.max(6, Math.round((item.c / max) * 100));
        return '<div class="kw-row">' +
          '<div class="kw-top"><span class="kw-name">' + escapeHtml(item.k) + '</span><span class="kw-count">' + item.c + '</span></div>' +
          '<div class="kw-bar-track"><div class="kw-bar-fill" style="width:' + pct + '%;background:' + color + '"></div></div>' +
          '</div>';
      }).join('');
    }
  }

  // ---------- cards ----------
  var cardList = document.getElementById('cardList');
  var listMeta = document.getElementById('listMeta');
  var emptyState = document.getElementById('emptyState');
  var loadMoreWrap = document.getElementById('loadMoreWrap');
  var loadMoreBtn = document.getElementById('loadMoreBtn');

  var roleLabel = { utama: 'utama', sekunder: 'kedua' };

  function spineHtml(t) {
    if (t.memberships.length === 0) return '<i style="background:var(--g-tidak_terklasifikasi)"></i>';
    return t.memberships.map(function (m) {
      return '<i style="background:var(--g-' + m.slug + ')"></i>';
    }).join('');
  }

  function membershipPills(t) {
    if (t.memberships.length === 0) {
      return '<span class="mpill" title="Tidak terklasifikasi" style="background:transparent;color:var(--g-tidak_terklasifikasi);border-color:var(--g-tidak_terklasifikasi);border-style:dashed;">' +
        '<span class="sw" style="background:var(--g-tidak_terklasifikasi)"></span>Unclassified</span>';
    }
    return t.memberships.map(function (m) {
      var g = groupBySlug[m.slug];
      var style = m.role === 'utama'
        ? 'background:var(--g-' + g.slug + ');border-color:var(--g-' + g.slug + ')'
        : 'background:transparent;color:var(--g-' + g.slug + ');border-color:var(--g-' + g.slug + ')';
      return '<span class="mpill role-' + m.role + '" title="' + escapeHtml(g.label) + ' &middot; ' + roleLabel[m.role] + '" style="' + style + '">' +
        g.abbr + ' &middot; ' + m.score +
        '</span>';
    }).join('');
  }

  function cardHtml(t) {
    var allKw = t.memberships.reduce(function (acc, m) { return acc.concat(m.keywords); }, []);
    var seen = {};
    var uniqKw = [];
    allKw.forEach(function (k) { var lk = k.toLowerCase(); if (!seen[lk]) { seen[lk] = 1; uniqKw.push(k); } });
    var kwChips = uniqKw.slice(0, 8).map(function (k) {
      return '<span class="chip">' + escapeHtml(k) + '</span>';
    }).join('');
    var reviewBadge = t.perlu_review ? '<span class="review-pill">perlu ditinjau ulang</span>' : '';
    var directUrl = digilibDirectUrl(t.judul);
    var fallbackUrl = digilibFallbackUrl(t.judul);
    var titleHtml = '<a class="title-link" href="' + escapeHtml(directUrl) + '" target="_blank" rel="noopener noreferrer" title="Buka di Digilib ITB (tautan tebakan, mungkin 404 untuk judul terbaru)">' + escapeHtml(t.judul) + '</a>';
    var fallbackHtml =
      '<a class="fallback-search" href="' + escapeHtml(fallbackUrl) + '" target="_blank" rel="noopener noreferrer" title="Link judul 404? Cari halaman ini di Digilib lewat Google">' +
        '<span>Go to paper</span>' +
        '<svg viewBox="0 0 24 24" fill="none" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="7" y1="17" x2="17" y2="7"/><polyline points="7 7 17 7 17 17"/></svg>' +
      '</a>';
    return '<article class="card">' +
      '<div class="spine">' + spineHtml(t) + '</div>' +
      '<div class="body">' +
        '<div class="row1">' +
          '<span class="idx">No. ' + escapeHtml(t.no) + '</span>' +
          '<span class="membership-pills">' + membershipPills(t) + reviewBadge + '</span>' +
        '</div>' +
        '<h3>' + titleHtml + '</h3>' +
        '<div class="tagrow">' + kwChips + fallbackHtml + '</div>' +
      '</div>' +
    '</article>';
  }

  function render() {
    buildTabs();
    buildPairRow();
    var spectrumBtns = spectrum.querySelectorAll('button');
    spectrumBtns.forEach(function (b) {
      var dim = state.filterType === 'group' && b.dataset.slug !== state.groupSlug;
      b.classList.toggle('dim', dim);
    });

    var filtered = getFiltered();
    renderPanel(filtered);

    listMeta.textContent = filtered.length.toLocaleString('id-ID') + ' judul ditemukan' + (state.query ? ' untuk "' + state.query + '"' : '');

    if (!filtered.length) {
      cardList.innerHTML = '';
      emptyState.style.display = 'block';
      loadMoreWrap.style.display = 'none';
      return;
    }
    emptyState.style.display = 'none';

    var slice = filtered.slice(0, state.visible);
    cardList.innerHTML = slice.map(cardHtml).join('');

    if (filtered.length > state.visible) {
      loadMoreWrap.style.display = 'block';
      var remaining = filtered.length - state.visible;
      loadMoreBtn.textContent = 'Tampilkan ' + Math.min(60, remaining) + ' judul berikutnya (' + remaining + ' tersisa)';
    } else {
      loadMoreWrap.style.display = 'none';
    }
  }

  loadMoreBtn.addEventListener('click', function () {
    state.visible += 60;
    render();
  });

  render();
})();
