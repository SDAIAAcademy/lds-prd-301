# /// script
# requires-python = ">=3.10"
# ///
"""Runs every lab tool on its starting file and on the reference solution, and checks the numbers
the slides, the lab pages and the answer key quote. Standard library only; no network.

    uv run labs/solutions/check.py        (from the course root)
"""
import csv
import json
import subprocess
import sys
from pathlib import Path

LABS = Path(__file__).resolve().parents[1]
TOOLS = LABS / "files" / "tools"
REF = LABS / "solutions" / "reference"
F = LABS / "files"
fails = 0


def ok(cond, msg):
    global fails
    if not cond:
        fails += 1
    print(("PASS " if cond else "FAIL ") + msg)


def run(tool, *args):
    p = subprocess.run([sys.executable, "-B", str(TOOLS / tool), *map(str, args)], capture_output=True,
                       text=True, encoding="utf-8", cwd=TOOLS)
    return p.returncode, p.stdout + p.stderr


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    stats = json.loads((REF / "stats.json").read_text(encoding="utf-8"))

    # participant files carry no truth column
    for rel in ["pilot1/pilot1_cases.csv", "capstone/pilot2_cases.csv"]:
        with open(F / rel, encoding="utf-8") as f:
            head = next(csv.reader(f))
        ok("truth" not in head, f"{rel}: no truth column ({len(head)} columns)")

    # 1.1
    rc, out = run("rank_harms.py", F / "d1_1" / "register_start.csv")
    ok(rc == 0 and "not yet" in out, "1.1 start register runs and is reported incomplete")
    rc, out = run("rank_harms.py", REF / "register_reference.csv")
    top = [ln.split()[1] for ln in out.splitlines() if ln.strip()[:2] in ("1.", "2.", "3.", "4.", "5.")]
    ok(rc == 0 and sorted(top) == ["H01", "H02", "H03", "H04", "H05"], f"1.1 reference top five {top}")
    ok("non-user harms: 3" in out and "categories missing: none" in out, "1.1 reference has non-users and all four categories")
    rc, out = run("slices.py", F / "pilot1" / "pilot1_cases.csv")
    ok("6/50  12.0% FAIL" in out and "4/29  13.8% FAIL" in out and "3/30  10.0% FAIL" in out,
       "1.1 pilot-1 audit slices: photo 12.0%, mixed 13.8%, English 10.0%")
    a1 = stats["pilot1_audit"]
    ok(a1["cases"] == 392 and a1["draft_errors"] == 25 and a1["draft_errors_caught"] == 10
       and a1["wrongful_denials"] == 15 and a1["wrongful_denials_appealed"] == 3,
       "1.1 audit: 392 cases, 25 draft errors, 10 caught, 15 wrongful denials, 3 appealed")
    p1 = stats["pilot1"]
    ok(p1["agreement_overall"] == 0.962 and p1["by_week"]["1"]["median_review_seconds"] == 178
       and p1["by_week"]["8"]["median_review_seconds"] == 67 and p1["appeals"] == 22 and p1["appeals_overturned"] == 4,
       "1.1 pilot report: 96.2% agreement, 178 to 67 seconds, 22 appeals, 4 overturned")

    # 1.2
    rc, out = run("run_tests.py", F / "d1_2" / "safeguards_start.json", F / "d1_2" / "drafts_v11.csv")
    ok(rc == 0 and "summary: S0 PASS" in out and "all: 11/250 = 4.4%" in out, "1.2 start file runs (S0 passes on the whole set, 11/250)")
    rc, out = run("run_tests.py", REF / "safeguards_reference.json", F / "d1_2" / "drafts_v11.csv")
    ok("summary: S1 FAIL, S2 FAIL, S3 FAIL, S4 PASS, S5 PASS" in out, "1.2 reference: S1 to S3 fail, S4 and S5 pass")
    ok("photo: 3/26 = 11.5% FAIL" in out and "en: 4/34 = 11.8% FAIL" in out and "mixed: 2/15 too few" in out
       and "letter_en: 38/124 = 30.6% FAIL" in out, "1.2 reference numbers: photo 11.5%, English 11.8%, mixed too few, English letters 30.6%")
    ok("segregation of duties" not in out, "1.2 reference: no safeguard owner signs off their own test")

    # 1.3
    rc, out = run("score_comprehension.py", F / "d1_3" / "answers_start.csv", F / "d1_3" / "comprehension_key.json")
    ok(rc == 0 and "no answers yet" in out, "1.3 empty answers file runs")
    rc, out = run("score_comprehension.py", REF / "answers_sample.csv", F / "d1_3" / "comprehension_key.json")
    ok("N2 en: P3 4/5, P4 3/5  ->  FAIL" in out and "N2 ar: P1 5/5, P2 4/5  ->  PASS" in out, "1.3 sample: N2 Arabic passes, English fails on q4")
    key = json.loads((F / "d1_3" / "comprehension_key.json").read_text(encoding="utf-8"))["key"]
    letters = "".join(v for k in key.values() for v in k.values())
    ok(all(letters.count(c) >= 2 for c in "ABCD"), f"1.3 key letters spread: {letters}")

    # 2.1
    rc, out = run("oversight_sim.py", F / "d2_1" / "oversight_start.json", F / "pilot1" / "pilot1_cases.csv", F / "d2_1" / "workload.csv")
    ok(rc == 0 and "capacity PASS, reach FAIL, triggers FAIL, log_fields FAIL, segregation_of_duties FAIL" in out,
       "2.1 start file runs and fails every target but capacity")
    ok("expected corrected by second review 1.8%" in out, "2.1 start reach 1.8%")
    rc, out = run("oversight_sim.py", REF / "oversight_reference.json", F / "pilot1" / "pilot1_cases.csv", F / "d2_1" / "workload.csv")
    ok("capacity PASS, reach PASS, triggers PASS, log_fields PASS, segregation_of_duties PASS" in out and "corrected by second review 63.3%" in out and "9.8 h" in out and "false alarms: 5 of 80" in out, "2.1 reference passes every target on pilot 1: reach 63.3%, top week 9.8 h, 5 false alarms of 80")
    reach = [ln for ln in out.splitlines() if ln.startswith("reach")]
    print("     " + reach[0] if reach else "     no reach line")
    rc, out = run("oversight_sim.py", REF / "oversight_reference.json", F / "capstone" / "pilot2_cases.csv", F / "capstone" / "pilot2_workload.csv")
    ok("capacity PASS, reach PASS, triggers PASS, log_fields PASS, segregation_of_duties PASS" in out and "CW09: weeks 1, 2" in out and "9.2 h" in out and "false alarms: 0 of 46" in out, "capstone: the reference spec passes on pilot 2, top week 9.2 h, flags CW09 in weeks 1 and 2, no false alarm")

    # capstone
    rc, out = run("slices.py", F / "capstone" / "pilot2_cases.csv", "--by", "channel,doc_lang,age_band,doc_form")
    ok("5/23  21.7% FAIL" in out and "0/15 too few" in out, "capstone pilot-2 audit: relative channel 21.7%, English too few for false not eligible")
    ok("1/29   3.4% ok" in out and "2/22   9.1% FAIL" in out and "5/64   7.8% FAIL" in out, "capstone inject cards: 60+ 3.4% ok, English false incomplete 9.1%, 18-39 7.8%")
    print(f"\n{'all checks passed' if not fails else str(fails) + ' check(s) failed'}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
