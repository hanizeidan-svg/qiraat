"""Cache a ketabonline.com book as text (reference only; source/books/ is git-ignored — do not publish).
   python scripts/fetch_ketab.py 24602 source/books/idaa_text
"""
import sys, re, json, html, time, pathlib, urllib.request

def get(book, page):
    url = f"https://ketabonline.com/ar/books/{book}/read?page={page}&part=1"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (research cache)"})
    return urllib.request.urlopen(req, timeout=60).read().decode("utf8", "ignore")

def page_text(raw):
    m = re.search(r'content:"((?:[^"\\]|\\.)*)"', raw)
    if not m:
        return None
    s = json.loads('"' + m.group(1) + '"')
    s = re.sub(r"</p>|<br\s*/?>", "\n", s)
    s = re.sub(r'<a [^>]*class="g-copy"[^>]*>.*?</a>', "", s, flags=re.S)
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()

def main():
    book, out = sys.argv[1], pathlib.Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    first = get(book, 1)
    cands = [int(x) for x in re.findall(r"page=(\d+)", first)]
    m = re.search(r"pages?_count\D{0,5}(\d+)|total_pages\D{0,5}(\d+)|last_page\D{0,5}(\d+)", first)
    last = int(next(g for g in m.groups() if g)) if m else None
    n, empty = 1, 0
    while True:
        f = out / f"{n:04d}.txt"
        if not f.exists():
            raw = first if n == 1 else None
            for _ in range(3):
                try:
                    raw = raw or get(book, n); break
                except Exception:
                    time.sleep(5)
            t = page_text(raw) if raw else None
            if not t:
                empty += 1
                if (last and n >= last) or empty >= 3:
                    break
            else:
                empty = 0
                f.write_text(t, encoding="utf8")
            time.sleep(1.2)
        n += 1
        if last and n > last:
            break
    print("done", n - 1, "pages")

if __name__ == "__main__":
    main()
