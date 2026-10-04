"""Build the masail database from data/masail/*.yaml.

Outputs (data/out/):
  qiraat_masail.xlsx  sheets: القراءات (long, one row per موضع × راوٍ × وجه) ← the core table
                              الجدول (wide, one row per موضع with 14 rawi columns), المسائل
  qiraat.csv / jadwal.csv / masail.csv
  qiraat.db   SQLite: matn, masail, mawadi, qiraat (+ view riwaya)
"""
import csv, json, re, sqlite3, sys, pathlib, difflib
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "out"

RAWIS = ["قالون", "ورش", "البزي", "قنبل", "دوري أبي عمرو", "السوسي", "هشام", "ابن ذكوان",
         "شعبة", "حفص", "خلف", "خلاد", "أبو الحارث", "دوري الكسائي"]
QURRA = {"نافع": RAWIS[0:2], "ابن كثير": RAWIS[2:4], "أبو عمرو": RAWIS[4:6], "ابن عامر": RAWIS[6:8],
         "عاصم": RAWIS[8:10], "حمزة": RAWIS[10:12], "الكسائي": RAWIS[12:14]}
QARI_OF = {r: q for q, rs in QURRA.items() for r in rs}
NAMES = {**QURRA, **{r: [r] for r in RAWIS}}
WASL, WAQF, BOTH = "وصلًا", "وقفًا", "وصلًا ووقفًا"
HALS = {WASL: {WASL}, WAQF: {WAQF}, BOTH: {WASL, WAQF}}

# ---------- Quran text ----------
BASMALA = "بسم الله الرحمن الرحيم"
MARKS = re.compile(r"[ؐ-ًؚ-ٟۖ-ۭـ﻿]")
LETTER = re.compile(r"[ء-يٱ]")

def canon(w):
    """Put shadda before the vowel mark so patterns are stable."""
    return re.sub(r"([ً-ِ])ّ", "ّ\\1", w)

def skel(s):
    s = s.replace("ٰ", "ا").replace("ٱ", "ا")
    s = MARKS.sub("", s)
    s = re.sub(r"[إأآا]", "ا", s).replace("ى", "ي").replace("ة", "ه")
    return re.sub(r"[ءؤئ]", "", s)

def load_quran():
    def load(name):
        return json.loads((ROOT / "source" / "quran" / f"{name}.json").read_text(encoding="utf8"))["data"]["surahs"]
    def words(t):
        return [canon(w) for w in t.replace("﻿", "").split() if LETTER.search(w)]
    simple, voc, uth = load("quran-simple-clean"), load("quran-simple"), load("quran-uthmani")
    Q = {}
    for ss, sv, su in zip(simple, voc, uth):
        sname = MARKS.sub("", su["name"]).replace("سورة ", "").strip()
        for a1, a2, a3 in zip(ss["ayahs"], sv["ayahs"], su["ayahs"]):
            t1, t2, t3 = words(a1["text"]), words(a2["text"]), words(a3["text"])
            if ss["number"] != 1 and a1["numberInSurah"] == 1 and " ".join(t1[:4]) == BASMALA:
                t1, t2, t3 = t1[4:], t2[4:], t3[4:]
            assert len(t1) == len(t2), (ss["number"], a1["numberInSurah"])
            Q[(ss["number"], a1["numberInSurah"])] = {"sura": sname, "simple": t1, "voc": t2, "uth": t3}
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
    """→ list of (key, simple_index)."""
    loc = m["loc"]
    excl = [tuple(e) for e in loc.get("exclude", [])]
    default_tok = loc.get("search") or ("^" + loc["token"] + "$" if "token" in loc else ".")
    if "at" in loc:   # [sura, aya] | [sura, aya, "token"] | [sura, aya, "token", nth]
        targets = [((a[0], a[1]), "^" + a[2] + "$" if len(a) > 2 else default_tok, a[3] if len(a) > 3 else loc.get("nth"))
                   for a in loc["at"]]
    else:
        keys = [k for k in Q if "within" not in loc or k[0] in loc["within"]]
        targets = [(k, default_tok, loc.get("nth")) for k in keys]
    hits, seen = [], set()
    for key, tok, nth in targets:
        ay = Q[key]; n = 0
        for i, t in enumerate(ay["simple"]):
            if not re.search(tok, t): continue
            if "near" in loc and (i == 0 or not re.search(loc["near"], ay["simple"][i - 1])): continue
            if "next" in loc and (i + 1 >= len(ay["simple"]) or not re.search(loc["next"], ay["simple"][i + 1])): continue
            if "vocal" in loc and not re.search(loc["vocal"], ay["voc"][i]): continue
            if "next_vocal" in loc:      # «cross»: the last word may join the first word of the next aya (wasl)
                nxt = ay["voc"][i + 1] if i + 1 < len(ay["voc"]) else (
                      Q[(key[0], key[1] + 1)]["voc"][0] if loc.get("cross") and (key[0], key[1] + 1) in Q else "")
                if not re.search(loc["next_vocal"], nxt): continue
            j = uth_index(ay, i)
            if "uthmani" in loc and not re.search(loc["uthmani"], ay["uth"][j]): continue
            if "uthmani_not" in loc and re.search(loc["uthmani_not"], ay["uth"][j]): continue
            n += 1
            if nth and n != nth: continue
            if key in excl or key + (n,) in excl: continue
            if (key, i) not in seen:
                seen.add((key, i)); hits.append((key, i))
    return hits

# ---------- usul shorthand → readings ----------
def _names(s):
    return [x.strip() for x in re.split(r"[،,]", s or "") if x.strip()]

def shorthand(m):
    """Expand compact usul fields into `readings` (used for the many usul masail taken from al-Budur):
      imala:  {kubra: names, taqlil: names, khulf: names, hal: "وقفًا"}   khulf → the stated wajh, then الفتح
      kabir:  true                                                       السوسي بالإدغام، والباقون بالإظهار
      saghir: {idgham: names, khulf: names}                              khulf → الإدغام ثم الإظهار
      yaa:    {fath: names} or {iskan: names}, khulf: names              ياء الإضافة (الوقف بالإسكان للجميع)
      zaida:  {wasl: names, halayn: names, khulf: names}                 ياء زائدة: إثبات وصلًا / في الحالين
    In every kind, `khulf_rev: names` (a subset of khulf) puts the opposite wajh first for those rawis.
    """
    kinds = [k for k in ("imala", "kabir", "saghir", "yaa", "zaida") if k in m]
    if not kinds: return m
    if len(kinds) > 1 or "readings" in m:
        raise SystemExit(f"{m['id']}: use one shorthand ({kinds}) and no explicit readings")
    k, spec = kinds[0], m[kinds[0]]
    R = []
    if k == "imala":
        hal = spec.get("hal")
        khulf = set(_names(spec.get("khulf")))
        for key, wasf in (("kubra", "بالإمالة الكبرى"), ("taqlil", "بالتقليل")):
            ns = _names(spec.get(key))
            plain = [n for n in ns if n not in khulf]; kh = [n for n in ns if n in khulf]
            for group in (plain, kh):
                if group:
                    r = {"by": "، ".join(group), "wasf": wasf}
                    if hal: r["hal"] = hal
                    R.append(r)
            for n in kh:
                r = {"by": n, "wasf": "بالفتح"}
                if hal: r["hal"] = hal
                R.append(r)
        R.append({"by": "الباقون", "wasf": "بالفتح", **({"hal": hal} if hal else {})})
        if hal == WAQF:
            R.append({"by": "الباقون", "hal": WASL, "wasf": "لا إمالة في الوصل"})
    elif k == "kabir":
        R = [{"by": "السوسي", "wasf": "بالإدغام الكبير"}, {"by": "الباقون", "wasf": "بالإظهار"}]
    elif k == "saghir":
        khulf = set(_names(spec.get("khulf")))
        ns = _names(spec.get("idgham"))
        plain = [n for n in ns if n not in khulf]
        if plain: R.append({"by": "، ".join(plain), "wasf": "بالإدغام"})
        kh = _names(spec.get("khulf"))
        if kh:
            R.append({"by": "، ".join(kh), "wasf": "بالإدغام"})
            R.append({"by": "، ".join(kh), "wasf": "بالإظهار"})
        R.append({"by": "الباقون", "wasf": "بالإظهار"})
    elif k == "yaa":
        khulf = _names(spec.get("khulf"))
        if "fath" in spec:
            ns = [n for n in _names(spec["fath"]) if n not in khulf]
            if ns: R.append({"by": "، ".join(ns), "hal": WASL, "wasf": "بفتح الياء"})
            if khulf:
                R.append({"by": "، ".join(khulf), "hal": WASL, "wasf": "بفتح الياء"})
                R.append({"by": "، ".join(khulf), "hal": WASL, "wasf": "بإسكان الياء"})
            R.append({"by": "الباقون", "wasf": "بإسكان الياء"})
        else:
            ns = [n for n in _names(spec["iskan"]) if n not in khulf]
            if ns: R.append({"by": "، ".join(ns), "wasf": "بإسكان الياء"})
            if khulf:
                R.append({"by": "، ".join(khulf), "hal": WASL, "wasf": "بإسكان الياء"})
                R.append({"by": "، ".join(khulf), "hal": WASL, "wasf": "بفتح الياء"})
            R.append({"by": "الباقون", "hal": WASL, "wasf": "بفتح الياء"})
        R.append({"by": "الباقون", "hal": WAQF, "wasf": "بإسكان الياء"})
    elif k == "zaida":
        halayn = _names(spec.get("halayn")); wasl = _names(spec.get("wasl")); khulf = _names(spec.get("khulf"))
        if halayn: R.append({"by": "، ".join(halayn), "wasf": "بإثبات الياء في الحالين"})
        w = [n for n in wasl if n not in khulf]
        if w: R.append({"by": "، ".join(w), "hal": WASL, "wasf": "بإثبات الياء وصلًا"})
        if khulf:
            R.append({"by": "، ".join(khulf), "hal": WASL, "wasf": "بإثبات الياء وصلًا"})
            R.append({"by": "، ".join(khulf), "hal": WASL, "wasf": "بحذف الياء وصلًا"})
        R.append({"by": "الباقون", "hal": WASL, "wasf": "بحذف الياء"})
        R.append({"by": "الباقون", "hal": WAQF, "wasf": "بحذف الياء"})
    rev = set(_names(spec.get("khulf_rev"))) if isinstance(spec, dict) else set()
    if k == "imala" and "ورش" in _names(spec.get("khulf")):
        rev ^= {"ورش"}   # ورش: الفتح ثم التقليل افتراضًا (قرار المراجع)؛ و khulf_rev له يقدّم التقليل
    if rev:   # «khulf_rev»: for these rawis the opposite wajh comes first — split them out with the two readings swapped
        out = []
        pair = [r for r in R if set(_names(r["by"])) & rev]
        for r in R:
            if r in pair:
                rest = [n for n in _names(r["by"]) if n not in rev]
                if rest: out.append({**r, "by": "، ".join(rest)})
            else:
                out.append(r)
        mine = [{**r, "by": "، ".join(n for n in _names(r["by"]) if n in rev)} for r in pair]
        idx = next(i for i, r in enumerate(out) if r["by"] == "الباقون")
        out[idx:idx] = list(reversed(mine))
        R = out
    m = dict(m)
    m["readings"] = R
    return m

# ---------- readings ----------
def expand(m):
    """→ list of reading dicts, each with 'rawis' resolved (hal-aware «الباقون»). Validates coverage."""
    rds = []
    for rd in m["readings"]:
        rd = {**rd, "hal": rd.get("hal", BOTH)}
        if rd["hal"] not in HALS: sys.exit(f"{m['id']}: bad hal «{rd['hal']}»")
        rds.append(rd)
    covered = {r: set() for r in RAWIS}
    for rd in rds:
        if rd["by"].strip() == "الباقون": continue
        rs = []
        for name in re.split(r"[،,]\s*", rd["by"]):
            name = name.strip()
            if name not in NAMES: sys.exit(f"{m['id']}: unknown name «{name}»")
            rs += NAMES[name]
        rd["rawis"] = rs
        for r in rs: covered[r] |= HALS[rd["hal"]]
    for rd in rds:                               # «الباقون» resolved in order, per hal
        if rd["by"].strip() != "الباقون": continue
        rd["rawis"] = [r for r in RAWIS if not (covered[r] & HALS[rd["hal"]])]
        for r in rd["rawis"]: covered[r] |= HALS[rd["hal"]]
    for r in RAWIS:
        if covered[r] != {WASL, WAQF}:
            sys.exit(f"{m['id']}: rawi «{r}» lacks {({WASL, WAQF} - covered[r])}")
    return rds

def lafz_at(rd, base):
    if "lafz" in rd: return canon(rd["lafz"])
    out = base
    for pat, rep in rd.get("tahwil", []):      # ordered alternatives; at least one must apply
        out = re.sub(canon(pat), canon(rep), out)
    if rd.get("tahwil") and out == base:
        sys.exit(f"tahwil {rd['tahwil']} did not change «{base}»")
    return out

def names_for(rs):
    """Name whole qurra where both rawis present."""
    names, left = [], list(rs)
    for qari, pair in QURRA.items():
        if all(p in left for p in pair):
            names.append(qari); left = [x for x in left if x not in pair]
    return "، ".join(names + left) if len(rs) < 14 else "الجميع"

def summary(rds):
    parts = []
    for rd in rds:
        if not rd["rawis"]: continue
        h = "" if rd["hal"] == BOTH else f" [{rd['hal']}]"
        parts.append(f"{rd.get('lafz') or rd['wasf']}{h}: {names_for(rd['rawis'])}")
    return " | ".join(parts)

# ---------- check mode (no outputs; safe to run in parallel) ----------
def _cmp(t):
    """Comparison form: canonical marks, no sukun / Quranic marks, unified alef."""
    t = canon(t).replace("ٱ", "ا")
    t = re.sub(r"[ْٰۖ-ۭؐ-ؚ]", "", t)
    return re.sub(r"[إأآ]", "ا", t).replace("ى", "ي")

def check(files):
    """python scripts/build_masail.py --check data/masail/X.yaml ...
    Validates the given files: names, 14-rawi coverage, locations, tahwil, and that Hafs's reading
    matches the mushaf text. Writes nothing."""
    Q = load_quran()
    matn = {v["n"]: v for v in json.loads((ROOT / "data" / "shatibiyya.json").read_text(encoding="utf8"))}
    all_ids = {}
    for f in sorted((ROOT / "data" / "masail").glob("*.yaml")):
        for x in yaml.safe_load(f.read_text(encoding="utf8")) or []:
            all_ids.setdefault(x["id"], []).append(f.name)
    errors = warns = 0
    for path in files:
        print(f"== {path}")
        try:
            masail = yaml.safe_load(pathlib.Path(path).read_text(encoding="utf8")) or []
        except yaml.YAMLError as e:
            print(f"  ERROR yaml: {e}"); errors += 1; continue
        for m in masail:
            mid = m.get("id", "?")
            try:
                m = shorthand(m)
                for key in ("id", "bayt", "qawl", "word", "scope", "loc", "readings"):
                    if key not in m: raise SystemExit(f"missing field «{key}»")
                if len(all_ids.get(mid, [])) > 1: raise SystemExit(f"duplicate id in {all_ids[mid]}")
                for n in m["bayt"]:
                    if n not in matn: raise SystemExit(f"bad bayt {n}")
                for e in m.get("marji", []):
                    if not isinstance(e, dict) or not e.get("kitab") or set(e) - MARJI_KEYS or "إقرار" in e["kitab"]:
                        raise SystemExit(f"bad marji entry {e} (a book: keys {sorted(MARJI_KEYS)}; personal decisions go in iqrar)")
                for e in m.get("tahrir", []):
                    if not isinstance(e, dict) or e.get("naw") not in TAHRIR_KINDS or not e.get("bayan") or set(e) - TAHRIR_KEYS:
                        raise SystemExit(f"bad tahrir entry {e} (naw in {TAHRIR_KINDS}, bayan required, keys {sorted(TAHRIR_KEYS)})")
                if any(rd.get("ziyada") for rd in m["readings"]) and not any(e.get("naw") == "زيادة على النظم" for e in m.get("tahrir", [])):
                    raise SystemExit("a reading has ziyada: true but no «زيادة على النظم» tahrir entry explains it")
                for e in m.get("iqrar", []):
                    if not isinstance(e, dict) or not e.get("man") or not e.get("tarikh") or set(e) - IQRAR_KEYS:
                        raise SystemExit(f"bad iqrar entry {e} (keys: {sorted(IQRAR_KEYS)}, man+tarikh required)")
                rds = expand(m)
                hits = locate(m, Q)
                if not hits: raise SystemExit("no locations found")
                span = m["loc"].get("span", 1)
                bad = []
                for (s, a), i in hits:
                    ay = Q[(s, a)]
                    base = " ".join(ay["voc"][i:i + span])
                    for rd in rds:
                        lf = lafz_at(rd, base)
                        if "حفص" in rd["rawis"] and rd["hal"] == BOTH:   # hal-specific readings may differ from the rasm
                            if "lafz" in rd:
                                text = _cmp(" ".join(ay["voc"]))
                                segs = [x.strip() for x in rd["lafz"].split("...") if x.strip()]
                                if not all(_cmp(seg) in text for seg in segs):
                                    bad.append(f"{s}:{a} حفص «{rd['lafz']}» ليس في نص الآية")
                            elif _cmp(lf) != _cmp(base):
                                bad.append(f"{s}:{a} حفص «{lf}» ≠ النص «{base}»")
                print(f"  {mid:10} {len(hits):4} موضع  {m['word']}")
                for b in bad[:5]:
                    print(f"     WARN {b}"); warns += 1
            except SystemExit as e:
                print(f"  ERROR {mid}: {e}"); errors += 1
    print(f"\n{errors} error(s), {warns} warning(s)")
    sys.exit(1 if errors else 0)

# ---------- main ----------
def main():
    if "--check" in sys.argv:
        return check([a for a in sys.argv[1:] if a != "--check"])
    Q = load_quran()
    matn = {v["n"]: v for v in json.loads((ROOT / "data" / "shatibiyya.json").read_text(encoding="utf8"))}
    masail = []
    for f in sorted((ROOT / "data" / "masail").glob("*.yaml")):
        masail += yaml.safe_load(f.read_text(encoding="utf8"))
    masail = [shorthand(m) for m in masail]
    ids = [m["id"] for m in masail]
    assert len(ids) == len(set(ids)), "duplicate ids"

    M, W, R = [], [], []          # masail, wide rows, long (per-rawi) rows
    RD, MW, SRC = [], [], {}      # normalized: reading definitions, mawadi, masala → source file
    for f in sorted((ROOT / "data" / "masail").glob("*.yaml")):
        for x in yaml.safe_load(f.read_text(encoding="utf8")): SRC[x["id"]] = f.name
    for m in masail:
        rds = expand(m)
        for k, rd in enumerate(rds):
            rd["rid"] = f"{m['id']}#{k + 1}"
            RD.append({"rid": rd["rid"], "masala_id": m["id"], "ord": k + 1, "by_text": rd["by"],
                       "lafz": rd.get("lafz", ""),
                       "tahwil": json.dumps(rd["tahwil"], ensure_ascii=False) if rd.get("tahwil") else "",
                       "wasf": rd.get("wasf", ""), "hal": rd["hal"], "dalil": rd.get("dalil", m["qawl"]),
                       "ramz": rd.get("ramz", m.get("rumuz", "")), "rawis": rd["rawis"],
                       "ziyada": 1 if rd.get("ziyada") else 0})
        hits = locate(m, Q)
        if not hits: sys.exit(f"{m['id']}: no locations found")
        bab = matn[m["bayt"][0]]["bab"]
        kind = "فرش" if bab.startswith(("سورة", "ومن سورة")) else "أصول"
        if kind == "فرش": bab = "فرش " + bab.removeprefix("ومن ")
        span = m["loc"].get("span", 1)
        bayt_text = " ** ".join(f"{n}: {matn[n]['sadr']} ... {matn[n]['ajz']}" for n in m["bayt"])
        base = {"id": m["id"], "naw": kind, "bab": bab, "abyat": "، ".join(map(str, m["bayt"])),
                "qawl": m["qawl"], "kalima": m["word"], "nitaq": m["scope"],
                "natija": summary(rds), "note": m.get("note", ""), "review": m.get("review", "")}
        M.append({**base, "nass_albayt": bayt_text, "adad": len(hits), "rumuz": m.get("rumuz", ""),
                  "bayt_list": m["bayt"], "src": SRC[m["id"]], "marji_list": m.get("marji", []),
                  "marji": marji_summary(m.get("marji", [])), "iqrar_list": m.get("iqrar", []),
                  "iqrar": iqrar_summary(m.get("iqrar", [])), "tahrir_list": m.get("tahrir", []),
                  "tahrir": "؛ ".join(dict.fromkeys(e["naw"] for e in m.get("tahrir", [])))})
        for (s, a), i in hits:
            ay = Q[(s, a)]
            word_voc = " ".join(ay["voc"][i:i + span])
            mid = f"{m['id']}@{s}:{a}:{i + 1}"
            mawdi = {"sura_no": s, "sura": ay["sura"], "aya_no": a, "word_no": i + 1,
                     "aya": " ".join(ay["uth"]), "mawdi": word_voc}
            MW.append({"mid": mid, "masala_id": m["id"], **mawdi, "aya_voc": " ".join(ay["voc"])})
            # Hafs's readings here → a row agrees with Hafs if he has the same lafz and ada' in an overlapping hal
            hafs = [(lafz_at(rd, word_voc), rd.get("wasf", ""), HALS[rd["hal"]]) for rd in rds if "حفص" in rd["rawis"]]
            agrees = lambda lf, wasf, hal: any(lf == hl and wasf == hw and HALS[hal] & hh for hl, hw, hh in hafs)
            cells = {r: [] for r in RAWIS}
            for r in RAWIS:
                mine = [k for k, rd in enumerate(rds) if r in rd["rawis"]]
                for wajh, k in enumerate(mine, 1):
                    rd = rds[k]
                    lf = lafz_at(rd, word_voc)
                    same_hal = [x for x in mine if HALS[rds[x]["hal"]] & HALS[rd["hal"]]]
                    R.append({**base, **mawdi, "mid": mid, "rid": rd["rid"], "rawi": r, "qari": QARI_OF[r], "lafz": lf, "wasf": rd.get("wasf", ""),
                              "hal": rd["hal"],
                              "wajh": f"{same_hal.index(k) + 1} من {len(same_hal)}" if len(same_hal) > 1 else "",
                              "dalil": rd.get("dalil", m["qawl"]), "ramz": rd.get("ramz", m.get("rumuz", "")),
                              "hafs": "نعم" if agrees(lf, rd.get("wasf", ""), rd["hal"]) else "لا",
                              "ziyada": "نعم" if rd.get("ziyada") else ""})
                    h = "" if rd["hal"] == BOTH else f" [{rd['hal']}]"
                    cells[r].append(f"{lf} ({rd.get('wasf', '')}){h}")
            W.append({**base, **mawdi, **{r: " / ".join(cells[r]) for r in RAWIS}})
        print(f"{m['id']:7} {kind:5} {len(hits):4} موضع  {m['word']}")

    OUT.mkdir(parents=True, exist_ok=True)
    AR = {"id": "رقم المسألة", "naw": "النوع", "bab": "الباب", "abyat": "رقم البيت", "nass_albayt": "نص البيت",
          "qawl": "قول الشاطبي", "kalima": "الكلمة", "nitaq": "النطاق", "natija": "النتيجة المعمول بها",
          "note": "ملاحظة", "review": "للمراجعة", "adad": "عدد المواضع", "sura_no": "رقم السورة", "sura": "السورة",
          "aya_no": "رقم الآية", "word_no": "رقم الكلمة", "aya": "نص الآية", "mawdi": "الكلمة في الآية (حفص)",
          "rawi": "الراوي", "qari": "القارئ", "lafz": "لفظ الراوي", "wasf": "الأداء", "hal": "الحال",
          "wajh": "الوجه", "dalil": "الدليل من النظم", "ramz": "الرمز", "hafs": "يوافق حفصًا",
          "marji": "مصدر الاعتماد", "iqrar": "إقرار المراجع", "tahrir": "تحرير / تنبيه", "ziyada": "زيادة على النظم"}
    r_cols = ["qari", "rawi", "sura_no", "sura", "aya_no", "word_no", "mawdi", "lafz", "wasf", "hal", "wajh", "hafs", "ziyada",
              "naw", "bab", "id", "abyat", "dalil", "ramz", "note", "review"]
    w_cols = ["id", "naw", "bab", "sura_no", "sura", "aya_no", "aya", "mawdi", "abyat", "qawl", "natija", *RAWIS, "nitaq", "note", "review"]
    m_cols = ["id", "naw", "bab", "abyat", "kalima", "nitaq", "adad", "qawl", "natija", "note", "review", "tahrir", "marji", "iqrar", "nass_albayt"]
    order = lambda r: (r["sura_no"], r["aya_no"], r["word_no"], RAWIS.index(r["rawi"]) if "rawi" in r else 0)
    R.sort(key=order); W.sort(key=order)

    def write_csv(path, rows, cols):
        with open(path, "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.writer(fh); w.writerow([AR.get(c, c) for c in cols])
            for r in rows: w.writerow([r[c] for c in cols])
    write_csv(OUT / "qiraat.csv", R, r_cols)
    write_csv(OUT / "jadwal.csv", W, w_cols)
    write_csv(OUT / "masail.csv", M, m_cols)
    for old in ("mawadi.csv",):
        (OUT / old).unlink(missing_ok=True)

    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill
    wb = Workbook()
    for title, rows, cols in [("القراءات", R, r_cols), ("الجدول", W, w_cols), ("المسائل", M, m_cols)]:
        ws = wb.active if title == "القراءات" else wb.create_sheet()
        ws.title = title; ws.sheet_view.rightToLeft = True
        ws.append([AR.get(c, c) for c in cols])
        for r in rows: ws.append([r[c] for c in cols])
        for c in ws[1]:
            c.font = Font(bold=True, color="FFFFFF"); c.fill = PatternFill("solid", fgColor="1F4E5F")
        for col in ws.columns:
            width = min(55, max(7, max(len(str(c.value or "")) for c in col[:300]) * 0.9))
            ws.column_dimensions[col[0].column_letter].width = width
            for c in col[1:]: c.alignment = Alignment(wrap_text=width >= 55, vertical="top")
        ws.freeze_panes = "C2"; ws.auto_filter.ref = ws.dimensions
    wb.save(OUT / "qiraat_masail.xlsx")

    write_db(matn, M, RD, MW, R)
    print(f"\n{len(M)} مسألة، {len(W)} موضع، {len(R)} صف قراءة → {OUT}")

MARJI_KEYS = {"kitab", "safha", "mawdu"}          # a book source
IQRAR_KEYS = {"man", "tarikh", "mawdu"}           # the reviewer's own decision (not a source)
TAHRIR_KINDS = ("خروج عن الطريق", "زيادة على النظم", "تنبيه على العبارة")
TAHRIR_KEYS = {"naw", "rawi", "bayan", "hukm", "qawl", "kitab", "safha"}

def iqrar_summary(entries):
    return "؛ ".join(dict.fromkeys(f"{e.get('man', '')} ({e.get('tarikh', '')})" for e in entries))

def marji_summary(entries):
    """«الوافي ص210؛ إقرار المراجع (هاني زيدان، 2026-10-04)»"""
    out = [f"{e['kitab']} ص{e['safha']}" if e.get("safha") else e["kitab"] for e in entries]
    return "؛ ".join(dict.fromkeys(out))

def plain(t):
    """Strip tashkeel/Quranic marks and unify alef/ya forms, for searching."""
    t = t.replace("ٱ", "ا").replace("ٰ", "ا")
    t = MARKS.sub("", t)
    return re.sub(r"[إأآ]", "ا", t).replace("ى", "ي")

def write_db(matn, M, RD, MW, R):
    """Content DB for scripts and the PHP app. Regenerated on every build;
    reviews live in a separate DB owned by the app (app/data/reviews.db)."""
    import subprocess, datetime
    db = OUT / "qiraat.db"
    db.unlink(missing_ok=True)
    con = sqlite3.connect(db)
    con.executescript((ROOT / "scripts" / "schema.sql").read_text(encoding="utf8"))
    def ins(table, rows):
        if rows: con.executemany(f"INSERT INTO {table} VALUES({','.join('?' * len(rows[0]))})", rows)
    ins("qurra", [(q, i + 1) for i, q in enumerate(QURRA)])
    ins("rawis", [(r, QARI_OF[r], i + 1) for i, r in enumerate(RAWIS)])
    ins("matn", [(v["n"], v["bab"], v["sadr"], v["ajz"], plain(v["sadr"] + " " + v["ajz"])) for v in matn.values()])
    ins("masail", [(m["id"], m["naw"], m["bab"], m["abyat"], m["kalima"], plain(m["kalima"]), m["nitaq"], m["qawl"],
                    m["rumuz"], m["natija"], m["note"], m["review"], m["adad"], m["src"], m["marji"], m["iqrar"], m["tahrir"]) for m in M])
    ins("tahrir", [(m["id"], k + 1, e["naw"], e.get("rawi", ""), e.get("bayan", ""), e.get("hukm", ""), e.get("qawl", ""),
                    e.get("kitab", ""), str(e.get("safha", ""))) for m in M for k, e in enumerate(m["tahrir_list"])])
    ins("iqrar", [(m["id"], k + 1, e.get("man", ""), str(e.get("tarikh", "")), e.get("mawdu", ""))
                  for m in M for k, e in enumerate(m["iqrar_list"])])
    ins("marji", [(m["id"], k + 1, e.get("kitab", ""), str(e.get("safha", "")), e.get("mawdu", ""), e.get("man", ""),
                   str(e.get("tarikh", ""))) for m in M for k, e in enumerate(m["marji_list"])])
    ins("masala_abyat", [(m["id"], n) for m in M for n in m["bayt_list"]])
    ins("readings", [(r["rid"], r["masala_id"], r["ord"], r["by_text"], r["lafz"], r["tahwil"], r["wasf"], r["hal"],
                      r["dalil"], r["ramz"], r["ziyada"]) for r in RD])
    ins("reading_rawis", [(r["rid"], rw) for r in RD for rw in r["rawis"]])
    ins("mawadi", [(w["mid"], w["masala_id"], w["sura_no"], w["sura"], w["aya_no"], w["word_no"], w["mawdi"],
                    plain(w["mawdi"]), w["aya"], w["aya_voc"]) for w in MW])
    ins("qiraat", [(r["mid"], r["rid"], r["rawi"], r["lafz"], plain(r["lafz"]), r["wajh"], 1 if r["hafs"] == "نعم" else 0)
                   for r in R])
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    ins("meta", [("built_at", datetime.datetime.now().isoformat(timespec="seconds")), ("git_commit", commit),
                 ("masail", str(len(M))), ("mawadi", str(len(MW))), ("qiraat", str(len(R)))])
    con.commit(); con.close()

if __name__ == "__main__":
    main()
