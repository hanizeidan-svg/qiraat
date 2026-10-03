"""Build the masail database from data/masail/*.yaml.

Outputs (data/out/):
  masail.csv     one row per مسألة
  mawadi.csv     one row per (مسألة × موضع) with the 14 rawi columns  ← the main table
  qiraat_masail.xlsx  both tables as sheets
  qiraat.db      SQLite: matn, masail, readings, mawadi + view jadwal
"""
import csv, json, re, sqlite3, sys, pathlib, difflib
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "out"

RAWIS = ["قالون", "ورش", "البزي", "قنبل", "دوري أبي عمرو", "السوسي", "هشام", "ابن ذكوان",
         "شعبة", "حفص", "خلف", "خلاد", "أبو الحارث", "دوري الكسائي"]
QURRA = {"نافع": RAWIS[0:2], "ابن كثير": RAWIS[2:4], "أبو عمرو": RAWIS[4:6], "ابن عامر": RAWIS[6:8],
         "عاصم": RAWIS[8:10], "حمزة": RAWIS[10:12], "الكسائي": RAWIS[12:14]}
NAMES = {**QURRA, **{r: [r] for r in RAWIS}}

# ---------- Quran text ----------
BASMALA = "بسم الله الرحمن الرحيم"
MARKS = re.compile(r"[ؐ-ًؚ-ٟۖ-ۭـ﻿]")

def skel(s):
    """Rough consonantal skeleton for aligning uthmani with simple-clean tokens."""
    s = s.replace("ٰ", "ا").replace("ٱ", "ا")
    s = MARKS.sub("", s)
    s = re.sub(r"[إأآا]", "ا", s).replace("ى", "ي").replace("ة", "ه")
    return re.sub(r"[ءؤئ]", "", s)

def load_quran():
    def load(name):
        return json.loads((ROOT / "source" / "quran" / f"{name}.json").read_text(encoding="utf8"))["data"]["surahs"]
    simple, uth = load("quran-simple-clean"), load("quran-uthmani")
    Q = {}
    for ss, su in zip(simple, uth):
        sname = MARKS.sub("", su["name"]).replace("سورة ", "").strip()
        for a1, a2 in zip(ss["ayahs"], su["ayahs"]):
            t1, t2 = a1["text"].replace("﻿", "").split(), a2["text"].replace("﻿", "").split()
            if ss["number"] != 1 and a1["numberInSurah"] == 1 and " ".join(t1[:4]) == BASMALA:
                t1, t2 = t1[4:], t2[4:]
            Q[(ss["number"], a1["numberInSurah"])] = {"sura": sname, "simple": t1, "uth": t2}
    return Q

def uth_index(ayah, i):
    """Map simple-token index → uthmani-token index."""
    s, u = ayah["simple"], ayah["uth"]
    if len(s) == len(u):
        return i
    target = skel(s[i])
    guess = round(i * len(u) / len(s))
    cands = range(max(0, guess - 3), min(len(u), guess + 4))
    return max(cands, key=lambda j: difflib.SequenceMatcher(None, target, skel(u[j])).ratio() - abs(j - guess) * 0.01)

# ---------- locating ----------
def locate(m, Q):
    loc = m["loc"]
    excl = [tuple(e) for e in loc.get("exclude", [])]
    hits = []
    if "uthmani" in loc and "search" not in loc and "at" not in loc:      # pure uthmani search
        rx = re.compile(loc["uthmani"])
        for key, ay in Q.items():
            n = 0
            for j, tok in enumerate(ay["uth"]):
                if rx.search(tok):
                    n += 1
                    if key in excl or key + (n,) in excl: continue
                    hits.append((key, j))
        return hits
    rx = re.compile(loc["search"] if "search" in loc else "^" + loc["token"] + "$")
    keys = [tuple(k) for k in loc["at"]] if "at" in loc else list(Q)
    for key in keys:
        ay = Q[key]; n = 0
        for i, tok in enumerate(ay["simple"]):
            if not rx.search(tok): continue
            if "near" in loc and (i == 0 or not re.search(loc["near"], ay["simple"][i - 1])): continue
            j = uth_index(ay, i)
            if "uthmani" in loc and "search" in loc and not re.search(loc["uthmani"], ay["uth"][j]): continue
            if "uthmani_not" in loc and re.search(loc["uthmani_not"], ay["uth"][j]): continue
            n += 1
            if "nth" in loc and n != loc["nth"]: continue
            if key in excl or key + (n,) in excl: continue
            hits.append((key, j))
    return hits

# ---------- readings ----------
def expand(m):
    """→ {rawi: [qiraa, ...]} ; validates names and full coverage."""
    per = {r: [] for r in RAWIS}
    rest = None
    for rd in m["readings"]:
        if rd["by"].strip() == "الباقون":
            rest = rd["qiraa"]; continue
        for name in re.split(r"[،,]\s*", rd["by"]):
            name = name.strip()
            if name not in NAMES: sys.exit(f"{m['id']}: unknown name «{name}»")
            for r in NAMES[name]:
                per[r].append(rd["qiraa"])
    for r in RAWIS:
        if not per[r]:
            if rest is None: sys.exit(f"{m['id']}: rawi «{r}» has no reading")
            per[r].append(rest)
    return per

def summary(per):
    """Group rawis by identical reading and name whole qurra where possible."""
    groups = {}
    for r in RAWIS:
        for q in per[r]: groups.setdefault(q, []).append(r)
    parts = []
    for q, rs in groups.items():
        names, left = [], list(rs)
        for qari, pair in QURRA.items():
            if all(p in left for p in pair):
                names.append(qari); left = [x for x in left if x not in pair]
        names += left
        parts.append(f"{q}: {'، '.join(names) if len(rs) < 14 else 'الجميع'}")
    return " | ".join(parts)

# ---------- main ----------
def main():
    Q = load_quran()
    matn = {v["n"]: v for v in json.loads((ROOT / "data" / "shatibiyya.json").read_text(encoding="utf8"))}
    masail = []
    for f in sorted((ROOT / "data" / "masail").glob("*.yaml")):
        masail += yaml.safe_load(f.read_text(encoding="utf8"))
    ids = [m["id"] for m in masail]
    assert len(ids) == len(set(ids)), "duplicate ids"

    M_ROWS, W_ROWS = [], []
    for m in masail:
        per = expand(m)
        hits = locate(m, Q)
        if not hits: sys.exit(f"{m['id']}: no locations found")
        bayt_text = " ** ".join(f"{matn[n]['sadr']} ... {matn[n]['ajz']}" for n in m["bayt"])
        res = summary(per)
        base = {"id": m["id"], "abyat": "، ".join(map(str, m["bayt"])), "bab": matn[m["bayt"][0]]["bab"],
                "nass_albayt": bayt_text, "qawl": m["qawl"], "rumuz": m.get("rumuz", ""),
                "kalima": m["word"], "nitaq": m["scope"], "natija": res,
                "note": m.get("note", ""), "review": m.get("review", "")}
        M_ROWS.append({**base, "adad_almawadi": len(hits)})
        for (s, a), j in hits:
            ay = Q[(s, a)]
            W_ROWS.append({**base, "sura_no": s, "sura": ay["sura"], "aya_no": a,
                           "aya": " ".join(ay["uth"]), "mawdi": ay["uth"][j],
                           **{r: " / ".join(per[r]) for r in RAWIS}})
        print(f"{m['id']}  {len(hits):4} موضع  {m['word']}")

    OUT.mkdir(parents=True, exist_ok=True)
    AR = {"id": "رقم المسألة", "abyat": "رقم البيت", "bab": "الباب", "nass_albayt": "نص البيت",
          "qawl": "قول الشاطبي", "rumuz": "الرموز", "kalima": "الكلمة", "nitaq": "النطاق",
          "natija": "النتيجة المعمول بها", "note": "ملاحظة", "review": "للمراجعة",
          "adad_almawadi": "عدد المواضع", "sura_no": "رقم السورة", "sura": "السورة",
          "aya_no": "رقم الآية", "aya": "نص الآية", "mawdi": "الكلمة في الآية"}
    m_cols = ["id", "abyat", "bab", "kalima", "nitaq", "adad_almawadi", "qawl", "rumuz", "natija", "note", "review", "nass_albayt"]
    w_cols = ["id", "sura_no", "sura", "aya_no", "aya", "mawdi", "abyat", "qawl", "natija", *RAWIS, "nitaq", "note", "review"]

    def write_csv(path, rows, cols):
        with open(path, "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.writer(fh); w.writerow([AR.get(c, c) for c in cols])
            for r in rows: w.writerow([r[c] for c in cols])
    write_csv(OUT / "masail.csv", M_ROWS, m_cols)
    write_csv(OUT / "mawadi.csv", W_ROWS, w_cols)

    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill
    wb = Workbook()
    for title, rows, cols in [("الجدول", W_ROWS, w_cols), ("المسائل", M_ROWS, m_cols)]:
        ws = wb.active if title == "الجدول" else wb.create_sheet()
        ws.title = title; ws.sheet_view.rightToLeft = True
        ws.append([AR.get(c, c) for c in cols])
        for r in rows: ws.append([r[c] for c in cols])
        for c in ws[1]:
            c.font = Font(bold=True, color="FFFFFF"); c.fill = PatternFill("solid", fgColor="1F4E5F")
        for col in ws.columns:
            letter = col[0].column_letter
            width = min(60, max(8, max(len(str(c.value or "")) for c in col[:200]) * 0.9))
            ws.column_dimensions[letter].width = width
            for c in col[1:]: c.alignment = Alignment(wrap_text=width >= 60, vertical="top")
        ws.freeze_panes = "B2"; ws.auto_filter.ref = ws.dimensions
    wb.save(OUT / "qiraat_masail.xlsx")

    db = OUT / "qiraat.db"
    db.unlink(missing_ok=True)
    con = sqlite3.connect(db)
    con.executescript("""
    CREATE TABLE matn(n INTEGER PRIMARY KEY, bab TEXT, sadr TEXT, ajz TEXT);
    CREATE TABLE masail(id TEXT PRIMARY KEY, abyat TEXT, bab TEXT, kalima TEXT, nitaq TEXT, qawl TEXT,
                        rumuz TEXT, natija TEXT, note TEXT, review TEXT);
    CREATE TABLE readings(masala_id TEXT REFERENCES masail(id), rawi TEXT, qiraa TEXT);
    CREATE TABLE mawadi(masala_id TEXT REFERENCES masail(id), sura_no INT, sura TEXT, aya_no INT, aya TEXT, mawdi TEXT);
    CREATE VIEW jadwal AS SELECT w.sura_no, w.sura, w.aya_no, w.aya, w.mawdi, m.abyat, m.qawl, m.natija, m.id
                          FROM mawadi w JOIN masail m ON m.id = w.masala_id ORDER BY w.sura_no, w.aya_no;
    """)
    con.executemany("INSERT INTO matn VALUES(?,?,?,?)", [(v["n"], v["bab"], v["sadr"], v["ajz"]) for v in matn.values()])
    con.executemany("INSERT INTO masail VALUES(?,?,?,?,?,?,?,?,?,?)",
                    [tuple(r[c] for c in ["id", "abyat", "bab", "kalima", "nitaq", "qawl", "rumuz", "natija", "note", "review"]) for r in M_ROWS])
    for m in masail:
        for r, qs in expand(m).items():
            con.executemany("INSERT INTO readings VALUES(?,?,?)", [(m["id"], r, q) for q in qs])
    con.executemany("INSERT INTO mawadi VALUES(?,?,?,?,?,?)",
                    [(r["id"], r["sura_no"], r["sura"], r["aya_no"], r["aya"], r["mawdi"]) for r in W_ROWS])
    con.commit(); con.close()
    print(f"\n{len(M_ROWS)} مسألة، {len(W_ROWS)} موضع → {OUT}")

if __name__ == "__main__":
    main()
