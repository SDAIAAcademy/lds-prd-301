# /// script
# requires-python = ">=3.10"
# ///
"""Run safeguard tests on recorded drafts (lab 1.2, LDS-PRD-301). Standard library only; no network.

    uv run run_tests.py ../d1_2/safeguards_start.json ../d1_2/drafts_v11.csv
    uv run run_tests.py my_safeguards.json ../d1_2/drafts_v11.csv

The drafts are the recorded outputs of the launch candidate v1.1 of the eligibility-drafting
assistant: a scripted stand-in written by the course's data generator, not a model. Each row has
the expected decision a senior caseworker labelled.

A safeguard: {"id", "harm", "requirement", "owner", "test_owner", "tests": [ ... ]}. Test types:
  rate_max     {"metric": "false_not_eligible" | "false_incomplete" | "wrong_any",
                "slice_by": "<column>" (optional), "max": 0.05, "min_n": 20}
  gap_max      {"metric": ..., "slice_by": "<column>", "max_gap": 0.03, "min_n": 20}
  letter_has   {"lang": "ar" | "en" | "both", "marker": "appeal_route" | "ai_disclosure" | "draft_label" |
                "rule_named", "when_decision": ["not_eligible", "incomplete"], "min_share": 1.0}
  field_equals {"field": "<column>", "value": "yes", "when": {"<column>": ["v1", "v2"]}, "min_share": 1.0}
A slice whose base is below min_n is "too few": it is reported and the test cannot pass on it.
A safeguard whose test_owner is its owner is flagged: the person who builds a safeguard does not
sign off its test.
"""
import argparse
import csv
import json
import re
import sys

MARKERS = {
    "appeal_route": {"ar": r"التظلم", "en": r"\bappeal\b"},
    "ai_disclosure": {"ar": r"ذكاء اصطناعي", "en": r"\bAI assistant\b"},
    "draft_label": {"ar": r"مسودة", "en": r"\bDraft\b"},
    "rule_named": {"ar": r"القاعدة \d", "en": r"\brule \d"},
}


def metric_counts(rows, metric):
    if metric == "false_not_eligible":
        base = [r for r in rows if r["expected_decision"] == "eligible"]
        bad = [r for r in base if r["draft_decision"] == "not_eligible"]
    elif metric == "false_incomplete":
        base = [r for r in rows if r["expected_decision"] != "incomplete"]
        bad = [r for r in base if r["draft_decision"] == "incomplete"]
    elif metric == "wrong_any":
        base = rows
        bad = [r for r in rows if r["draft_decision"] != r["expected_decision"]]
    else:
        raise ValueError(f"unknown metric {metric}")
    return len(bad), len(base)


def slices(rows, field):
    if not field:
        return [("all", rows)]
    if field not in rows[0]:
        raise ValueError(f"unknown column {field}")
    return [(v, [r for r in rows if r[field] == v]) for v in sorted({r[field] for r in rows})]


def run_test(t, rows):
    kind = t.get("type")
    lines, passed = [], True
    if kind in ("rate_max", "gap_max"):
        min_n = int(t.get("min_n", 20))
        rates = []
        for v, sub in slices(rows, t.get("slice_by")):
            k, n = metric_counts(sub, t["metric"])
            if n < min_n:
                lines.append(f"      {v}: {k}/{n} too few")
                passed = False
                continue
            r = k / n
            rates.append(r)
            flag = ""
            if kind == "rate_max" and r > float(t["max"]):
                flag, passed = " FAIL", False
            lines.append(f"      {v}: {k}/{n} = {r:.1%}{flag}")
        if kind == "gap_max" and rates:
            gap = max(rates) - min(rates)
            ok = gap <= float(t["max_gap"])
            passed = passed and ok
            lines.append(f"      gap {gap:.1%} (max {float(t['max_gap']):.0%}){'' if ok else ' FAIL'}")
        head = f"{kind} {t['metric']}" + (f" by {t['slice_by']}" if t.get("slice_by") else "") + \
            (f" <= {float(t['max']):.0%}" if kind == "rate_max" else "")
    elif kind == "letter_has":
        marker = t["marker"]
        langs = ["ar", "en"] if t.get("lang", "both") == "both" else [t["lang"]]
        when = t.get("when_decision")
        sub = [r for r in rows if not when or r["draft_decision"] in when]
        need = float(t.get("min_share", 1.0))
        for lang in langs:
            pat = re.compile(MARKERS[marker][lang])
            k = sum(1 for r in sub if pat.search(r[f"letter_{lang}"]))
            share = k / len(sub) if sub else 0.0
            ok = share >= need
            passed = passed and ok
            lines.append(f"      letter_{lang}: {k}/{len(sub)} = {share:.1%}{'' if ok else ' FAIL'}")
        head = f"letter_has {marker}" + (f" when {'/'.join(when)}" if when else "")
    elif kind == "field_equals":
        when = t.get("when", {})
        sub = [r for r in rows if all(r[c] in vs for c, vs in when.items())]
        k = sum(1 for r in sub if r[t["field"]] == t["value"])
        share = k / len(sub) if sub else 0.0
        passed = share >= float(t.get("min_share", 1.0))
        lines.append(f"      {k}/{len(sub)} = {share:.1%}{'' if passed else ' FAIL'}")
        head = f"field_equals {t['field']}={t['value']}"
    else:
        raise ValueError(f"unknown test type {kind}")
    return passed, head, lines


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("safeguards_json")
    ap.add_argument("drafts_csv")
    a = ap.parse_args(argv)
    try:
        with open(a.safeguards_json, encoding="utf-8-sig") as f:
            spec = json.load(f)
        with open(a.drafts_csv, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    except OSError as e:
        print(f"cannot read a file: {e.strerror}")
        return 2
    except json.JSONDecodeError as e:
        print(f"the safeguards file is not valid JSON: line {e.lineno}, column {e.colno}")
        return 2
    sg = spec.get("safeguards", [])
    print(f"drafts: {len(rows)} (recorded, scripted stand-in) · safeguards: {len(sg)}")
    summary = []
    for s in sg:
        sid = s.get("id", "?")
        print(f"\n{sid} · harm {s.get('harm', '?')} · owner: {s.get('owner', '?')} · test owner: {s.get('test_owner', '?')}")
        notes = []
        if not s.get("owner") or not s.get("test_owner"):
            notes.append("an owner and a test owner are both required")
        elif s["owner"].strip() == s["test_owner"].strip():
            notes.append("segregation of duties: the owner signs off their own test")
        if not s.get("tests"):
            notes.append("no test: a safeguard without a pass or fail test is a wish")
        all_ok = bool(s.get("tests"))
        for t in s.get("tests", []):
            try:
                ok, head, lines = run_test(t, rows)
            except (KeyError, ValueError) as e:
                ok, head, lines = False, f"{t.get('type', '?')}", [f"      cannot run this test: {e}"]
            all_ok = all_ok and ok
            print(f"   {'PASS' if ok else 'FAIL'} {head}")
            for ln in lines:
                print(ln)
        for n in notes:
            print(f"   check: {n}")
        summary.append((sid, all_ok and not notes))
    print("\nsummary: " + ", ".join(f"{sid} {'PASS' if ok else 'FAIL'}" for sid, ok in summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
