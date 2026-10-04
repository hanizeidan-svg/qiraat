"""One-off: the reviewer's own decisions are not a «marji» (source). Move them to a separate field «iqrar»,
and attribute to al-Wafi the masail whose decision was checked against it and found to match.
"""
import glob, pathlib, re
import yaml

WAFI_MATCH = {   # masala → (page, what al-Wafi says) — checked against al-Wafi, matching the reviewer's decision
    "2-013": ("201", "«وعن كل القراء السبعة ضم الهاء في أن يمل هو»"),
    "2-018": ("202", "السوسي ليس له إلا الإسكان، والدوري له الإسكان والاختلاس"),
    "2-024": ("204", "إذا وقف حمزة أبدل الهمزة واوًا، وله نقل حركتها إلى الزاي"),
    "2-025": ("204", "إذا وقف حمزة أبدل الهمزة واوًا، وله نقل حركتها إلى الفاء"),
    "2-k01": ("53", "المقروء به من طريق الشاطبية والتيسير: الإدغام خاص بالسوسي، والدوري ليس له إلا الإظهار"),
    "2-m05": ("154", "«التحقيق أن الإمالة للدوري عنه والفتح للسوسي»"),
    "2-z01": ("196", "لقالون الحذف والإثبات، «والأصح الحذف»"),
}
LINE = re.compile(r'^    - \{kitab: "إقرار المراجع", (man: .*)\}$')

def q(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'

for f in sorted(glob.glob("data/masail/*.yaml")):
    p = pathlib.Path(f)
    lines = p.read_text(encoding="utf8").split("\n")
    starts = [i for i, l in enumerate(lines) if l.startswith("- id: ")] + [len(lines)]
    out, changed = lines[:starts[0]], False
    for a, b in zip(starts, starts[1:]):
        block = lines[a:b]
        mid = block[0][len("- id: "):].strip()
        iqrar = [LINE.match(l).group(1) for l in block if LINE.match(l)]
        if not iqrar and mid not in WAFI_MATCH:
            out += block; continue
        changed = True
        block = [l for l in block if not LINE.match(l)]
        mi = next((i for i, l in enumerate(block) if l == "  marji:"), None)
        if mid in WAFI_MATCH:
            page, what = WAFI_MATCH[mid]
            entry = f'    - {{kitab: "الوافي", safha: {q(page)}, mawdu: {q(what)}}}'
            if mi is None:
                end = len(block)
                while end > 1 and (not block[end - 1].strip() or block[end - 1].lstrip().startswith("#")): end -= 1
                block = block[:end] + ["  marji:", entry] + block[end:]
            else:
                j = mi + 1
                while j < len(block) and block[j].startswith("    - "): j += 1
                block = block[:j] + [entry] + block[j:]
        mi = next((i for i, l in enumerate(block) if l == "  marji:"), None)
        if mi is not None and not (mi + 1 < len(block) and block[mi + 1].startswith("    - ")):
            del block[mi]                                   # marji left empty
        if iqrar:
            end = len(block)
            while end > 1 and (not block[end - 1].strip() or block[end - 1].lstrip().startswith("#")): end -= 1
            block = block[:end] + ["  iqrar:"] + [f"    - {{{x}}}" for x in iqrar] + block[end:]
        out += block
    if changed:
        p.write_text("\n".join(out), encoding="utf8")
        yaml.safe_load(p.read_text(encoding="utf8"))
print("ok")
