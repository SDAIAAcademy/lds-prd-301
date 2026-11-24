# /// script
# requires-python = ">=3.10"
# ///
"""Replay an oversight specification on pilot data (lab 2.1, LDS-PRD-301). Standard library only.

    uv run oversight_sim.py ../d2_1/oversight_start.json ../pilot1/pilot1_cases.csv ../d2_1/workload.csv

What it computes, week by week, from the synthetic pilot of Al-Rukhama Family Care Society:
  - second reviews: each case gets the highest sampling rate of the strata it matches (else the
    base rate); expected reviews = the sum of rates; hours = reviews x minutes_per_review / 60;
  - reach: of the audited cases whose final decision was wrong, the expected share a second
    review would correct (rate x catch_rate; catch_rate is 0.9 unless the file says otherwise);
  - triggers on workload.csv, per caseworker and week: rubber_stamp (agreement at or above
    agreement_min, median review seconds at or below median_seconds_max, at least min_cases) and
    blank_reasons (share of overrides with no reason above max_share, at least min_overrides).

The targets it checks are the society's own rules for this course, not a national text:
capacity every week, reach at least 50%, every suspect caseworker-week flagged (no override at all
and a median under 60 seconds) with false alarms on at most 10% of the others, the full set of log
fields, and segregation of duties between the deciding caseworker, the second reviewer and the
appeals reviewer.
"""
import argparse
import csv
import json
import sys

REQUIRED_LOG = ["case_id", "assistant_version", "draft", "final", "caseworker", "review_seconds",
                "override_reason", "second_review_result"]


def matches(row, when):
    return all(row.get(c) in vs for c, vs in when.items())


def case_rate(row, spec):
    sr = spec.get("second_review", {})
    rate = float(sr.get("base_rate", 0))
    for s in sr.get("strata", []):
        if matches(row, s.get("when", {})):
            rate = max(rate, float(s.get("rate", 0)))
    return min(rate, 1.0)


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("oversight_json")
    ap.add_argument("cases_csv")
    ap.add_argument("workload_csv")
    a = ap.parse_args(argv)
    try:
        with open(a.oversight_json, encoding="utf-8-sig") as f:
            spec = json.load(f)
        with open(a.cases_csv, encoding="utf-8") as f:
            cases = list(csv.DictReader(f))
        with open(a.workload_csv, encoding="utf-8") as f:
            wl = list(csv.DictReader(f))
    except OSError as e:
        print(f"cannot read a file: {e.strerror}")
        return 2
    except json.JSONDecodeError as e:
        print(f"the oversight file is not valid JSON: line {e.lineno}, column {e.colno}")
        return 2
    sr = spec.get("second_review", {})
    minutes = float(sr.get("minutes_per_review", 9))
    catch = float(sr.get("catch_rate", 0.9))
    cap = float(spec.get("capacity_hours_per_week", 10))
    results = {}

    print("second reviews by week (expected)")
    weeks = sorted({int(c["week"]) for c in cases})
    worst = 0.0
    for w in weeks:
        sub = [c for c in cases if int(c["week"]) == w]
        n = sum(case_rate(c, spec) for c in sub)
        h = n * minutes / 60
        worst = max(worst, h)
        print(f"  week {w}: {n:5.1f} reviews, {h:4.1f} h (capacity {cap:g} h){'  OVER' if h > cap + 1e-9 else ''}")
    results["capacity"] = worst <= cap + 1e-9

    aud = [c for c in cases if c.get("audit_decision")]
    wrong = [c for c in aud if c["final"] != c["audit_decision"]]
    reach = sum(case_rate(c, spec) * catch for c in wrong) / len(wrong) if wrong else 0.0
    print(f"\nreach: audited wrong final decisions {len(wrong)}; expected corrected by second review {reach:.1%}")
    results["reach"] = reach >= 0.5

    trig = spec.get("triggers", [])
    fired = set()
    for t in trig:
        for r in wl:
            key = (r["caseworker"], int(r["week"]))
            if t.get("type") == "rubber_stamp":
                if (int(r["cases"]) >= int(t.get("min_cases", 10)) and float(r["agreement_rate"]) >= float(t.get("agreement_min", 1.01))
                        and float(r["median_review_seconds"]) <= float(t.get("median_seconds_max", 0))):
                    fired.add(key)
            elif t.get("type") == "blank_reasons":
                ov = int(r["overrides"])
                if ov >= int(t.get("min_overrides", 2)) and int(r["overrides_blank_reason"]) / ov > float(t.get("max_share", 1)):
                    fired.add(key)
    suspect = {(r["caseworker"], int(r["week"])) for r in wl
               if int(r["overrides"]) == 0 and float(r["median_review_seconds"]) < 60}
    others = {(r["caseworker"], int(r["week"])) for r in wl} - suspect
    hit = len(suspect & fired)
    false_alarms = len(others & fired)
    print(f"\ntriggers: {len(trig)}; caseworker-weeks flagged {len(fired)} of {len(wl)}")
    print(f"  suspect caseworker-weeks (no override, median under 60 s): {len(suspect)}, flagged {hit}")
    print(f"  false alarms: {false_alarms} of {len(others)} other caseworker-weeks ({false_alarms / len(others):.1%})")
    by_cw = {}
    for cw, w in sorted(fired):
        by_cw.setdefault(cw, []).append(w)
    for cw, ws in by_cw.items():
        print(f"    {cw}: weeks {', '.join(map(str, ws))}")
    results["triggers"] = hit == len(suspect) and false_alarms <= 0.10 * len(others) and bool(trig)

    logs = spec.get("log_fields", [])
    missing = [f for f in REQUIRED_LOG if f not in logs]
    print("\nlog fields missing: " + (", ".join(missing) if missing else "none"))
    results["log_fields"] = not missing

    roles = spec.get("roles", {})
    d, s, p = (roles.get(k, "").strip() for k in ("decides", "second_review", "appeal_review"))
    sod = bool(d and s and p) and len({d, s, p}) == 3
    print(f"roles: decides «{d or '?'}», second review «{s or '?'}», appeal review «{p or '?'}»")
    results["segregation_of_duties"] = sod

    print("\ntargets (the society's own rules): " + ", ".join(f"{k} {'PASS' if v else 'FAIL'}" for k, v in results.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
