"""Collect every «review» flag from data/masail/*.yaml into docs/REVIEW.md (grouped by file, in mushaf order).

  python scripts/review_list.py
"""
import pathlib, re
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent

def main():
    out, n = ["# نقاط المراجعة", "",
              "مولَّدة من حقل `review` في `data/masail/*.yaml`. بعد الفصل في نقطة: عدّل المسألة واحذف حقل review، ثم أعد البناء.", ""], 0
    for f in sorted((ROOT / "data" / "masail").glob("*.yaml")):
        items = [m for m in yaml.safe_load(f.read_text(encoding="utf8")) or [] if m.get("review")]
        if not items: continue
        out.append(f"## {f.name} ({len(items)})\n")
        for m in items:
            n += 1
            out.append(f"- [ ] **{m['id']}** (البيت {', '.join(map(str, m['bayt']))}) {m['word']}: {m['review']}")
        out.append("")
    out.insert(2, f"العدد: {n}")
    (ROOT / "docs" / "REVIEW.md").write_text("\n".join(out), encoding="utf8")
    print(f"{n} نقطة → docs/REVIEW.md")

if __name__ == "__main__":
    main()
