"""Look up al-Wafi's commentary (عبد الفتاح القاضي) on a bayt, from the local cache in source/books/wafi
(fetched with scripts/fetch_book.py; reference only — the cache is git-ignored and must not be published).

  python scripts/wafi.py 740            → the commentary on bayt 740 (with its page numbers)
  python scripts/wafi.py 740 742        → bayts 740–742 (a bayt commented together with the following ones is followed to its commentary)
  python scripts/wafi.py --search النَّاس  → diacritic-insensitive search with page numbers
"""
import re, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
CACHE = ROOT / "source" / "books" / "wafi"
AR = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
HEAD = re.compile(r"^\s*([٠-٩]{1,4})\s*-\s*\S")     # «٩٧ - وقد ذكروا ...» starts a bayt

def segments():
    """Yield (bayt_no, page_label, text) for every commented bayt, in book order."""
    cur_n, cur_page, buf = None, None, []
    for f in sorted(CACHE.glob("*.txt")):
        lines = f.read_text(encoding="utf8").splitlines()
        page = re.match(r"ص(\d+)", lines[0]).group(1) if lines and re.match(r"ص\d+", lines[0]) else f.stem
        for line in lines[2:]:
            m = HEAD.match(line)
            if m:
                if cur_n is not None:
                    yield cur_n, cur_page, "\n".join(buf).strip()
                cur_n, cur_page, buf = int(m.group(1).translate(AR)), page, [line]
            elif cur_n is not None:
                buf.append(line)
    if cur_n is not None:
        yield cur_n, cur_page, "\n".join(buf).strip()

NAV = re.compile(r"\s*تحميل الصفحة التالية.*?اذهب", re.S)

def lookup(a, b=None):
    """Segments for bayts a..b. Al-Wafi often quotes several bayts and comments on them together after the
    last one: if a requested bayt has no commentary of its own, the following segments are added up to the
    first one that has commentary."""
    b = b or a
    segs = [(n, p, NAV.sub(" ", t)) for n, p, t in segments()]
    idx = [i for i, (n, _, _) in enumerate(segs) if a <= n <= b]
    if not idx: return []
    last = idx[-1]
    while last + 1 < len(segs) and len(segs[last][2].splitlines()) <= 1:
        last += 1
    return segs[idx[0]:last + 1]

def search(term):
    """Diacritic-insensitive search → [(page, snippet)]."""
    strip = lambda s: re.sub(r"[ً-ْٰـ]", "", s)
    term = strip(term)
    out = []
    for f in sorted(CACHE.glob("*.txt")):
        t = strip(NAV.sub(" ", f.read_text(encoding="utf8")))
        page = re.match(r"ص(\d+)", t).group(1) if re.match(r"ص\d+", t) else f.stem
        for m in re.finditer(re.escape(term), t):
            out.append((page, t[max(0, m.start() - 200):m.start() + 300].replace("\n", " ")))
    return out

if __name__ == "__main__":
    if len(sys.argv) < 2: sys.exit(__doc__)
    if sys.argv[1] == "--search":
        for p, s in search(" ".join(sys.argv[2:])): print(f"--- ص{p}\n{s}\n")
        sys.exit()
    a = int(sys.argv[1]); b = int(sys.argv[2]) if len(sys.argv) > 2 else a
    res = lookup(a, b)
    if not res: sys.exit(f"bayt {a} not found in cache")
    for n, p, t in res:
        print(f"===== البيت {n} — الوافي ص{p}\n{t}\n")
