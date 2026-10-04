"""Cache a Shamela book locally (reference only; source/books/ is git-ignored — do not publish).
   python scripts/fetch_book.py 38075 source/books/wafi
"""
import sys, re, html, time, json, pathlib, urllib.request
book, out = sys.argv[1], pathlib.Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
def get(n):
    req = urllib.request.Request(f"https://shamela.ws/book/{book}/{n}", headers={"User-Agent": "Mozilla/5.0 (research cache)"})
    return urllib.request.urlopen(req, timeout=60).read().decode("utf8")
first = get(1)
last = max(int(x) for x in re.findall(rf"/book/{book}/(\d+)", first))
pages = {}
for n in range(1, last + 1):
    f = out / f"{n:04d}.txt"
    if f.exists(): continue
    for attempt in range(3):
        try:
            t = get(n); break
        except Exception as e:
            time.sleep(5)
    else:
        print("failed", n); continue
    title = re.search(r"<title>(.*?)</title>", t, re.S)
    m = re.search(r'<div class="nass[^"]*"[^>]*>(.*?)</div>\s*</div>', t, re.S) or re.search(r'<div class="nass[^"]*"[^>]*>(.*)', t, re.S)
    body = re.sub(r"<br\s*/?>|</p>", "\n", m.group(1)) if m else ""
    body = html.unescape(re.sub(r"<[^>]+>", "", body))
    f.write_text((html.unescape(title.group(1)).strip() if title else "") + "\n\n" + body.strip(), encoding="utf8")
    time.sleep(1.2)
print("done", last)
