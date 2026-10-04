"""One-off migration: add a structured «marji» field (the source a ruling/review was settled on) to the masail.

- al-Wafi citations already written in `note` («الوافي ص210», «على ترتيب الوافي (ص210)») become
  {kitab: "الوافي", safha: "210", mawdu: <the sentence>}.
- The reviewer's decisions given in conversation become {kitab: "إقرار المراجع", man, tarikh, mawdu}.
Edits the YAML as text (inserts lines at the end of each masala block) to keep the hand formatting.
"""
import re, glob, pathlib
import yaml

WAFI = re.compile(r"الوافي[^ص]{0,12}ص\s*\.?\s*([\d٠-٩]+(?:\s*[–-]\s*[\d٠-٩]+)?)")
REVIEWER = "هاني زيدان"
DECISIONS = {   # masala id → [(date, what was confirmed)]
    "2-013": [("2026-10-03", "«يمل هو» بالضم للجميع من طريق الشاطبية، والإسكان لقالون من زيادات النشر")],
    "2-024": [("2026-10-03", "لحمزة وقفًا وجهان: الإبدال واوًا على الرسم، والنقل")],
    "2-025": [("2026-10-03", "لحمزة وقفًا وجهان: الإبدال واوًا على الرسم، والنقل")],
    "2-018": [("2026-10-03", "للدوري وجهان: الإسكان والاختلاس")],
    "2-k01": [("2026-10-03", "الإدغام الكبير للسوسي وحده، والدوري بالإظهار")],
    "2-m05": [("2026-10-03", "إمالة «الناس» المجرور للدوري لا للسوسي"),
              ("2026-10-03", "حذف وجه الفتح للدوري، فله الإمالة وحدها")],
    "2-z01": [("2026-10-03", "الوجهان لقالون مقروء بهما، والحذف أشهر")],
    "12-773b": [("2026-10-04", "اعتماد الإدغام مع الإشمام وجهًا أول، ثم الإخفاء")],
    "52-1048b": [("2026-10-04", "الصاد أولًا لحفص في «المصيطرون»")],
}

def q(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'

def sentence_around(text, pos):
    start = max(text.rfind(".", 0, pos), text.rfind("؛", 0, pos)) + 1
    ends = [i for i in (text.find(".", pos), text.find("؛", pos)) if i != -1]
    end = min(ends) if ends else len(text)
    s = re.sub(r"\s+", " ", text[start:end]).strip()
    return s if len(s) <= 160 else s[:157] + "…"

def entries_for(m):
    out, seen = [], set()
    text = (m.get("note") or "") + " " + (m.get("review") or "")
    for mt in WAFI.finditer(text):
        page = re.sub(r"\s+", "", mt.group(1)).replace("-", "–")
        if page in seen: continue
        seen.add(page)
        out.append({"kitab": "الوافي", "safha": page, "mawdu": sentence_around(text, mt.start())})
    for date, what in DECISIONS.get(m["id"], []):
        out.append({"kitab": "إقرار المراجع", "man": REVIEWER, "tarikh": date, "mawdu": what})
    return out

def main():
    total = 0
    for f in sorted(glob.glob("data/masail/*.yaml")):
        p = pathlib.Path(f)
        text = p.read_text(encoding="utf8")
        data = {m["id"]: m for m in yaml.safe_load(text) or []}
        lines = text.split("\n")
        starts = [i for i, l in enumerate(lines) if l.startswith("- id: ")] + [len(lines)]
        out, changed = lines[:starts[0]], False
        for a, b in zip(starts, starts[1:]):
            block = lines[a:b]
            mid = block[0][len("- id: "):].strip()
            m = data[mid]
            ents = [] if "marji" in m else entries_for(m)
            if ents:
                end = len(block)
                while end > 1 and (not block[end - 1].strip() or block[end - 1].lstrip().startswith("#")):
                    end -= 1
                ins = ["  marji:"] + ["    - {" + ", ".join(f"{k}: {q(v)}" for k, v in e.items()) + "}" for e in ents]
                block = block[:end] + ins + block[end:]
                changed = True
                total += 1
            out += block
        if changed:
            p.write_text("\n".join(out), encoding="utf8")
            yaml.safe_load(p.read_text(encoding="utf8"))   # must still parse
    missing = [k for k in DECISIONS if not any(k == m["id"] for f in glob.glob("data/masail/*.yaml")
                                                for m in yaml.safe_load(open(f, encoding="utf8")))]
    print(f"marji added to {total} masail; unknown decision ids: {missing}")

if __name__ == "__main__":
    main()
