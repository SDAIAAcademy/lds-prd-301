# /// script
# requires-python = ">=3.10"
# ///
"""Answer-key statistics for assessments/bank.json and the deck checkpoints.

Prints key positions, the true/false balance, and how often the key is the
longest or the shortest option, so the spread can be checked without counting
by hand. Run from the course root: uv run labs/_tools/bank_stats.py
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def strip(html):
    return re.sub(r"<[^>]+>", "", html).strip()


def deck_items():
    items = []
    for deck in sorted((ROOT / "slides").glob("*.html")):
        s = deck.read_text(encoding="utf-8")
        for m in re.finditer(r'<div class="quiz"[^>]*>(.*?)<div class="callout tip why">', s, re.S):
            opts = re.findall(r'<div class="opt"( data-ok)?[^>]*>(.*?)</div>', m.group(1), re.S)
            items.append((f"{deck.stem}", [strip(o[1]) for o in opts], [i for i, o in enumerate(opts) if o[0]]))
    return items


def summarise(label, items):
    pos, extreme, n = Counter(), 0, 0
    for _, opts, keys in items:
        if len(keys) != 1:
            continue
        n += 1
        k = keys[0]
        pos["ABCDEFG"[k]] += 1
        lens = [len(o) for o in opts]
        if lens[k] == max(lens) or lens[k] == min(lens):
            extreme += 1
    print(f"{label}: {n} single-answer items; key positions " + ", ".join(f"{p} {pos[p]}" for p in sorted(pos)))
    if n:
        print(f"  key is the longest or the shortest option in {extreme} of {n} ({extreme / n:.0%})")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    bank = json.loads((ROOT / "assessments" / "bank.json").read_text(encoding="utf-8"))["questions"]
    types = Counter(q["type"] for q in bank)
    print("bank: " + ", ".join(f"{t} {c}" for t, c in sorted(types.items())))
    tf = [q for q in bank if q["type"] in ("truefalse", "true_false", "tf")]
    if tf:
        vals = Counter(str(q.get("correct")) for q in tf)
        print("  true/false keys: " + ", ".join(f"{k} {v}" for k, v in sorted(vals.items())))
    single = [(q["id"], q["options"], q["correct"]) for q in bank if q["type"] == "single"]
    summarise("bank single", single)
    summarise("deck checkpoints", deck_items())
    by_lo = Counter(q["id"].split("-")[1] for q in bank)
    print("bank by outcome: " + ", ".join(f"{k.upper()} {v}" for k, v in sorted(by_lo.items())))


if __name__ == "__main__":
    main()
