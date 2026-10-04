"""Look up al-Wafi's commentary (عبد الفتاح القاضي) on a bayt, from the local cache in source/books/wafi
(fetched with scripts/fetch_book.py; reference only — the cache is git-ignored and must not be published).

  python scripts/wafi.py 740            → the commentary on bayt 740 (with its page numbers)
  python scripts/wafi.py 740 742        → bayts 740–742
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

def lookup(a, b=None):
    b = b or a
    out = [(n, p, t) for n, p, t in segments() if a <= n <= b]
    return out

if __name__ == "__main__":
    if len(sys.argv) < 2: sys.exit(__doc__)
    a = int(sys.argv[1]); b = int(sys.argv[2]) if len(sys.argv) > 2 else a
    res = lookup(a, b)
    if not res: sys.exit(f"bayt {a} not found in cache")
    for n, p, t in res:
        print(f"===== البيت {n} — الوافي ص{p}\n{t}\n")
