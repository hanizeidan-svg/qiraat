"""Turn an export from the app (المراجعات → تصدير) into a checklist for editing data/masail/*.yaml.

  python scripts/reviews.py reviews-accepted-20261003.json  → prints Markdown grouped by source file and masala

After applying the changes: rebuild (python scripts/build_masail.py), deploy the new data/out/qiraat.db,
and mark the issues «طُبِّقت في المصدر» in the app.
"""
import json, sys, pathlib
from itertools import groupby

def main():
    if len(sys.argv) != 2: sys.exit(__doc__)
    data = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf8"))
    issues = sorted(data["issues"], key=lambda i: (i.get("src_file") or "~", i.get("masala_id") or "", i["id"]))
    print(f"# مراجعات ({data['status']}) — {len(issues)} بندًا، نسخة المحتوى {data['content_commit']}\n")
    for src, g in groupby(issues, key=lambda i: i.get("src_file") or "(بلا ملف: المتن/عامة)"):
        print(f"## {src}\n")
        for i in g:
            stale = i.get("value_now") is not None and i["value_now"] != i["current_value"]
            print(f"- [ ] **#{i['id']}** {i.get('target_label') or i['target_key']} · `{i['target_key']}` · الحقل: `{i['field']}`"
                  + (" ⚠ تغيّرت القيمة منذ البلاغ" if stale else ""))
            if i["current_value"]: print(f"  - الحالي: {i['current_value']}")
            if i["proposed_value"]: print(f"  - المقترح: {i['proposed_value']}")
            if i["comment"]: print(f"  - التعليل: {i['comment']}")
            for c in i.get("comments", []): print(f"  - {c['who']}: {c['body']}")
        print()

if __name__ == "__main__":
    main()
