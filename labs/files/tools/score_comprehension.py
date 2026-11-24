# /// script
# requires-python = ">=3.10"
# ///
"""Score the peer comprehension test of the notices (lab 1.3, LDS-PRD-301). Standard library only.

    uv run score_comprehension.py ../d1_3/answers_start.csv ../d1_3/comprehension_key.json

answers CSV columns: notice (N1 or N2), lang (ar or en), reader (a code, never a name), q1 to q5
(the letter each reader chose: A, B, C or D). The key file holds the right letter of each
question for each notice. The course's rule: a notice passes in a language when at least two
peers read it and every one of them answers at least four of the five questions correctly.
"""
import argparse
import csv
import json
import sys
from collections import defaultdict


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("answers_csv")
    ap.add_argument("key_json")
    a = ap.parse_args(argv)
    try:
        with open(a.key_json, encoding="utf-8-sig") as f:
            key = json.load(f)["key"]
        with open(a.answers_csv, encoding="utf-8-sig") as f:
            rows = [r for r in csv.DictReader(f) if (r.get("reader") or "").strip()]
    except OSError as e:
        print(f"cannot read a file: {e.strerror}")
        return 2
    if not rows:
        print("no answers yet: add one row per reader, notice and language")
        return 0
    groups = defaultdict(list)
    for r in rows:
        groups[(r["notice"].strip(), r["lang"].strip())].append(r)
    missed_all = defaultdict(int)
    for (notice, lang), rs in sorted(groups.items()):
        k = key.get(notice)
        if not k:
            print(f"{notice}: no key for this notice")
            continue
        scores = []
        missed = defaultdict(int)
        for r in rs:
            s = 0
            for q in ("q1", "q2", "q3", "q4", "q5"):
                if (r.get(q) or "").strip().upper() == k[q]:
                    s += 1
                else:
                    missed[q] += 1
                    missed_all[(notice, q)] += 1
            scores.append((r["reader"].strip(), s))
        ok = len(scores) >= 2 and all(s >= 4 for _, s in scores)
        print(f"{notice} {lang}: " + ", ".join(f"{who} {s}/5" for who, s in scores) + f"  ->  {'PASS' if ok else 'FAIL'}")
        if missed:
            print("   missed: " + ", ".join(f"{q} x{n}" for q, n in sorted(missed.items(), key=lambda x: -x[1])))
        if len(scores) < 2:
            print("   needs at least two readers")
    return 0


if __name__ == "__main__":
    sys.exit(main())
