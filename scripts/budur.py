"""Read «البدور الزاهرة» (عبد الفتاح القاضي) from the local cache in source/books/budur
(fetched with scripts/fetch_book.py 57; reference only — the cache is git-ignored and must not be published).

  python scripts/budur.py --sections          → section titles with their page ranges (several suras may share one)
  python scripts/budur.py --pages 25 30       → book pages 25–30
  python scripts/budur.py --quarters 2        → the hizb-quarters (أرباع) of sura 2 with their aya ranges
  python scripts/budur.py --search <words>    → diacritic-insensitive search with page numbers
"""
import re, sys, json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
CACHE = ROOT / "source" / "books" / "budur"
NAV = re.compile(r"\s*تحميل الصفحة التالية.*?اذهب", re.S)

def pages():
    """→ [(page_label, section_title, text)] in book order."""
    out = []
    for f in sorted(CACHE.glob("*.txt")):
        t = f.read_text(encoding="utf8")
        head, _, body = t.partition("\n")
        m = re.match(r"(?:ج\d+\s*-\s*)?(?:ملحق\s*-\s*)?ص(\d+)\s*-\s*كتاب[^-]*-\s*(.*?)\s*-\s*المكتبة الشاملة", head)
        page = m.group(1) if m else f.stem
        title = m.group(2).strip() if m else ""
        out.append((page, title, NAV.sub(" ", body).strip()))
    return out

def norm(s):
    s = re.sub(r"[ؐ-ًؚ-ٰٟۖ-ۭـ]", "", s)
    return re.sub(r"[إأآٱ]", "ا", s).replace("ى", "ي").replace("ة", "ه")

def sections():
    """Shamela's section titles with their page ranges: [(title, first_page, last_page)].
    Titles are not one-per-sura (several suras share a section), so agents read pages by range."""
    P = [(int(p), t) for p, t, _ in pages() if p.isdigit()]
    out = []
    for p, t in P:
        if out and out[-1][0] == t:
            out[-1][2] = p
        else:
            out.append([t, p, p])
    return [tuple(x) for x in out]

def quarters(n):
    d = json.loads((ROOT / "source" / "quran" / "quran-simple-clean.json").read_text(encoding="utf8"))["data"]["surahs"]
    qs = {}
    for s in d:
        for a in s["ayahs"]:
            qs.setdefault(a["hizbQuarter"], []).append((s["number"], a["numberInSurah"]))
    return {q: (v[0], v[-1]) for q, v in qs.items() if any(x[0] == n for x in v)}

if __name__ == "__main__":
    if len(sys.argv) < 2: sys.exit(__doc__)
    cmd = sys.argv[1]
    if cmd == "--sections":
        for t, a, b in sections(): print(f"ص{a}–{b}\t{t}")
    elif cmd == "--pages":
        a, b = int(sys.argv[2]), int(sys.argv[3]) if len(sys.argv) > 3 else int(sys.argv[2])
        for p, t, x in pages():
            if p.isdigit() and a <= int(p) <= b: print(f"===== البدور ص{p} — {t}\n{x}\n")
    elif cmd == "--quarters":
        for q, (s, e) in sorted(quarters(int(sys.argv[2])).items()):
            print(f"الربع {q}: {s[0]}:{s[1]} → {e[0]}:{e[1]}")
    elif cmd == "--search":
        term = norm(" ".join(sys.argv[2:]))
        for p, t, x in pages():
            nx = norm(x)
            for m in re.finditer(re.escape(term), nx):
                print(f"--- ص{p} ({t})\n{nx[max(0, m.start() - 200):m.start() + 300]}\n")
    else:
        sys.exit(__doc__)
