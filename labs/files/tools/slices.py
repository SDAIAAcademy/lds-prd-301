# /// script
# requires-python = ">=3.10"
# ///
"""Subgroup results from the audited cases of a pilot file (Al-Rukhama Family Care Society, synthetic).

    uv run slices.py ../pilot1/pilot1_cases.csv
    uv run slices.py ../pilot1/pilot1_cases.csv --decision final --by doc_form,channel --max 0.05 --min-n 20

Only audited rows count (audit_decision is filled): the audit is the society's re-decision of a
random sample by two senior caseworkers. Metrics, each with its own base:
  false_not_eligible = drafts (or finals) "not_eligible" among audited "eligible"
  false_incomplete   = drafts (or finals) "incomplete" among audited "eligible" or "not_eligible"
A slice whose base is below --min-n is shown as "too few", never as a pass.
Standard library only; no network.
"""
import argparse
import csv
import sys

FIELDS = ["doc_form", "doc_lang", "age_band", "channel", "household_type", "district"]


def table(rows, field, key):
    out = []
    for v in sorted({r[field] for r in rows}):
        sub = [r for r in rows if r[field] == v]
        el = [r for r in sub if r["audit_decision"] == "eligible"]
        ni = [r for r in sub if r["audit_decision"] != "incomplete"]
        fne = sum(1 for r in el if r[key] == "not_eligible")
        fin = sum(1 for r in ni if r[key] == "incomplete")
        out.append((v, len(sub), len(el), fne, len(ni), fin))
    return out


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pilot_csv")
    ap.add_argument("--decision", choices=["draft", "final"], default="draft")
    ap.add_argument("--by", default=",".join(FIELDS[:4]))
    ap.add_argument("--max", type=float, default=0.05, help="release threshold for each rate (default 0.05)")
    ap.add_argument("--min-n", type=int, default=20, help="smallest base that can pass (default 20)")
    a = ap.parse_args(argv)
    try:
        with open(a.pilot_csv, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    except OSError as e:
        print(f"cannot read the file: {e.strerror}")
        return 2
    rows = [r for r in rows if r.get("audit_decision")]
    if not rows:
        print("no audited rows in this file")
        return 2
    print(f"audited cases: {len(rows)} · decision read: {a.decision} · threshold {a.max:.0%} · min n {a.min_n}")
    worst = []
    for field in [x.strip() for x in a.by.split(",") if x.strip()]:
        if field not in rows[0]:
            print(f"\nunknown column: {field}")
            continue
        print(f"\n{field}")
        print(f"  {'slice':<16}{'n':>5}{'elig':>6}{'false not eligible':>22}{'false incomplete':>20}")
        for v, n, ne, fne, ni, fin in table(rows, field, a.decision):
            def cell(k, base):
                if base < a.min_n:
                    return f"{k}/{base} too few"
                r = k / base
                return f"{k}/{base} {r:6.1%}{' FAIL' if r > a.max else ' ok  '}"
            print(f"  {v:<16}{n:>5}{ne:>6}{cell(fne, ne):>22}{cell(fin, ni):>20}")
            for k, base, m in ((fne, ne, "false_not_eligible"), (fin, ni, "false_incomplete")):
                if base >= a.min_n and k / base > a.max:
                    worst.append((k / base, field, v, m, k, base))
    print()
    if worst:
        worst.sort(reverse=True)
        print("slices above the threshold:")
        for r, field, v, m, k, base in worst:
            print(f"  {field}={v}: {m} {k}/{base} = {r:.1%}")
    else:
        print("no slice with enough cases is above the threshold")
    return 0


if __name__ == "__main__":
    sys.exit(main())
