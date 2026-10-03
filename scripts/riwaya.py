"""Extract one qari's (or rawi's) reading with its evidence from the Shatibiyya.

  python scripts/riwaya.py "ابن كثير"            → data/out/riwayat/ابن كثير.md + .xlsx
  python scripts/riwaya.py "قنبل" --khilaf        → only where the reading differs from Hafs
"""
import sys, sqlite3, pathlib, argparse
from itertools import groupby

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from build_masail import QURRA, RAWIS, OUT, BOTH

def fmt(r):
    h = "" if r["hal"] == BOTH else f" [{r['hal']}]"
    w = f" (وجه {r['wajh']})" if r["wajh"] else ""
    return f"{r['lafz']} — {r['wasf']}{h}{w}"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name"); ap.add_argument("--khilaf", action="store_true", help="only where it differs from Hafs")
    a = ap.parse_args()
    rawis = QURRA.get(a.name) or ([a.name] if a.name in RAWIS else None)
    if not rawis: sys.exit(f"unknown: {a.name}. choose from {list(QURRA) + RAWIS}")

    con = sqlite3.connect(OUT / "qiraat.db"); con.row_factory = sqlite3.Row
    rows = con.execute(f"SELECT * FROM qiraat WHERE rawi IN ({','.join('?' * len(rawis))}) "
                       "ORDER BY sura_no, aya_no, word_no, id", rawis).fetchall()
    rows = [dict(r) for r in rows]
    key = lambda r: (r["sura_no"], r["aya_no"], r["word_no"], r["id"])
    title = f"قراءة {a.name.replace('أبو ', 'أبي ')}" + (f" ({' و'.join(rawis)})" if len(rawis) > 1 else "")
    md = [f"# {title}", "", "من بيانات «حرز الأماني» — النموذج الحالي: فرش البقرة 445–474، وأصول البقرة (انظر README).",
          "" if not a.khilaf else "مقتصرًا على ما خالف فيه رواية حفص.", ""]
    flat, n = [], 0
    for sura, g_s in groupby(rows, key=lambda r: (r["sura_no"], r["sura"])):
        md.append(f"## سورة {sura[1]}")
        for k, g in groupby(list(g_s), key=key):
            g = list(g)
            if a.khilaf and all(r["hafs"] == "نعم" for r in g): continue
            n += 1
            r0 = g[0]
            by_rawi = {rw: [x for x in g if x["rawi"] == rw] for rw in rawis}
            texts = {rw: " · ".join(fmt(x) for x in rs) for rw, rs in by_rawi.items()}
            agree = len(set(texts.values())) == 1
            md.append(f"- **{r0['aya_no']}: {r0['mawdi']}** [{r0['bab']}]")
            if agree:
                md.append(f"  - {texts[rawis[0]]}")
            else:
                for rw in rawis: md.append(f"  - {rw}: {texts[rw]}")
            dal = sorted({(x["abyat"], x["dalil"], x["ramz"]) for x in g})
            for ab, dl, rz in dal:
                md.append(f"  - الدليل (البيت {ab}): «{dl}»" + (f" — الرمز: {rz}" if rz and rz != "—" else ""))
            for rw in rawis:
                for x in by_rawi[rw]:
                    flat.append({"الراوي": rw, "السورة": r0["sura"], "الآية": r0["aya_no"], "الكلمة": r0["mawdi"],
                                 "لفظه": x["lafz"], "الأداء": x["wasf"], "الحال": x["hal"], "الوجه": x["wajh"],
                                 "يوافق حفصًا": x["hafs"], "الباب": x["bab"], "البيت": x["abyat"],
                                 "الدليل": x["dalil"], "الرمز": x["ramz"], "المسألة": x["id"]})
        md.append("")
    md.insert(4, f"عدد المواضع: {n}")

    d = OUT / "riwayat"; d.mkdir(exist_ok=True)
    stem = a.name + (" - الخلاف مع حفص" if a.khilaf else "")
    (d / f"{stem}.md").write_text("\n".join(md), encoding="utf8")
    from openpyxl import Workbook
    from openpyxl.styles import Font
    wb = Workbook(); ws = wb.active; ws.title = "الرواية"; ws.sheet_view.rightToLeft = True
    cols = list(flat[0]) if flat else []
    ws.append(cols)
    for r in flat: ws.append([r[c] for c in cols])
    for c in ws[1]: c.font = Font(bold=True)
    ws.freeze_panes = "B2"; ws.auto_filter.ref = ws.dimensions
    wb.save(d / f"{stem}.xlsx")
    print(f"{n} موضع → {d / stem}.md / .xlsx")

if __name__ == "__main__":
    main()
