# /// script
# requires-python = ">=3.10"
# ///
"""The parallel example of the slides: the society's emergency rent aid service (إعانة الإيجار
الطارئة), where an assistant drafts an urgency priority (urgent or normal) for a caseworker. Its
numbers differ from the case's on purpose, so no slide gives away a lab answer. Fixed seed.

    uv run labs/_tools/examples.py        (from the course root)

Writes labs/solutions/reference/examples.json and prints every number the slides quote.
"""
import json
import math
import random
from pathlib import Path

REF = Path(__file__).resolve().parents[1] / "solutions" / "reference"


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(c - h, 4), round(c + h, 4))


def main():
    rng = random.Random(30199)
    rows = []
    for i in range(600):
        form = "photo" if rng.random() < 0.22 else "typed"
        urgent = rng.random() < 0.40
        r = rng.random()
        if urgent and form == "photo":
            draft = "normal" if r < 0.11 else "urgent"
        elif urgent:
            draft = "normal" if r < 0.015 else "urgent"
        else:
            draft = "urgent" if r < 0.03 else "normal"
        rows.append({"form": form, "urgent": urgent, "draft": draft})
    out = {}
    allu = [r for r in rows if r["urgent"]]
    k = sum(1 for r in allu if r["draft"] == "normal")
    out["overall"] = {"k": k, "n": len(allu), "rate": round(k / len(allu), 4)}
    for f in ("typed", "photo"):
        sub = [r for r in allu if r["form"] == f]
        kk = sum(1 for r in sub if r["draft"] == "normal")
        out[f] = {"k": kk, "n": len(sub), "rate": round(kk / len(sub), 4)}
    # a small slice: the same rate on 12 cases, and its interval
    out["small_slice"] = {"k": 1, "n": 12, "rate": round(1 / 12, 4), "wilson95": wilson(1, 12)}
    out["photo"]["wilson95"] = wilson(out["photo"]["k"], out["photo"]["n"])
    # oversight arithmetic of the example: one supervisor, 4 hours a week, 12 minutes a review
    cap_reviews = 4 * 60 // 12
    out["capacity"] = {"hours": 4, "minutes_per_review": 12, "reviews_per_week": cap_reviews,
                       "requests_per_week": 90, "max_share": round(cap_reviews / 90, 4)}
    # rubber-stamp example: two caseworkers of the rent aid desk over six weeks
    out["rubber_stamp"] = {"desk_A": {"agreement": [0.94, 0.95, 0.93, 0.95, 0.94, 0.96], "median_seconds": [160, 150, 155, 148, 152, 150]},
                           "desk_B": {"agreement": [0.95, 0.98, 1.0, 1.0, 1.0, 1.0], "median_seconds": [140, 95, 60, 41, 38, 36]}}
    # harms ranking example (level = impact x likelihood)
    out["ranking"] = [
        {"harm": "urgent request drafted normal, eviction proceeds", "impact": 4, "likelihood": 2, "level": 8, "reversibility": "irreversible"},
        {"harm": "normal request drafted urgent, queue jumps", "impact": 2, "likelihood": 4, "level": 8, "reversibility": "reversible"},
        {"harm": "landlord learns of the request from a letter", "impact": 3, "likelihood": 2, "level": 6, "reversibility": "irreversible"},
        {"harm": "letter in Arabic only", "impact": 2, "likelihood": 3, "level": 6, "reversibility": "costly"},
    ]
    # comprehension example: six readers of a rent aid letter, correct answers per reader
    out["comprehension"] = {"before": [3, 2, 4, 3, 3, 2], "after": [5, 4, 4, 5, 4, 5], "missed_most_before": "q4 deadline"}
    REF.mkdir(parents=True, exist_ok=True)
    (REF / "examples.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
