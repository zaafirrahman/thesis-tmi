"""Normalisasi nama dosen & pencocokan ke config/kk.yaml."""
import re
import unicodedata
from difflib import SequenceMatcher

import yaml

from common import CONFIG

TITLES = {'prof', 'dr', 'ir', 'drs', 'dra', 'eng', 'ing', 'h', 'hj', 'dipl'}
DEGREES = {'dea', 'ipm', 'ipu', 'msie', 'mpa', 'mba', 'msc', 'mt', 'st', 'phd', 'ssi'}
KK_META = ('label', 'abbr', 'color', 'color_dark')


_MOJIBAKE = re.compile(r'(?:[ÃÂ][\u0080-\u00bf\u2013-\u203a]*)+')


def _fold(s):
    """Buang sisa encoding rusak ('MaÃ‚Â’ruf' -> 'Maruf') & lipat aksen ke ASCII."""
    s = _MOJIBAKE.sub('', s)
    return unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii')


def name_key(raw):
    """'Dr.Eng. Yosi Agustina Hidayat, S.T., M.T.' -> 'yosi agustina hidayat'."""
    s = _fold((raw or '').strip()).strip()
    had_comma = ',' in s
    s = s.split(',', 1)[0].lower()
    for ch in "’'`":
        s = s.replace(ch, '')
    toks = [t for t in re.split(r'[\s.]+', s) if t]
    while toks and toks[0] in TITLES:
        toks.pop(0)
    if not had_comma:
        while toks and toks[-1] in DEGREES:
            toks.pop()
    # sisa gelar bertitik tanpa koma di depannya, mis. 'Taufiqurrahman S.T.' -> 's','t'
    while len(toks) > 1 and len(toks[-1]) == 1:
        toks.pop()
    return ' '.join(toks)


_PREFIX = re.compile(r'(?i)^\s*(?:dosen\s+)?(?:pembimbing|promotor|supervisors?)\s*\d*\s*:?\s*')
# gelar belakang yang langsung disusul gelar depan nama berikutnya = dua nama menempel
_GLUED = re.compile(r'(?i)\b(m\.?\s?sc|m\.?\s?t|s\.?\s?t|ph\.?\s?d|dea|m\.?\s?eng|msie|mpa)\.?,?\s+(?=(?:prof|dr|ir)\.?\s)')


# bukan dosen: petugas scan/editor perpustakaan yang tercampur di kolom pembimbing
NON_ADVISORS = {'neneng', 'yati rohmah', 'mudjiono', 'dewi', 'korry', 'kory', 'ena sukmana',
                'scan', 'scan dewi', 'editor'}
_JUNK_SUBSTR = ('tesis', 'theses', 'programme', 'perpustakaan', 'dipublikasikan', 'ketentuan',
                'penulis', 'catalogue', 'sumber dokumen', 'pedoman', 'kebiasaan', 'http', 'www.', '@')
_ROLE_PREFIX_DROP = ('penulis', 'editor', 'catalogue', 'sumber')


def _is_junk(part):
    low = part.lower()
    return (any(j in low for j in _JUNK_SUBSTR) or re.search(r'\d', part) is not None
            or len(part.split()) > 12 or name_key(part) in NON_ADVISORS)


def extract_advisor_names(raw_list):
    """Bersihkan string dospem tesis lama menjadi daftar nama murni. Menangani: tag HTML
    (<br>, <p>), 'Pembimbing [2] :', 'Supervisors :', '(1)', '(ITB)', '(Nama)', 'Scanner: X',
    tanggal, placeholder '#..#', dan dua nama yang menempel dalam satu string."""
    out = []
    for raw in raw_list or []:
        s = re.sub(r'(?i)<\s*(?:br|p)\b[^>]*>|</\s*p\s*>', ';', raw or '')
        s = re.sub(r'<[^>]+>', '', s).replace('&nbsp;', ' ').replace('\\', '')
        for chunk in s.split(';'):
            chunk = re.sub(r'(?i)\bscan(?:ner)?\s*:.*$', '', chunk)
            chunk = _PREFIX.sub('', chunk)
            chunk = re.sub(r'\b\d{4}-\d{2}-\d{2}\b\.?', '', chunk)
            chunk = re.sub(r'\(\s*\d+\s*\)|\(\s*[A-Z]{2,6}\s*\)', '', chunk)   # (1) (ITB) (CYCU)
            chunk = _GLUED.sub(lambda m: m.group(0).rstrip() + ';', chunk)
            chunk = re.sub(r'(?i),?\s+(?:dan|and|&)\s+', ';', chunk)    # 'A, Dr., dan B, M.T'
            for piece in chunk.split(';'):
                for part in re.split(r'\s*\b\d+\s*\.\s*(?=[A-Za-z])', piece):
                    part = _PREFIX.sub('', part)
                    if ':' in part:                       # 'Komisi Pembimbing: X', 'Utama: X', 'I : X'
                        pre, rest = part.split(':', 1)
                        if any(w in pre.lower() for w in _ROLE_PREFIX_DROP):
                            continue
                        if len(pre.split()) <= 4 and not re.search(r'(?i)\b(prof|dr|ir)\b', pre):
                            part = rest
                    part = re.sub(r'\([^)]*$', '', part)                  # '(Anggota' menggantung
                    part = re.sub(r'(?i)^\s*alm\.?\s+', '', part)           # almarhum
                    part = part.strip(' .,;()')
                    if '#' in part or _is_junk(part):
                        continue
                    if len(re.sub(r'[^A-Za-z]', '', part)) >= 3 and part not in out:
                        out.append(part)
    return out


def load_kk(path=None):
    """Return dict slug -> {label, abbr, color, color_dark, ketua, anggota}."""
    with open(path or CONFIG / 'kk.yaml', encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_aliases(path=None):
    p = path or CONFIG / 'advisor_aliases.yaml'
    try:
        with open(p, encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
    except FileNotFoundError:
        data = {}
    return {name_key(k): name_key(v) for k, v in data.items()}


class LecturerIndex:
    """Peta nama (kunci ternormalisasi) -> daftar slug KK."""

    def __init__(self, kk, aliases=None):
        self.aliases = aliases or {}
        self.kks = {}       # key -> [slug,...]
        self.display = {}   # key -> nama tampilan
        for slug, spec in kk.items():
            for nm in [spec.get('ketua')] + list(spec.get('anggota') or []):
                if not nm:
                    continue
                key = name_key(nm)
                self.kks.setdefault(key, [])
                if slug not in self.kks[key]:
                    self.kks[key].append(slug)
                self.display.setdefault(key, nm)

    def match(self, raw):
        """Return (key|None, [slug], metode)."""
        key = name_key(raw)
        key = self.aliases.get(key, key)
        if key in self.kks:
            return key, self.kks[key], ('alias' if name_key(raw) in self.aliases else 'exact')
        dt = key.split()
        toks = set(dt)
        if toks:
            cands = []
            for k in self.kks:
                kt = k.split()
                if toks <= set(kt):
                    # kata tunggal ('Hidayat') hanya sah bila itu NAMA DEPAN ('Rajesri', 'Kadarsah')
                    if len(dt) >= 2 or kt[0] == key:
                        cands.append(k)
                elif set(kt) <= toks:
                    cands.append(k)
            if len(cands) == 1:
                return cands[0], self.kks[cands[0]], 'subset'
            # singkatan awalan: 'moh miradj isnaini' -> 'mohammad miradj isnaini'
            if len(dt) >= 3:
                ab = []
                for k in self.kks:
                    kt = k.split()
                    ok = all(any(t == x or x.startswith(t) for x in kt) for t in dt)   # inisial 'R' / 'Moh' ok
                    if ok and sum(1 for t in dt if t in kt) >= 2:
                        ab.append(k)
                if len(ab) == 1:
                    return ab[0], self.kks[ab[0]], 'abbrev'
        best, best_r = None, 0.0
        for k in self.kks:
            r = SequenceMatcher(None, key, k).ratio()
            if r > best_r:
                best, best_r = k, r
        if best and best_r >= 0.9:
            return best, self.kks[best], 'fuzzy'
        return None, [], 'unmapped'
