"""تقطيع المتن (قطع الشاطبية) — the matn cut at masala boundaries with «/», as the commentators print it.

The editable source of truth is data/matn_muqatta.txt: one bayt per line, «N: صدر ... عجز», with « / » at every
cut. Removing the slashes must give back data/shatibiyya.json word for word (checked on every build). Bab
boundaries are implicit cuts. A قطعة is the text between two cuts; it may run across bayts.

  python scripts/qita.py --draft      → (re)generate data/matn_muqatta.txt from the masail quotes (overwrites manual edits!)
                                         farsh: a cut where each masala's quote starts; usul: at the start of that bayt
  python scripts/qita.py --check      → validate the file and print counts
  python scripts/qita.py --review     → docs/QITA_REVIEW.md: unmatched quotes, al-Wafi's quote starts that are not cuts
"""
import re, sys, json, glob, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
MATN = ROOT / "data" / "shatibiyya.json"
QFILE = ROOT / "data" / "matn_muqatta.txt"
SEP = "..."

def load_matn():
    return {v["n"]: v for v in json.loads(MATN.read_text(encoding="utf8"))}

def words(matn):
    """[(bayt, half, word)] for the whole matn in order; half is 0 (صدر) or 1 (عجز)."""
    return [(n, h, w) for n in sorted(matn) for h, part in enumerate((matn[n]["sadr"], matn[n]["ajz"])) for w in part.split()]

_TR = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي", "ؤ": "و", "ئ": "ي", "ة": "ه"})
def key(s):
    """Letters only, hamza/alif forms folded — for matching quotes against the matn."""
    return re.sub(r"[^ا-ي]|ـ", "", s.translate(_TR).replace("ء", ""))

class Index:
    """Character index over the matn letters (no spaces), so quotes match even across a word split between
    hemistichs («النُّبُو ... ءةِ»)."""
    def __init__(self, W):
        self.W, chars, owner, self.first = W, [], [], {}
        for i, (n, _, w) in enumerate(W):
            self.first.setdefault(n, len(chars))
            for c in key(w):
                chars.append(c); owner.append(i)
        self.s, self.owner = "".join(chars), owner
        self.first_word = {}
        for i, (n, _, _) in enumerate(W): self.first_word.setdefault(n, i)

    def find_in(self, quote, bayts):
        """Like find(), but only inside the masala's own bayts (a quote may run into the next listed bayt)."""
        bs = sorted(set(bayts))
        for b in bs:
            sp = self.find(quote, b, b + 1 if b + 1 in bs else b)
            if sp: return sp
        return None

    def find(self, quote, lo, hi):
        """Word span (i, j) of `quote` inside bayts lo..hi, or None."""
        q = key(quote)
        if not q or lo not in self.first: return None
        a = self.first[lo]
        b = self.first.get(hi + 1, len(self.s))
        k = self.s.find(q, a, b)
        return (self.owner[k], self.owner[k + len(q) - 1]) if k >= 0 else None

def quote_parts(qawl):
    return [p.strip() for p in re.split(r"\.\.\.|…", qawl or "") if key(p)]

def masail():
    import yaml
    for f in sorted(glob.glob(str(ROOT / "data" / "masail" / "*.yaml"))):
        for m in yaml.safe_load(open(f, encoding="utf8")) or []:
            yield m

# ---------- the file ----------
def render(matn, cuts):
    W = words(matn)
    out, i = [], 0
    for n in sorted(matn):
        halves = [[], []]
        while i < len(W) and W[i][0] == n:
            if i in cuts: halves[W[i][1]].append("/")
            halves[W[i][1]].append(W[i][2]); i += 1
        out.append(f"{n}: {' '.join(halves[0])} {SEP} {' '.join(halves[1])}")
    return "\n".join(out) + "\n"

def parse(matn=None):
    """→ (W, cuts): cuts = set of word indices that start a qita (explicit «/» only)."""
    matn = matn or load_matn()
    W = words(matn)
    cuts, i, seen = set(), 0, set()
    for ln, line in enumerate(QFILE.read_text(encoding="utf8").splitlines(), 1):
        if not line.strip(): continue
        m = re.match(r"(\d+):\s*(.*)$", line)
        if not m: raise SystemExit(f"matn_muqatta.txt:{ln}: expected «N: ...»")
        n = int(m.group(1))
        if n not in matn or n in seen: raise SystemExit(f"matn_muqatta.txt:{ln}: bad or repeated bayt {n}")
        seen.add(n)
        halves = m.group(2).split(SEP)
        if len(halves) != 2: raise SystemExit(f"matn_muqatta.txt:{ln}: bayt {n} needs exactly one «{SEP}»")
        for h, part in enumerate(halves):
            pending = False
            for tok in part.split():
                if tok == "/": pending = True; continue
                if i >= len(W) or W[i][:2] != (n, h) or W[i][2] != tok:
                    exp = W[i] if i < len(W) else None
                    raise SystemExit(f"matn_muqatta.txt:{ln}: bayt {n}: «{tok}» ≠ matn {exp} — only «/» may be added")
                if pending: cuts.add(i); pending = False
                i += 1
            if pending: raise SystemExit(f"matn_muqatta.txt:{ln}: bayt {n}: «/» at the end of a hemistich — put it before the next word")
    if i != len(W): raise SystemExit(f"matn_muqatta.txt: ends early at {W[i]}")
    return W, cuts

def segments(matn, W, cuts):
    """[(id, bab, i_from, i_to)] — cuts plus bab boundaries."""
    starts = set(cuts) | {0}
    for i in range(1, len(W)):
        if matn[W[i][0]]["bab"] != matn[W[i - 1][0]]["bab"]: starts.add(i)
    starts = sorted(starts)
    return [(k + 1, matn[W[a][0]]["bab"], a, (starts[k + 1] if k + 1 < len(starts) else len(W)) - 1) for k, a in enumerate(starts)]

def seg_text(W, a, b):
    """Text of words a..b with «...» between hemistichs and «**» between bayts."""
    out = []
    for i in range(a, b + 1):
        if i > a and W[i][0] != W[i - 1][0]: out.append("**")
        elif i > a and W[i][1] != W[i - 1][1]: out.append(SEP)
        out.append(W[i][2])
    return " ".join(out)

def word_pos(W):
    """global index → position inside its bayt (0-based over sadr+ajz)."""
    pos, last, k = [], None, 0
    for n, _, _ in W:
        k = k + 1 if n == last else 0
        pos.append(k); last = n
    return pos

def link(matn, W, segs, M):
    """masala id → [(qita_id, exact)] from its quote parts; falls back to every qita touching its bayts."""
    idx = Index(W)
    seg_of = {}
    for sid, _, a, b in segs:
        for i in range(a, b + 1): seg_of[i] = sid
    out, missing = {}, []
    for m in M:
        bs = sorted(m.get("bayt") or [])
        if not bs: continue
        found = []
        for p in quote_parts(m.get("qawl")):
            sp = idx.find_in(p, bs)
            if sp: found.append(sp)
        if found:
            ids = sorted({seg_of[i] for a, b in found for i in range(a, b + 1)})
            out[m["id"]] = [(s, 1) for s in ids]
        else:
            missing.append(m["id"])
            ids = sorted({seg_of[i] for i, (n, _, _) in enumerate(W) if n in bs})
            out[m["id"]] = [(s, 0) for s in ids]
    return out, missing

# ---------- commands ----------
def draft():
    matn = load_matn(); W = words(matn); idx = Index(W)
    cuts = set()
    for m in masail():
        bs = sorted(m.get("bayt") or [])
        parts = quote_parts(m.get("qawl"))
        if not bs or not parts: continue
        if re.match(r"^\d+-\d", m["id"]):          # farsh: cut exactly where the quote starts
            sp = idx.find_in(parts[0], bs)
            if sp and sp[0] > 0: cuts.add(sp[0])
        else:                                         # usul: quotes pick rule fragments — cut at the start of each quoted bayt
            for p in parts:
                sp = idx.find_in(p, bs)
                if sp and idx.first_word[W[sp[0]][0]] > 0: cuts.add(idx.first_word[W[sp[0]][0]])
    # a cut on a bayt's first word is redundant only at a bab start (implicit); keep the rest
    QFILE.write_text(render(matn, cuts), encoding="utf8")
    print(f"{len(cuts)} cuts → {QFILE.relative_to(ROOT)}")

def wafi_quotes():
    """(bayt, quote) for every «قوله (...)» / «(...)» quote al-Wafi makes from the bayt it is commenting."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import wafi
    for n, _, t in wafi.segments():
        for q in re.findall(r"\(([^()]{3,80})\)", t):
            # a masala usually opens with «و/ف…» and a few words; one-word quotes are rumuz glosses
            if len(q.split()) >= 3 and re.match(r"[وف]", q.strip()) and not re.search(r"\d", q): yield n, q

def review():
    matn = load_matn(); W, cuts = parse(matn); segs = segments(matn, W, cuts)
    M = list(masail())
    links, missing = link(matn, W, segs, M)
    idx = Index(W); pos = word_pos(W)
    bab_start = {a for _, _, a, _ in segs}
    sug = {}
    for n, q in wafi_quotes():
        sp = idx.find(q, n, n)
        if not sp: continue
        i = sp[0]
        if i in cuts or i in bab_start or pos[i] == 0: continue      # already a cut, or the bayt's first word
        sug.setdefault(n, set()).add(i)
    lines = ["# مراجعة تقطيع المتن", "",
             "مولَّد بـ `python scripts/qita.py --review`. الملف المرجع: `data/matn_muqatta.txt` (الشرطة « / » عند حدود المسائل).", "",
             f"- القطع: {len(segs)} (منها {len(cuts)} قطعًا صريحًا، والباقي حدود أبواب).",
             f"- مسائل لم يُعثر على شاهدها في المتن حرفيًّا: {len(missing)} — رُبطت بقطع أبياتها كلها حتى يُصحَّح شاهدها.", ""]
    if missing:
        lines += ["## مسائل لم يطابق شاهدها المتن", "", "| المسألة | الشاهد (`qawl`) |", "|---|---|"]
        mm = {m["id"]: m for m in M}
        lines += [f"| {i} | {mm[i].get('qawl', '')[:90]} |" for i in missing] + [""]
    lines += ["## مواضع يقتبس الوافي منها ولا قطع عندها", "",
              "اقتباسات «قوله (...)» من وسط البيت: قد تكون حدَّ مسألة لم يُقطع عنده، أو مجرد شرح لكلمة. تُراجع ولا تُطبَّق آليًّا.", "",
              "| البيت | النص بعلامة مقترحة |", "|---|---|"]
    for n in sorted(sug):
        toks, i0 = [], next(k for k, w in enumerate(W) if w[0] == n)
        k = i0
        while k < len(W) and W[k][0] == n:
            if k > i0 and W[k][1] != W[k - 1][1]: toks.append(SEP)
            if k in cuts: toks.append("/")
            if k in sug[n]: toks.append("**⁄**")
            toks.append(W[k][2]); k += 1
        lines.append(f"| {n} | {' '.join(toks)} |")
    (ROOT / "docs" / "QITA_REVIEW.md").write_text("\n".join(lines) + "\n", encoding="utf8")
    print(f"{len(segs)} qita, {len(missing)} unmatched quotes, {sum(map(len, sug.values()))} al-Wafi suggestions in {len(sug)} bayts → docs/QITA_REVIEW.md")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "--draft": draft()
    elif cmd == "--check":
        matn = load_matn(); W, cuts = parse(matn); segs = segments(matn, W, cuts)
        print(f"ok: {len(W)} words, {len(cuts)} cuts, {len(segs)} qita")
    elif cmd == "--review": review()
    else: sys.exit(__doc__)
