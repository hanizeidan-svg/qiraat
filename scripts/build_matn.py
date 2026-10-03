"""Build data/shatibiyya.json + .csv: 1173 verses (vocalized) with chapter (باب) assigned.
Base text: me7me7/Shatibiya (الشاطبي.txt, cp1256). Chapters: ar.wikisource (unvocalized), aligned by fuzzy match."""
import re, json, csv, difflib, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "source"

def norm(s):
    s = re.sub(r"[ً-ْٰـ]", "", s)          # tashkeel, dagger alef, tatweel
    s = re.sub(r"[إأآٱا]", "ا", s).replace("ى", "ي").replace("ة", "ه").replace("ؤ", "و").replace("ئ", "ي")
    return re.sub(r"[^ء-ي ]", " ", s).split()

verses = []
for line in (SRC / "me7_shatibi.txt").read_bytes().decode("cp1256").splitlines():
    n, rest = line.split("\t", 1)
    parts = [p.strip() for p in rest.split("\t") if p.strip()]
    verses.append({"n": int(n), "sadr": parts[0], "ajz": parts[1] if len(parts) > 1 else ""})
assert [v["n"] for v in verses] == list(range(1, 1174))
for n, fix in json.loads((ROOT / "data" / "text_corrections.json").read_text(encoding="utf8")).items():
    v = verses[int(n) - 1]
    v.update({k: fix[k] for k in ("sadr", "ajz") if k in fix})
    v["corrected"] = fix["reason"]

# wikisource: sequence of (heading_or_None, verse_text)
wiki = []
heading = "خطبة الكتاب"
for f in ["intro_wikisource.wiki", "shatibiyya_wikisource.wiki"]:
    for l in (SRC / f).read_text(encoding="utf8").splitlines():
        m = re.match(r"^=+\s*(.+?)\s*=+$", l.strip())
        if m: heading = m.group(1); continue
        if "\\\\" in l:
            wiki.append((heading, l.replace("{{أبيات|", "").replace("}}", "")))

# align by word sequences (diff over verse-level normalized strings)
a = [" ".join(norm(v["sadr"] + " " + v["ajz"])) for v in verses]
b = [" ".join(norm(t)) for _, t in wiki]
sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
idx = [None] * len(a)
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag == "equal":
        for k in range(i2 - i1): idx[i1 + k] = j1 + k
    elif tag == "replace":
        for k in range(i2 - i1):
            best = max(range(j1, j2), key=lambda j: difflib.SequenceMatcher(None, a[i1 + k], b[j]).ratio())
            if difflib.SequenceMatcher(None, a[i1 + k], b[best]).ratio() > 0.5: idx[i1 + k] = best
cur = "خطبة الكتاب"; unmatched = []
for v, j in zip(verses, idx):
    if j is None: unmatched.append(v["n"])
    else: cur = wiki[j][0]
    v["bab"] = cur.replace("{{ص}}", "ﷺ")
print("wiki verses:", len(wiki), "unmatched base verses:", unmatched)

out = ROOT / "data"; out.mkdir(exist_ok=True)
(out / "shatibiyya.json").write_text(json.dumps(verses, ensure_ascii=False, indent=1), encoding="utf8")
with open(out / "shatibiyya.csv", "w", encoding="utf-8-sig", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=["n", "bab", "sadr", "ajz", "corrected"]); w.writeheader(); w.writerows(verses)
from collections import OrderedDict
c = OrderedDict()
for v in verses: c.setdefault(v["bab"], [v["n"], v["n"]])[1] = v["n"]
for k, (s, e) in c.items(): print(f"{s:5}-{e:5}  {k}")
