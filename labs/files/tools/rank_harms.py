# /// script
# requires-python = ">=3.10"
# ///
"""Rank a harms register (lab 1.1, LDS-PRD-301). Standard library only; no network.

    uv run rank_harms.py ../d1_1/register_start.csv
    uv run rank_harms.py my_register.csv --out ranked.csv

Columns: id, harm, affected, affected_kind (user | non_user), category (failure | misuse | scale |
bias), impact (1-4), likelihood (1-4), reversibility (reversible | costly | irreversible), evidence.

Level = impact x likelihood, as in the matrix of SDAIA's National AI Risk Management Framework:
1-2 low (منخفض), 3-6 medium (متوسط), 8-12 high (مرتفع), 16 catastrophic (كارثي).
Course rule (Al-Rukhama Family Care Society's own, not the framework's): inside the same level an
irreversible harm ranks above a costly one, and a costly one above a reversible one; then the
higher impact first.
"""
import argparse
import csv
import sys

COLS = ["id", "harm", "affected", "affected_kind", "category", "impact", "likelihood", "reversibility", "evidence"]
REV = {"irreversible": 0, "costly": 1, "reversible": 2}
CATS = ["failure", "misuse", "scale", "bias"]


def band(level):
    if level <= 2:
        return "low منخفض"
    if level <= 6:
        return "medium متوسط"
    if level <= 12:
        return "high مرتفع"
    return "catastrophic كارثي"


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("register_csv")
    ap.add_argument("--out", help="write the ranked register to this CSV file")
    ap.add_argument("--top", type=int, default=5)
    a = ap.parse_args(argv)
    try:
        with open(a.register_csv, encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
    except OSError as e:
        print(f"cannot read the file: {e.strerror}")
        return 2
    problems, ok = [], []
    for r in rows:
        rid = (r.get("id") or "?").strip()
        if not (r.get("harm") or "").strip():
            continue
        try:
            imp, lik = int(r.get("impact", "")), int(r.get("likelihood", ""))
            assert 1 <= imp <= 4 and 1 <= lik <= 4
        except (ValueError, AssertionError):
            problems.append(f"{rid}: impact and likelihood must be whole numbers from 1 to 4")
            continue
        rev = (r.get("reversibility") or "").strip()
        if rev not in REV:
            problems.append(f"{rid}: reversibility must be reversible, costly or irreversible")
            continue
        r["impact"], r["likelihood"], r["reversibility"] = imp, lik, rev
        r["level"] = imp * lik
        r["band"] = band(r["level"])
        ok.append(r)
    ok.sort(key=lambda r: (-r["level"], REV[r["reversibility"]], -r["impact"], r.get("id", "")))
    for i, r in enumerate(ok, 1):
        r["rank"] = i
    print(f"harms read: {len(ok)}")
    for i, r in enumerate(ok[: a.top], 1):
        print(f"  {i}. {r['id']:<5} level {r['level']:>2} {r['band']:<18} {r['reversibility']:<12} {r['affected_kind']:<9} {r['harm'][:70]}")
    nonusers = [r for r in ok if (r.get("affected_kind") or "").strip() == "non_user"]
    cats = {(r.get("category") or "").strip() for r in ok}
    print()
    print(f"non-user harms: {len(nonusers)} (the register needs at least 2)")
    missing = [c for c in CATS if c not in cats]
    print("categories missing: " + (", ".join(missing) if missing else "none"))
    no_evidence = [r["id"] for r in ok if not (r.get("evidence") or "").strip()]
    if no_evidence:
        print("rows without evidence or reasoning: " + ", ".join(no_evidence))
    for p in problems:
        print("check: " + p)
    if a.out:
        with open(a.out, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["rank"] + COLS + ["level", "band"], extrasaction="ignore", lineterminator="\n")
            w.writeheader()
            w.writerows(ok)
        print(f"written: {a.out.replace(chr(92), '/').split('/')[-1]}")
    complete = len(nonusers) >= 2 and not missing and not problems and len(ok) >= 10
    print("register complete enough to rank: " + ("yes" if complete else "not yet"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
