import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
FIX = ROOT / 'tests' / 'fixtures'

from classify_thesis import advisor_vector, run  # noqa: E402
from common import angkatan_from_nim, canonical_url, file_stem, fix_href, safe_url  # noqa: E402
from build_site import bump_sw_cache  # noqa: E402
from check_data import compare, problems, summary  # noqa: E402
from fetch_detail import candidates, fetch_one, load_known_bad, slug_variants  # noqa: E402
from crawl_list import assign_ids, parse_list_page  # noqa: E402
from names import LecturerIndex, extract_advisor_names, load_kk, name_key  # noqa: E402
from parse_detail import parse_detail, split_keywords  # noqa: E402


class ListPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.items, cls.total = parse_list_page((FIX / 'list_page.html').read_text(encoding='utf-8'))

    def test_counts(self):
        self.assertEqual(self.total, 1132)
        self.assertEqual(len(self.items), 20)
        self.assertEqual(len({i['id'] for i in self.items}), 20)

    def test_first_item_old_thesis_without_nim_in_url(self):
        it = self.items[0]
        self.assertTrue(it['title'].startswith('PENGEMBANGAN MODEL SISTEM DAUR ULANG SATU LANGKAH'))
        self.assertNotIn('?', it['url'])
        self.assertFalse(it['url'].endswith('/'))
        self.assertEqual((it['author'], it['nim']), ('New Vita Mey Destty Marbun', '23410056'))
        self.assertEqual(it['advisors'], ['Ir. Rachmawati Wangsaputra, M.T., Ph.D.'])
        self.assertEqual(it['rank'], 1)

    def test_multiple_advisors_split_on_semicolon(self):
        it = [i for i in self.items if i['nim'] == '23424053'][0]
        self.assertEqual(len(it['advisors']), 3)
        self.assertIn('Titah Yudhistira, S.T., M.T., Ph.D.', it['advisors'])


class OldRecords(unittest.TestCase):
    def test_href_whitespace_removed(self):
        h = 'https://x/gdl/view_data/abc-\n\tdef-\n/?rows=1&per_page=3'
        self.assertEqual(fix_href(h).split('?')[0], 'https://x/gdl/view_data/abc-def-/')
        self.assertEqual(canonical_url(h), 'https://x/gdl/view_data/abc-def-')

    def test_file_stem_short_and_safe(self):
        stem = file_stem('a' * 300 + '/weird id:*')
        self.assertLess(len(stem), 100)
        self.assertRegex(stem, r'^[A-Za-z0-9._~-]+$')

    def test_duplicate_slugs_get_unique_ids_not_dropped(self):
        mk = lambda t, a: {'id': 'same-slug', 'title': t, 'author': a, 'ambiguous_url': False}
        items = assign_ids([mk('JUDUL A', 'Budi'), mk('Judul a', 'Sari'), {**mk('lain', 'x'), 'id': 'other'}])
        self.assertEqual(len({i['id'] for i in items}), 3)
        self.assertEqual([i['ambiguous_url'] for i in items], [True, True, False])
        self.assertEqual(items[2]['id'], 'other')

    def test_exact_duplicate_entries_kept_with_unique_ids(self):
        mk = lambda: {'id': 'same-slug', 'title': 'JUDUL A', 'author': 'Budi', 'ambiguous_url': False}
        a, b = assign_ids([mk(), mk()])
        self.assertNotEqual(a['id'], b['id'])
        self.assertIsNone(a['duplicate_of'])
        self.assertEqual(b['duplicate_of'], a['id'])

    def test_empty_nim_brackets(self):
        html = ('<div class="col-lg-11"><a href="https://d/gdl/view_data/x/?rows=2&per_page=1">T</a>'
                '<sup><i class="bi bi-person"></i> Shaaban Bakar Said[] <i class="bi bi-people"></i> P</sup></div>')
        it = parse_list_page(html)[0][0]
        self.assertEqual((it['author'], it['nim']), ('Shaaban Bakar Said', None))

    def test_old_advisor_strings(self):
        f = extract_advisor_names
        self.assertEqual(f(['Pembimbing : 1.Matthias Aroef 2. Ubuh Buchara Didayat Scan: Mudjiono']),
                         ['Matthias Aroef', 'Ubuh Buchara Didayat'])
        self.assertEqual(f(['Muhamad Faisal ', 'Muhamad Sutarno Scanner : Kory']),
                         ['Muhamad Faisal', 'Muhamad Sutarno'])
        self.assertEqual(f(['Pembimbing : Prof.Dr.Mathias Aroef, MSIE. Scanner: Alice Diniarti', '2008-01-04.']),
                         ['Prof.Dr.Mathias Aroef, MSIE'])
        self.assertEqual(f(['P']), [])
        self.assertEqual(f(['#CONTRIBUTOR#']), [])
        self.assertEqual(f(['Dr. Ir. S.B. Hari Lubis']), ['Dr. Ir. S.B. Hari Lubis'])

    def test_html_and_glued_advisor_strings(self):
        f = extract_advisor_names
        self.assertEqual(f(['<br /> <br /> Prof. Dr. Ir. Senator Nur Bahagia <br /> <br /> Dr. Titah Yudhistira, S.T., M.T']),
                         ['Prof. Dr. Ir. Senator Nur Bahagia', 'Dr. Titah Yudhistira, S.T., M.T'])
        self.assertEqual(f(['Prof.Dr.Ir. Abdul Hakim Halim, MSc. Dr. Wisnu Aribowo, ST., MT']),
                         ['Prof.Dr.Ir. Abdul Hakim Halim, MSc', 'Dr. Wisnu Aribowo, ST., MT'])
        self.assertEqual(f(['Harsono Taroepratjeka, Prof., Dr., Ir., dan Dradjad Irianto, Prof. Dr. Ir. M.Eng']),
                         ['Harsono Taroepratjeka, Prof., Dr., Ir', 'Dradjad Irianto, Prof. Dr. Ir. M.Eng'])
        self.assertEqual(f(['Pembimbing Dr. TMA. Ari Samadhi']), ['Dr. TMA. Ari Samadhi'])
        self.assertEqual(f(['(Suprayogi Ph.D.)']), ['Suprayogi Ph.D'])
        self.assertEqual(f(['(1) Dr. Sukoyo (ITB)']), ['Dr. Sukoyo'])
        self.assertEqual(f(['Supervisors : <br /> <br />']), [])
        self.assertEqual(f(['<br /> <br />']), [])
        self.assertEqual(f(['<br /> <br /> Pembimbing 2 : Dradjad Irianto,Ir., M.Eng,. <br />']),
                         ['Dradjad Irianto,Ir., M.Eng'])
        idx = LecturerIndex(load_kk())
        self.assertEqual(idx.match("Dr.Ir. Anas Ma\\'ruf")[1], ['sistem_manufaktur'])

    def test_junk_and_scanner_names_dropped(self):
        f = extract_advisor_names
        for junk in ['Neneng', 'Mudjiono', 'Yati Rohmah', 'Editor:', 'Catalogue Link:', 'ena506@yahoo.co.id',
                     'http://webpac.lib.itb.ac.id/index.php?menu=library_detail&ID=55525', '05 Februari 2008',
                     'penulis : ADE GEOVANIA A', 'Pembingbing :', 'Pmbimbing :', 'Theses - Industrial Engineering',
                     'Pedoman Penggunaan Tesis:', 'Scan dewi', 'Neneng@unix.lib.itb.ac.id>']:
            self.assertEqual(f([junk]), [], junk)

    def test_role_prefixes_with_colon(self):
        f = extract_advisor_names
        self.assertEqual(f(['Komisi Pembimbing: Iman Sudirman, Dr., Ir']), ['Iman Sudirman, Dr., Ir'])
        self.assertEqual(f(['Utama: Ida I Dewa Gde Raka, Dr., Ir., MEIE']), ['Ida I Dewa Gde Raka, Dr., Ir., MEIE'])
        self.assertEqual(f(['Ko-Pembimbing: M. Tasrif Arif, Ir., M.Eng']), ['M. Tasrif Arif, Ir., M.Eng'])
        self.assertEqual(f(['Alm. Dr. Ir. TMA. Ari Samadhi (Anggota']), ['Dr. Ir. TMA. Ari Samadhi'])
        self.assertEqual(f(['Ketua Program : Ali Basyah Siregar, Dr. Ir']), ['Ali Basyah Siregar, Dr. Ir'])

    def test_single_surname_must_not_match(self):
        idx = LecturerIndex(load_kk())
        self.assertEqual(idx.match('Hidayat')[2], 'unmapped')          # bukan Yosi Agustina Hidayat
        self.assertEqual(idx.match('Dr.Ir. Ubuh Buchara Hidayat')[2], 'unmapped')
        self.assertEqual(idx.match('Prof. Dr. Rajesri, S.T., M.T')[1], ['sistem_informasi_keputusan'])  # nama depan OK
        self.assertEqual(idx.match('Kadarsah,Dr.Ir')[1], ['sistem_informasi_keputusan'])

    def test_middle_initial(self):
        idx = LecturerIndex(load_kk())
        self.assertEqual(idx.match('Dr. Ir. Herman R. Soetisna, DEA')[1], ['ergonomi_rekayasa_kerja'])
        self.assertEqual(idx.match('Dr.Ir. Herman R Soetisna, DEA')[1], ['ergonomi_rekayasa_kerja'])

    def test_abbreviated_first_name(self):
        idx = LecturerIndex(load_kk())
        k, slugs, m = idx.match('Dr.Moh. MiÃ‚Â’radj Isnaini, ST., MT')
        self.assertEqual((slugs, m), (['sistem_manufaktur'], 'abbrev'))

    def test_mojibake_name(self):
        self.assertEqual(name_key('Dr. Ir. Anas MaÃ‚Â’ruf'), 'anas maruf')
        idx = LecturerIndex(load_kk())
        self.assertEqual(idx.match('Prof. Dr. Ir. Anas MaÃ‚Â’ruf')[1], ['sistem_manufaktur'])
        self.assertEqual(idx.match('Dr. Ir. Drajad Irianto, M. Eng')[1], ['sistem_manufaktur'])


class DetailPage(unittest.TestCase):
    def test_fields(self):
        d = parse_detail((FIX / 'detail_sample.html').read_text(encoding='utf-8'))
        self.assertTrue(d['title'].startswith('EKSPLORASI STRUKTUR FAKTOR NILAI'))
        self.assertNotIn('  ', d['title'])
        self.assertEqual((d['author'], d['nim']), ('G P Chandra Adidharma Yasa', '23424011'))
        self.assertEqual(d['advisors'], ['Prof. Dr. Ir. Joko Siswanto, M.PA.'])
        self.assertIsInstance(d['year'], int)
        self.assertTrue(d['subject'])
        self.assertGreaterEqual(len(d['keywords']), 3)
        self.assertTrue(all(k == k.strip() and k for k in d['keywords']))
        self.assertTrue(d['url'].startswith('https://digilib.itb.ac.id/gdl/view_data/'))
        self.assertTrue(d['abstract'])


class FakeResp:
    def __init__(self, code, text=''):
        self.status_code, self.text = code, text


class FakeSession:
    """rules: fungsi url -> (kode, teks). Mencatat url yang dicoba."""
    def __init__(self, rule):
        self.rule, self.tried = rule, []

    def get(self, url, timeout=0):
        self.tried.append(url)
        return FakeResp(*self.rule(url))


class FetchFallback(unittest.TestCase):
    OK = '<meta property="og:title" content="x">'
    IT = {'url': "https://d/gdl/view_data/a-homel's-model", 'href': "https://d/gdl/view_data/a-homel's-model/?rows=9&per_page=3",
          'ambiguous_url': False}

    def test_safe_url_encodes_apostrophe_and_brackets(self):
        self.assertEqual(safe_url("https://d/gdl/view_data/a-b's-[c]/?rows=1"),
                         'https://d/gdl/view_data/a-b%27s-%5Bc%5D/?rows=1')
        self.assertEqual(safe_url('https://d/x/a%20b'), 'https://d/x/a%20b')  # tidak double-encode

    def test_safe_url_keeps_newline_as_percent_0a(self):
        self.assertEqual(safe_url('https://d/x/a-\nb\tc/?r=1'), 'https://d/x/a-%0Ab%09c/?r=1')

    def test_candidates_order_and_unique(self):
        c = candidates(self.IT)
        self.assertEqual(c[0], self.IT['url'])
        self.assertEqual(c[1], self.IT['href'])
        self.assertEqual(len(c), len(set(c)))
        amb = candidates({**self.IT, 'ambiguous_url': True})
        self.assertEqual(amb[0], self.IT['href'])

    def test_newline_in_raw_href_gets_percent_0a_variant(self):
        it = {'url': 'https://d/gdl/view_data/ab-cd', 'href': 'https://d/gdl/view_data/ab-cd/?rows=9&per_page=3',
              'href_raw': 'https://d/gdl/view_data/ab-\ncd/?rows=9&per_page=3', 'ambiguous_url': False}
        c = candidates(it)
        self.assertIn('https://d/gdl/view_data/ab-%0Acd/?rows=9&per_page=3', c)
        s = FakeSession(lambda u: (200, self.OK) if '%0A' in u else (500, ''))
        html, log = fetch_one(s, it, delay=0)
        self.assertIsNotNone(html)

    def test_slug_variants_drop_special_chars(self):
        v = slug_variants("https://d/gdl/view_data/a-b's-[c]-d")
        self.assertIn('https://d/gdl/view_data/a-bs-c-d', v)
        self.assertIn('https://d/gdl/view_data/a-b-s-c-d', v)
        self.assertEqual(slug_variants('https://d/gdl/view_data/polos-saja'), [])

    def test_400_on_raw_apostrophe_recovers_with_encoded(self):
        s = FakeSession(lambda u: (200, self.OK) if '%27' in u else (400, ''))
        html, log = fetch_one(s, self.IT, delay=0)
        self.assertEqual(html, self.OK)
        self.assertEqual(log[-1], '200')
        self.assertTrue(set(log[:-1]) == {'400'})

    def test_500_on_canonical_falls_back_to_original_href(self):
        it = {'url': 'https://d/gdl/view_data/abc', 'href': 'https://d/gdl/view_data/abc/?rows=9&per_page=3',
              'ambiguous_url': False}
        s = FakeSession(lambda u: (200, self.OK) if 'per_page' in u else (500, ''))
        html, log = fetch_one(s, it, delay=0)
        self.assertIsNotNone(html)
        self.assertEqual(log, ['500', '200'])

    def test_all_variants_fail_reports_statuses(self):
        s = FakeSession(lambda u: (500, ''))
        html, log = fetch_one(s, self.IT, delay=0)
        self.assertIsNone(html)
        self.assertGreaterEqual(len(log), 3)
        self.assertEqual(set(log), {'500'})

    def test_200_error_page_is_not_accepted(self):
        s = FakeSession(lambda u: (200, '<html>Terjadi kesalahan</html>'))
        html, log = fetch_one(s, self.IT, delay=0)
        self.assertIsNone(html)
        self.assertIn('200-bukan-detail', log)


EXTRA = {'anggota_lain': {'sistem_manufaktur': [{'nama': 'Dosen Contoh', 'pola': 'contoh', 'yakin': 0.35}]},
         'tanpa_kk': [{'nama': 'Orang Sbm', 'pola': 'orang sbm', 'alasan': 'dosen sbm'}]}


class Reliability(unittest.TestCase):
    JS = 'Prof. Dr. Ir. Joko Siswanto, M.PA.'   # resmi, manajemen_industri

    @staticmethod
    def _fillers(n=30):
        # tesis pengisi tanpa kata kunci itu, agar IDF kata kunci uji > 0
        return [rec(200 + i, f'Pengisi {i}', [], [f'kata lain {i}']) for i in range(n)]

    def _recs(self, advisor):
        recs = [rec(i, f'Judul netral {i}', [self.JS], ['strategi bisnis']) for i in range(6)]
        recs.append(rec(99, 'Judul netral X', [advisor], ['strategi bisnis']))
        return recs + self._fillers()

    def test_pola_and_tanpa_kk_matching(self):
        idx = LecturerIndex(load_kk(), None, EXTRA)
        k, slugs, m = idx.match('Dr. Ir. Z. Contoh Lain, M.T')
        self.assertEqual((slugs, m, idx.reliability(k)), (['sistem_manufaktur'], 'pola', 0.35))
        self.assertEqual(idx.match('Orang SBM, Dr')[1:], ([], 'tanpa_kk'))
        self.assertEqual(idx.reliability(idx.match(self.JS)[0]), 1.0)

    def test_unsure_dosen_loses_to_conflicting_content(self):
        out, _, _ = run(self._recs('Dosen Contoh'), load_kk(), None, EXTRA)
        o = [x for x in out if x['id'] == '99'][0]
        self.assertEqual(o['memberships'][0]['slug'], 'manajemen_industri')   # ikut konten
        self.assertIn('KK dosen (perkiraan) berbeda dengan konten', o['review_reasons'])
        self.assertEqual(o['dosen_yakin'], 0.35)

    def test_confident_dosen_still_wins(self):
        extra = {'anggota_lain': {'sistem_manufaktur': [{'nama': 'Dosen Contoh', 'pola': 'contoh', 'yakin': 1.0}]}}
        out, _, _ = run(self._recs('Dosen Contoh'), load_kk(), None, extra)
        o = [x for x in out if x['id'] == '99'][0]
        self.assertEqual(o['memberships'][0]['slug'], 'sistem_manufaktur')
        self.assertNotIn('KK dosen (perkiraan) berbeda dengan konten', o['review_reasons'])

    def test_tanpa_kk_goes_by_content_and_is_not_flagged_unmapped(self):
        out, _, _ = run(self._recs('Orang SBM'), load_kk(), None, EXTRA)
        o = [x for x in out if x['id'] == '99'][0]
        self.assertEqual(o['memberships'][0]['slug'], 'manajemen_industri')
        self.assertNotIn('dospem belum ter-map ke KK', o['review_reasons'])

    def test_unsure_lecturer_contributes_less_to_keyword_profile(self):
        # 6 tesis 'Dosen Contoh'(SM, yakin .35) vs 6 tesis resmi MI: keyword tetap condong ke MI
        recs = [rec(i, 'J', ['Dosen Contoh'], ['kata bersama']) for i in range(6)]
        recs += [rec(10 + i, 'J', [self.JS], ['kata bersama']) for i in range(6)]
        recs.append(rec(99, 'J', ['Dosen Tak Dikenal'], ['kata bersama']))
        recs += self._fillers()
        out, _, _ = run(recs, load_kk(), None, EXTRA)
        o = [x for x in out if x['id'] == '99'][0]
        self.assertEqual(o['memberships'][0]['slug'], 'manajemen_industri')


class AbstractFallback(unittest.TestCase):
    JS = 'Prof. Dr. Ir. Joko Siswanto, M.PA.'      # manajemen_industri
    HI = 'Prof. Ir. Hardianto Iridiastadi, MSIE., Ph.D.'   # ergonomi

    def _corpus(self):
        MI = 'kepemimpinan organisasi budaya strategi pemasaran konsumen persaingan bisnis perusahaan'
        ER = 'postur kerja ergonomi beban fisik kelelahan operator antropometri risiko cedera'
        recs = []
        for i in range(8):
            r = rec(i, f'Judul netral {i}', [self.JS], [f'kw mi {i}']); r['abstract'] = MI + f' kasus{i}'
            recs.append(r)
        for i in range(8):
            r = rec(20 + i, f'Judul lain {i}', [self.HI], [f'kw er {i}']); r['abstract'] = ER + f' contoh{i}'
            recs.append(r)
        for i in range(30):
            r = rec(100 + i, f'Pengisi {i}', [f'Tak Dikenal {i}'], [f'kw acak {i}']); r['abstract'] = f'dokumen acak nomor{i} bahasan{i}'
            recs.append(r)
        return recs

    def test_abstract_rescues_thesis_without_advisor_and_keywords(self):
        recs = self._corpus()
        t = rec(999, 'Kajian tanpa petunjuk', [], [])
        t['abstract'] = 'penelitian ini membahas strategi pemasaran konsumen persaingan bisnis perusahaan organisasi budaya kepemimpinan'
        out, _, _ = run(recs + [t], load_kk())
        o = [x for x in out if x['id'] == '999'][0]
        self.assertEqual(o['memberships'][0]['slug'], 'manajemen_industri')
        self.assertIn('abstract', o['memberships'][0]['signals'])
        self.assertIn('tanpa dosen & kata kunci (abstrak+judul)', o['review_reasons'])

    def test_abstract_is_regular_signal_but_dosen_still_decides_with_agreeing_content(self):
        recs = self._corpus()
        out, _, _ = run(recs, load_kk())
        for o in out:
            if o['id'] in ('0', '20'):
                self.assertIn('abstract', o['memberships'][0]['signals'])
                self.assertNotIn('tanpa dosen & kata kunci (abstrak+judul)', o['review_reasons'])

    def test_placeholder_abstracts_are_ignored(self):
        from common import usable_abstract
        for junk in ['P', '-', 'Abstrak bisa dilihat di filenya', 'kelestarian lingkungan', '', None]:
            self.assertIsNone(usable_abstract(junk), junk)
        self.assertIsNotNone(usable_abstract('kata ' * 30))

    def test_too_few_supported_words_gives_no_abstract_signal(self):
        recs = self._corpus()
        t = rec(999, 'zzz qqq', [], [])
        t['abstract'] = 'strategi pemasaran'          # < ABS_MIN_WORDS kata berdukungan
        out, _, _ = run(recs + [t], load_kk())
        o = [x for x in out if x['id'] == '999'][0]
        self.assertEqual(o['memberships'], [])


class Angkatan(unittest.TestCase):
    def test_decode(self):
        self.assertEqual(angkatan_from_nim('23410056'), 2010)
        self.assertEqual(angkatan_from_nim('23424011'), 2024)
        self.assertEqual(angkatan_from_nim('23499001'), 1999)   # YY 70-99 -> 19YY
        self.assertEqual(angkatan_from_nim('23489123'), 1989)

    def test_non_standard_or_future_is_none(self):
        for bad in (None, '', 'S2-758403', '758531', '2819', '23916001', '234160123'):
            self.assertIsNone(angkatan_from_nim(bad), bad)
        self.assertIsNone(angkatan_from_nim('23430001', today_year=2026))   # 2030 > tahun ini


class KnownBad(unittest.TestCase):
    def test_load_known_bad_ignores_comments_and_blank(self):
        import tempfile
        with tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write('# komentar\n\nid-satu\n  id-dua   # catatan\n#id-tiga\n')
        self.assertEqual(load_known_bad(f.name), {'id-satu', 'id-dua'})

    def test_missing_file_is_empty(self):
        self.assertEqual(load_known_bad('/tidak/ada.txt'), set())

    def test_shipped_list_matches_failed_ids(self):
        bad = load_known_bad()
        self.assertGreaterEqual(len(bad), 1)
        self.assertIn('analisis-koordinasi-studi-kasus-pt-x', bad)


class SiteGuards(unittest.TestCase):
    @staticmethod
    def site(n, abstracts=None, review=0):
        abstracts = n if abstracts is None else abstracts
        return {'theses': [{'url': f'u{i}', 'judul': f'J{i}', 'has_abstract': i < abstracts,
                            'perlu_review': i < review} for i in range(n)]}

    def test_sw_cache_bump_keeps_version_and_replaces_hash(self):
        a = "x\nconst CACHE_NAME = 'katalog-tmi-v5';\ny"
        b = bump_sw_cache(a, 'abcdef12')
        self.assertIn("'katalog-tmi-v5-abcdef12'", b)
        self.assertIn("'katalog-tmi-v5-00112233'", bump_sw_cache(b, '00112233'))
        self.assertEqual(bump_sw_cache(b, 'abcdef12'), b)      # idempoten

    def test_growth_is_ok(self):
        old, new = self.site(100), self.site(105)
        c = compare(new, old)
        self.assertEqual((len(c['added']), len(c['removed'])), (5, 0))
        self.assertEqual(problems(new, c), [])

    def test_collapsed_crawl_is_blocked(self):
        old, new = self.site(1000), self.site(700)
        self.assertTrue(any('jumlah tesis turun' in p for p in problems(new, compare(new, old))))

    def test_lost_abstracts_is_blocked(self):
        old, new = self.site(1000, abstracts=900), self.site(1000, abstracts=500)
        self.assertTrue(any('abstrak turun' in p for p in problems(new, compare(new, old))))

    def test_missing_url_is_blocked_and_no_baseline_is_lenient(self):
        new = self.site(10); new['theses'][3]['url'] = ''
        self.assertTrue(any('tanpa judul/url' in p for p in problems(new, compare(new, None), have_old=False)))
        ok = self.site(10)
        self.assertEqual(problems(ok, compare(ok, None), have_old=False), [])

    def test_summary_mentions_counts_and_new_titles(self):
        old, new = self.site(5), self.site(7)
        md = summary(compare(new, old), [], ['3  - "Dosen Baru"'])
        self.assertIn('**7**', md); self.assertIn('+2', md); self.assertIn('J5', md); self.assertIn('Dosen Baru', md)


class RepoHygiene(unittest.TestCase):
    def test_gitignore_does_not_swallow_web_data(self):
        lines = [l.strip() for l in (ROOT / '.gitignore').read_text(encoding='utf-8').splitlines()]
        for bad in ('data', 'data/', '**/data', '**/data/'):
            self.assertNotIn(bad, lines, f'"{bad}" juga mengabaikan web/data/ yang harus di-commit; pakai "/data/"')
        self.assertIn('/data/', lines)

    def test_git_does_not_ignore_web_data(self):
        import shutil
        import subprocess
        if not shutil.which('git'):
            self.skipTest('git tidak tersedia')
        r = subprocess.run(['git', 'check-ignore', '-q', 'web/data/thesis-data.json'], cwd=ROOT)
        if r.returncode == 128:
            self.skipTest('bukan repo git')
        self.assertEqual(r.returncode, 1, 'web/data/thesis-data.json diabaikan oleh .gitignore')


class Keywords(unittest.TestCase):
    def test_trailing_period_and_blanks(self):
        self.assertEqual(split_keywords('Pembelajaran, UMKM Fesyen,  Learning Management System. ,'),
                         ['Pembelajaran', 'UMKM Fesyen', 'Learning Management System'])


class Names(unittest.TestCase):
    def test_name_key(self):
        self.assertEqual(name_key('Dr.Eng. Yosi Agustina Hidayat, S.T., M.T.'), 'yosi agustina hidayat')
        self.assertEqual(name_key('Prof. Dr. Ir. Anas Ma’ruf, M.T., IPM.'), 'anas maruf')
        self.assertEqual(name_key("Prof. Dr. Ir. Anas Ma'ruf"), 'anas maruf')
        self.assertEqual(name_key('Dr. Ir. Herman Rahadian Soetisna, DEA'), 'herman rahadian soetisna')
        self.assertEqual(name_key('Prof. Dr. Ir. Kadarsah Suryadi DEA'), 'kadarsah suryadi')
        self.assertEqual(name_key('Taufiqurrahman S.T., M.S.E'), 'taufiqurrahman')
        self.assertEqual(name_key('G P Chandra Adidharma Yasa'), 'g p chandra adidharma yasa')

    def test_matching(self):
        idx = LecturerIndex(load_kk())
        k, slugs, m = idx.match('Prof. Dr. Ir. Joko Siswanto, M.PA.')
        self.assertEqual((slugs, m), (['manajemen_industri'], 'exact'))
        # typo digilib: tanpa nama belakang
        k, slugs, m = idx.match('Prof. Dr. Rajesri, S.T., M.T.')
        self.assertEqual((slugs, m), (['sistem_informasi_keputusan'], 'subset'))
        self.assertEqual(idx.match('Dosen Luar Negeri, Ph.D.')[2], 'unmapped')

    def test_all_kk_members_unique_and_mapped(self):
        kk = load_kk()
        idx = LecturerIndex(kk)
        for spec in kk.values():
            for nm in [spec['ketua']] + spec['anggota']:
                self.assertEqual(idx.match(nm)[2], 'exact', nm)


def rec(i, title, advisors, keywords):
    return {'id': str(i), 'no': i, 'url': f'u{i}', 'title': title, 'author': 'x', 'nim': None,
            'advisors': advisors, 'year': 2024, 'subject': None, 'keywords': keywords}


class Classify(unittest.TestCase):
    JS = 'Prof. Dr. Ir. Joko Siswanto, M.PA.'      # manajemen_industri
    HI = 'Prof. Ir. Hardianto Iridiastadi, MSIE., Ph.D.'  # ergonomi

    def test_advisor_vector(self):
        v = advisor_vector([('a', 'a', ['x', 'y'], 'exact'), ('b', 'b', ['x'], 'exact'),
                            ('c', None, [], 'unmapped')])
        self.assertAlmostEqual(v['x'], 0.75)
        self.assertAlmostEqual(v['y'], 0.25)
        self.assertIsNone(advisor_vector([('c', None, [], 'unmapped')]))

    def test_single_advisor_wins_and_keywords_learned(self):
        recs = [rec(i, f'Judul netral {i}', [self.HI], ['postur kerja', 'ergonomi']) for i in range(6)]
        recs += [rec(10 + i, f'Judul lain {i}', [self.JS], ['strategi bisnis', 'kepemimpinan']) for i in range(6)]
        # tesis tanpa dospem ter-map: harus ditentukan keyword
        recs.append(rec(99, 'Tanpa dospem', ['Dosen Tak Dikenal'], ['postur kerja']))
        out, _, _ = run(recs, load_kk())
        by = {o['id']: o for o in out}
        self.assertEqual(by['0']['memberships'][0]['slug'], 'ergonomi_rekayasa_kerja')
        self.assertEqual(by['10']['memberships'][0]['slug'], 'manajemen_industri')
        self.assertEqual(by['99']['memberships'][0]['slug'], 'ergonomi_rekayasa_kerja')
        self.assertTrue(by['99']['perlu_review'])
        self.assertIn('dospem belum ter-map ke KK', by['99']['review_reasons'])

    def test_two_advisors_two_kk_gives_secondary(self):
        recs = [rec(0, 'X', [self.JS, self.HI], [])]
        out, _, _ = run(recs, load_kk())
        roles = [m['role'] for m in out[0]['memberships']]
        self.assertEqual(roles, ['utama', 'sekunder'])

    def test_no_signal_is_unclassified(self):
        out, _, _ = run([rec(0, 'zzz qqq', [], [])], load_kk())
        self.assertEqual(out[0]['memberships'], [])
        self.assertTrue(out[0]['perlu_review'])

    def test_scores_are_ints_and_leave_one_out(self):
        # keyword unik milik satu tesis tidak boleh mengangkat tesis itu sendiri
        recs = [rec(0, 'X', [self.JS], ['kata sangat unik'])]
        out, _, _ = run(recs, load_kk())
        sig = out[0]['memberships'][0]['signals']
        self.assertNotIn('keyword', sig)
        self.assertIsInstance(out[0]['memberships'][0]['score'], int)


if __name__ == '__main__':
    unittest.main()
