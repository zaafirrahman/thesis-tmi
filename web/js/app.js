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
  THESES.forEach(function (t) {
    var kws = (t.keywords_official || []).slice();
    t.memberships.forEach(function (m) { kws = kws.concat(m.keywords); });
    t._hay = [t.judul, t.author || '', (t.advisors || []).join(' '), kws.join(' ')].join(' ').toLowerCase();
  });
  var dataDate = document.getElementById('dataDate');
  if (dataDate && raw.generated) dataDate.textContent = raw.generated;
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
  // filterType: 'all' | 'group' | 'multi' | 'pair'
  var state = { filterType: 'all', groupSlug: null, pairSlugs: null, query: '', sort: 'no', reviewOnly: false, advisor: '', visible: 60 };

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

  // filter dosen pembimbing
  var advisorSelect = document.getElementById('advisorSelect');
  var advisorCounts = {};
  THESES.forEach(function (t) { (t.advisors || []).forEach(function (a) { advisorCounts[a] = (advisorCounts[a] || 0) + 1; }); });
  Object.keys(advisorCounts).sort(function (a, b) {
    return advisorCounts[b] - advisorCounts[a] || a.localeCompare(b, 'id');
  }).forEach(function (a) {
    var o = document.createElement('option');
    o.value = a;
    o.textContent = a + ' (' + advisorCounts[a] + ')';
    advisorSelect.appendChild(o);
  });
  advisorSelect.addEventListener('change', function () {
    state.advisor = advisorSelect.value;
    state.visible = 60;
    render();
  });
  document.getElementById('cardList').addEventListener('click', function (e) {
    var b = e.target.closest('.abs-btn');
    if (b) toggleAbstract(b);
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
    if (state.advisor) {
      list = list.filter(function (t) { return (t.advisors || []).indexOf(state.advisor) !== -1; });
    }
    if (state.query) {
      var q = state.query;
      list = list.filter(function (t) { return t._hay.indexOf(q) !== -1; });
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
    if (t.keywords_official && t.keywords_official.length) return t.keywords_official;
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

  // ---------- abstrak (dimuat sekali, hanya saat dibuka) ----------
  var abstractsData = null, abstractsPromise = null;
  function loadAbstracts() {
    if (!abstractsPromise) {
      abstractsPromise = fetch('./data/abstracts.json')
        .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
        .then(function (j) { abstractsData = j; return j; })
        .catch(function (e) { abstractsPromise = null; throw e; });
    }
    return abstractsPromise;
  }
  function toggleAbstract(btn) {
    var card = btn.closest('.card');
    var body = card.querySelector('.abs-body');
    var no = btn.getAttribute('data-no');
    if (!body.hidden) {
      body.hidden = true;
      btn.setAttribute('aria-expanded', 'false');
      btn.querySelector('.abs-label').textContent = 'Baca abstrak';
      return;
    }
    body.hidden = false;
    btn.setAttribute('aria-expanded', 'true');
    btn.querySelector('.abs-label').textContent = 'Tutup abstrak';
    if (abstractsData) { body.textContent = abstractsData[no] || 'Abstrak tidak tersedia.'; return; }
    body.textContent = 'Memuat abstrak…';
    loadAbstracts().then(function (a) {
      body.textContent = a[no] || 'Abstrak tidak tersedia.';
    }).catch(function () {
      body.textContent = 'Gagal memuat abstrak. Periksa koneksi lalu coba lagi.';
    });
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
    var g = groupBySlug[slug];
    if (!g || !g.ketua) return '';
    var chips = '<span class="kwm-chip strong">' + escapeHtml(g.ketua) + ' (ketua)</span>' +
      (g.anggota || []).map(function (n) { return '<span class="kwm-chip weak">' + escapeHtml(n) + '</span>'; }).join('');
    return '<div class="kwm-panel' + (kwMatchOpen ? ' open' : '') + '">' +
      '<button type="button" class="kwm-toggle" data-slug="' + slug + '">' +
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 6 15 12 9 18"/></svg>' +
        (kwMatchOpen ? 'Sembunyikan cara klasifikasi' : 'Cara klasifikasi &amp; dosen KK') +
      '</button>' +
      '<div class="kwm-body">' +
        '<p class="kwm-note">Ini bukan penilaian resmi kelompok keilmuan. Tiap tesis diberi skor per kelompok dari empat sinyal: kelompok keilmuan <strong>dosen pembimbing</strong>, <strong>kata kunci resmi</strong> di Digilib, <strong>isi abstrak</strong>, dan kata pada judul (bobot sangat kecil). Dosen yang kelompoknya tidak tercantum eksplisit diberi bobot lebih rendah, dan bila kelompok dosen itu berbeda dari isi tesisnya, isi tesis lebih menentukan.</p>' +
        '<p class="kwm-section-label">Dosen resmi kelompok ini</p>' +
        '<div class="kwm-chips">' + chips + '</div>' +
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
          '<p class="desc">' + counts[g.slug].toLocaleString('id-ID') + ' judul belum bisa dikelompokkan karena tidak punya sinyal sama sekali &mdash; tanpa data dosen pembimbing, kata kunci, maupun abstrak di Digilib.</p>' +
          '<div class="legend-note">Kebanyakan adalah tesis lama yang di Digilib hanya tercatat judulnya. Cocok dicek manual.</div>';
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
      return '<span class="mpill role-' + m.role + '" title="' + escapeHtml(g.label) + ' &middot; ' + roleLabel[m.role] + ' &middot; skor ' + m.score + '%" style="' + style + '">' +
        g.abbr + ' &middot; ' + m.score + '%' +
        '</span>';
    }).join('');
  }

  function cardHtml(t) {
    var kws = (t.keywords_official && t.keywords_official.length) ? t.keywords_official :
      t.memberships.reduce(function (acc, m) { return acc.concat(m.keywords); }, []);
    var seen = {};
    var uniqKw = [];
    kws.forEach(function (k) { var lk = k.toLowerCase(); if (!seen[lk]) { seen[lk] = 1; uniqKw.push(k); } });
    var kwChips = uniqKw.slice(0, 8).map(function (k) {
      return '<span class="chip">' + escapeHtml(k) + '</span>';
    }).join('');
    var reasons = (t.review_reasons || []).join('; ');
    var reviewBadge = t.perlu_review
      ? '<span class="review-pill" title="' + escapeHtml(reasons || 'Klasifikasi belum tegas') + '">perlu ditinjau ulang</span>' : '';
    var titleHtml = t.url
      ? '<a class="title-link" href="' + escapeHtml(t.url) + '" target="_blank" rel="noopener noreferrer" title="Buka di Digilib ITB">' + escapeHtml(t.judul) + '</a>'
      : escapeHtml(t.judul);
    var metaParts = [];
    if (t.author) metaParts.push('<span>' + escapeHtml(t.author) + '</span>');
    if (t.angkatan) metaParts.push('<span title="Angkatan masuk, dibaca dari NIM">Angkatan ' + t.angkatan + '</span>');
    if (t.year) metaParts.push('<span title="Tahun terbit di Digilib">Terbit ' + t.year + '</span>');
    if (t.advisors && t.advisors.length) {
      metaParts.push('<span class="adv">Pembimbing: ' + t.advisors.map(escapeHtml).join('; ') + '</span>');
    }
    var metaHtml = metaParts.length ? '<div class="meta-line">' + metaParts.join('') + '</div>' : '';
    var absBtn = t.has_abstract
      ? '<button type="button" class="abs-btn" data-no="' + escapeHtml(t.no) + '" aria-expanded="false">' +
          '<svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
            '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><polyline points="14 3 14 8 19 8"/>' +
            '<line x1="9" y1="13" x2="15" y2="13"/><line x1="9" y1="17" x2="13" y2="17"/>' +
          '</svg>' +
          '<span class="abs-label">Baca abstrak</span>' +
        '</button>' : '';
    return '<article class="card">' +
      '<div class="spine">' + spineHtml(t) + '</div>' +
      '<div class="body">' +
        '<div class="row1">' +
          '<span class="idx">No. ' + escapeHtml(t.no) + '</span>' +
          '<span class="membership-pills">' + membershipPills(t) + reviewBadge + '</span>' +
        '</div>' +
        '<h3>' + titleHtml + '</h3>' +
        metaHtml +
        '<div class="tagrow">' + kwChips + absBtn + '</div>' +
        (t.has_abstract ? '<div class="abs-body" hidden></div>' : '') +
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
