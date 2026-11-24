# /// script
# requires-python = ">=3.10"
# ///
"""Writes every synthetic data file of the course from fixed seeds. Same bytes on every run.

    uv run labs/_tools/generate.py        (from the course root)

Everything is invented: Al-Rukhama Family Care Society, its city, its rules, its caseworkers
(codes CW01 to CW12) and every application. No names, no phone numbers, no identity numbers.
The eligibility-drafting assistant is a scripted stand-in: its drafts are written here by rules
with planted errors, not by a model.
"""
import csv
import json
import math
import random
from pathlib import Path

LABS = Path(__file__).resolve().parents[1]
FILES = LABS / "files"
REF = LABS / "solutions" / "reference"

INCOME_LIMIT = 1200  # riyals a month per household member: the society's own (invented) rule

DOC_FORMS = [("typed", 0.62), ("handwritten", 0.18), ("photo", 0.20)]
DOC_LANGS = [("ar", 0.82), ("en", 0.10), ("mixed", 0.08)]
CHANNELS = [("counter", 0.55), ("web", 0.30), ("relative", 0.15)]
AGES = [("18-39", 0.35), ("40-59", 0.40), ("60+", 0.25)]
HOUSEHOLDS = [("widowed_head", 0.20), ("divorced_mother", 0.18), ("disabled_member", 0.17),
              ("unemployed_head", 0.20), ("elderly_alone", 0.10), ("large_family", 0.15)]
DISTRICTS = [("D1", 0.24), ("D2", 0.22), ("D3", 0.20), ("D4", 0.19), ("D5", 0.15)]  # D5: outlying villages


def pick(rng, table):
    x = rng.random()
    acc = 0.0
    for v, p in table:
        acc += p
        if x < acc:
            return v
    return table[-1][0]


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: r[k] for k in fields})


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def applicant(rng):
    a = {}
    a["age_band"] = pick(rng, AGES)
    hh = pick(rng, HOUSEHOLDS)
    if a["age_band"] == "60+" and rng.random() < 0.35:
        hh = "elderly_alone"
    if hh == "elderly_alone" and a["age_band"] != "60+":
        hh = "unemployed_head"
    a["household_type"] = hh
    a["members"] = 1 if hh == "elderly_alone" else (rng.randint(6, 9) if hh == "large_family" else rng.randint(2, 6))
    form = pick(rng, DOC_FORMS)
    if a["age_band"] == "60+" and form == "typed" and rng.random() < 0.45:
        form = "handwritten"
    a["doc_form"] = form
    a["doc_lang"] = pick(rng, DOC_LANGS)
    a["channel"] = pick(rng, CHANNELS)
    a["district"] = pick(rng, DISTRICTS)
    # income per member: two thirds below the limit, a tail above it
    if rng.random() < 0.66:
        inc = rng.randint(250, INCOME_LIMIT)
    else:
        inc = rng.randint(INCOME_LIMIT + 1, 2600)
    a["income_per_member"] = int(round(inc / 10.0) * 10) if inc > INCOME_LIMIT + 10 else inc
    a["docs_complete"] = "yes" if rng.random() < 0.88 else "no"
    if a["docs_complete"] == "no":
        truth = "incomplete"
    elif a["income_per_member"] <= INCOME_LIMIT:
        truth = "eligible"
    else:
        truth = "not_eligible"
    a["truth"] = truth
    return a


def draft_v10(rng, a):
    """Pilot assistant v1.0: planted errors by document form and language."""
    t = a["truth"]
    d = t
    if t in ("eligible", "not_eligible") and a["doc_lang"] in ("en", "mixed") and rng.random() < 0.15:
        return "incomplete"
    if t in ("eligible", "not_eligible") and a["doc_lang"] == "ar" and rng.random() < 0.015:
        return "incomplete"
    if t == "eligible":
        p = 0.13 if a["doc_form"] in ("handwritten", "photo") else 0.025
        if rng.random() < p:
            d = "not_eligible"
    elif t == "not_eligible" and rng.random() < 0.03:
        d = "eligible"
    elif t == "incomplete" and rng.random() < 0.02:
        d = "eligible"
    return d


def lognormal_seconds(rng, median, sigma=0.45):
    return max(8, int(round(median * math.exp(rng.gauss(0, sigma)))))


def pilot1():
    rng = random.Random(30101)
    rows = []
    n = 0
    lazy = {"CW04", "CW09"}
    for week in range(1, 9):
        catch = 0.75 - (0.75 - 0.25) * (week - 1) / 7
        med = 210 - (210 - 75) * (week - 1) / 7
        for cw in range(1, 13):
            cid = f"CW{cw:02d}"
            for _ in range(15):
                n += 1
                a = applicant(rng)
                a["case_id"] = f"R1-{n:04d}"
                a["week"] = week
                a["caseworker"] = cid
                a["draft"] = draft_v10(rng, a)
                c = 0.0 if cid in lazy else catch
                final = a["draft"]
                if a["draft"] != a["truth"] and rng.random() < c:
                    final = a["truth"]
                elif a["draft"] == a["truth"] and cid not in lazy and rng.random() < 0.01:
                    final = rng.choice([x for x in ("eligible", "not_eligible", "incomplete") if x != a["truth"]])
                a["final"] = final
                a["review_seconds"] = lognormal_seconds(rng, 35 if cid in lazy else med)
                a["overridden"] = "yes" if final != a["draft"] else "no"
                if a["overridden"] == "yes":
                    a["override_reason"] = "" if rng.random() < 0.6 else rng.choice(
                        ["income_reread", "documents_found", "rule_misapplied", "other"])
                else:
                    a["override_reason"] = ""
                wrong_denial = final in ("not_eligible", "incomplete") and a["truth"] == "eligible"
                if wrong_denial:
                    a["appealed"] = "yes" if rng.random() < 0.12 else "no"
                elif final in ("not_eligible", "incomplete"):
                    a["appealed"] = "yes" if rng.random() < 0.03 else "no"
                else:
                    a["appealed"] = "no"
                if a["appealed"] == "yes":
                    a["appeal_result"] = "overturned" if (wrong_denial and rng.random() < 0.9) else "upheld"
                else:
                    a["appeal_result"] = ""
                rows.append(a)
    return rows


PILOT_FIELDS = ["case_id", "week", "caseworker", "channel", "district", "age_band", "household_type", "members",
                "doc_form", "doc_lang", "income_per_member", "docs_complete", "draft", "final", "review_seconds",
                "overridden", "override_reason", "appealed", "appeal_result", "audit_decision"]
KEY_FIELDS = ["case_id", "truth"]


# ---------------------------------------------------------------- recorded drafts (lab 1.2)

LETTER_AR = {
    "eligible": "مسودة: بعد مراجعة طلبكم رقم {id} يقترح المساعد أن الأسرة مستحقة للإعانة الشهرية وفق القاعدة 1. يراجع الأخصائي المسودة ويتخذ القرار.",
    "not_eligible": "مسودة: بعد مراجعة طلبكم رقم {id} يقترح المساعد أن الأسرة غير مستحقة لأن دخل الفرد الشهري {inc} ريال، وهو أعلى من حد القاعدة 2. يراجع الأخصائي المسودة ويتخذ القرار.",
    "incomplete": "مسودة: طلبكم رقم {id} ينقصه مستند مطلوب وفق القاعدة 3. يراجع الأخصائي المسودة ويتخذ القرار.",
}
LETTER_EN = {
    "eligible": "Draft: after reviewing application {id}, the assistant proposes that the household is eligible for the monthly allowance under rule 1. A caseworker reviews the draft and decides.",
    "not_eligible": "Draft: after reviewing application {id}, the assistant proposes that the household is not eligible because monthly income per member is {inc} riyals, above the limit of rule 2. A caseworker reviews the draft and decides.",
    "incomplete": "Draft: application {id} is missing a required document under rule 3. A caseworker reviews the draft and decides.",
}
AI_AR = " أُعدت هذه المسودة بمساعد ذكاء اصطناعي."
AI_EN = " This draft was prepared with an AI assistant."
APPEAL_AR = " يحق لكم التظلم خلال 30 يومًا في مكتب الاستقبال أو عبر نموذج الجمعية."
APPEAL_EN = " You may appeal within 30 days at the reception office or through the society's form."


def testset():
    """250 recorded drafts of the launch candidate v1.1 (scripted, not a model). Errors are planted
    at fixed shares inside each slice, so every run gives the same counts."""
    rng = random.Random(30102)
    rows = []
    plan = ([("typed", "ar")] * 100 + [("handwritten", "ar")] * 50 + [("photo", "ar")] * 50 +
            [("typed", "en")] * 35 + [("typed", "mixed")] * 15)
    for i, (form, lang) in enumerate(plan, 1):
        a = applicant(rng)
        a["doc_form"], a["doc_lang"] = form, lang
        if a["docs_complete"] == "yes":
            a["truth"] = "eligible" if a["income_per_member"] <= INCOME_LIMIT else "not_eligible"
        a["case_id"] = f"T-{i:03d}"
        a["expected_decision"] = a["truth"]
        a["draft_decision"] = a["truth"]
        a["shown_income"] = a["income_per_member"]
        rows.append(a)
    # planted errors: (slice test, base test, share, wrong decision)
    plants = [
        (lambda r: r["doc_form"] == "photo", lambda r: r["truth"] == "eligible", 0.10, "not_eligible"),
        (lambda r: r["doc_form"] == "handwritten", lambda r: r["truth"] == "eligible", 0.04, "not_eligible"),
        (lambda r: r["doc_form"] == "typed" and r["doc_lang"] == "ar", lambda r: r["truth"] == "eligible", 0.02, "not_eligible"),
        (lambda r: r["doc_lang"] == "en", lambda r: r["truth"] != "incomplete", 0.12, "incomplete"),
        (lambda r: r["doc_lang"] == "mixed", lambda r: r["truth"] != "incomplete", 0.10, "incomplete"),
    ]
    for in_slice, in_base, share, wrong in plants:
        base = [r for r in rows if in_slice(r) and in_base(r) and r["draft_decision"] == r["truth"]]
        k = max(1, round(share * len(base)))
        for r in rng.sample(base, k):
            r["draft_decision"] = wrong
            if wrong == "not_eligible":
                r["shown_income"] = INCOME_LIMIT + rng.randint(2, 40) * 10  # the misread figure
    for r in rows:
        d = r["draft_decision"]
        r["rule_cited"] = {"eligible": "rule_1", "not_eligible": "rule_2", "incomplete": "rule_3"}[d]
        r["income_shown"] = "yes"
        r["human_check_flag"] = "yes" if (r["doc_form"] in ("handwritten", "photo") or r["doc_lang"] != "ar") else "no"
        ar = LETTER_AR[d].format(id=r["case_id"], inc=r["shown_income"]) + AI_AR
        en = LETTER_EN[d].format(id=r["case_id"], inc=r["shown_income"]) + AI_EN
        if d in ("not_eligible", "incomplete"):
            ar += APPEAL_AR
            # planted: the English template of v1.1 adds the appeal sentence only for "incomplete"
            if d == "incomplete":
                en += APPEAL_EN
        r["letter_ar"], r["letter_en"] = ar, en
    return rows


TEST_FIELDS = ["case_id", "channel", "age_band", "household_type", "doc_form", "doc_lang", "income_per_member",
               "expected_decision", "draft_decision", "rule_cited", "income_shown", "human_check_flag", "letter_ar", "letter_en"]


# ---------------------------------------------------------------- pilot 2 (capstone)

def pilot2():
    """Four weeks of v1.1 in operation with second-review sampling; a new weak slice: via a relative."""
    rng = random.Random(30103)
    rows = []
    n = 0
    for week in range(1, 5):
        for cw in range(1, 13):
            cid = f"CW{cw:02d}"
            for _ in range(15):
                n += 1
                a = applicant(rng)
                a["case_id"] = f"R2-{n:04d}"
                a["week"] = week
                a["caseworker"] = cid
                t = a["truth"]
                d = t
                r = rng.random()
                if t in ("eligible", "not_eligible") and a["doc_lang"] != "ar" and r < 0.04:
                    d = "incomplete"
                elif t == "eligible" and a["channel"] == "relative" and r < 0.12:
                    d = "not_eligible"  # planted: income of the absent applicant entered by a relative
                elif t == "eligible" and a["doc_form"] == "photo" and r < 0.05:
                    d = "not_eligible"
                elif t == "eligible" and a["doc_form"] == "handwritten" and r < 0.035:
                    d = "not_eligible"
                elif t == "eligible" and r < 0.02:
                    d = "not_eligible"
                a["draft"] = d
                lazy = cid == "CW09" and week <= 2
                catch = 0.05 if lazy else 0.6
                final = d
                if d != t and rng.random() < catch:
                    final = t
                a["final"] = final
                a["review_seconds"] = lognormal_seconds(rng, 40 if lazy else 150)
                a["overridden"] = "yes" if final != d else "no"
                a["override_reason"] = (rng.choice(["income_reread", "documents_found", "rule_misapplied", "other"])
                                        if a["overridden"] == "yes" and rng.random() < 0.85 else "")
                wrong_denial = final in ("not_eligible", "incomplete") and t == "eligible"
                if wrong_denial:
                    a["appealed"] = "yes" if rng.random() < 0.35 else "no"
                elif final in ("not_eligible", "incomplete"):
                    a["appealed"] = "yes" if rng.random() < 0.05 else "no"
                else:
                    a["appealed"] = "no"
                a["appeal_result"] = ("overturned" if wrong_denial and rng.random() < 0.9 else "upheld") if a["appealed"] == "yes" else ""
                rows.append(a)
    return rows


# ---------------------------------------------------------------- summaries

def rate(num, den):
    return round(num / den, 4) if den else None


def slice_table(rows, field, decision_key):
    out = {}
    for v in sorted({r[field] for r in rows}):
        sub = [r for r in rows if r[field] == v]
        elig = [r for r in sub if r["truth"] == "eligible"]
        fne = sum(1 for r in elig if r[decision_key] == "not_eligible")
        finc = sum(1 for r in sub if r["truth"] != "incomplete" and r[decision_key] == "incomplete")
        nonin = sum(1 for r in sub if r["truth"] != "incomplete")
        out[v] = {"n": len(sub), "eligible_n": len(elig),
                  "false_not_eligible": rate(fne, len(elig)),
                  "false_incomplete": rate(finc, nonin)}
    return out


def workload(rows):
    out = []
    for cw in sorted({r["caseworker"] for r in rows}):
        for week in sorted({r["week"] for r in rows}):
            sub = [r for r in rows if r["caseworker"] == cw and r["week"] == week]
            secs = sorted(r["review_seconds"] for r in sub)
            med = secs[len(secs) // 2] if len(secs) % 2 else (secs[len(secs) // 2 - 1] + secs[len(secs) // 2]) / 2
            ov = [r for r in sub if r["overridden"] == "yes"]
            out.append({"caseworker": cw, "week": week, "cases": len(sub),
                        "review_hours_available": 6,
                        "median_review_seconds": int(med),
                        "agreement_rate": round(1 - len(ov) / len(sub), 3),
                        "overrides": len(ov),
                        "overrides_blank_reason": sum(1 for r in ov if not r["override_reason"])})
    return out


def summary(rows, decision_key="final"):
    wrong = [r for r in rows if r[decision_key] != r["truth"]]
    wd = [r for r in rows if r[decision_key] in ("not_eligible", "incomplete") and r["truth"] == "eligible"]
    draft_wrong = [r for r in rows if r["draft"] != r["truth"]]
    caught = [r for r in draft_wrong if r["final"] == r["truth"]]
    ap = [r for r in rows if r["appealed"] == "yes"]
    ov = [r for r in rows if r["overridden"] == "yes"]
    weeks = sorted({r["week"] for r in rows})
    by_week = {}
    for w in weeks:
        sub = [r for r in rows if r["week"] == w]
        dw = [r for r in sub if r["draft"] != r["truth"]]
        secs = sorted(r["review_seconds"] for r in sub)
        by_week[w] = {"agreement": round(1 - sum(1 for r in sub if r["overridden"] == "yes") / len(sub), 3),
                      "median_review_seconds": secs[len(secs) // 2],
                      "draft_errors": len(dw),
                      "draft_errors_caught": sum(1 for r in dw if r["final"] == r["truth"])}
    return {
        "cases": len(rows),
        "draft_errors": len(draft_wrong),
        "draft_errors_caught": len(caught),
        "final_wrong": len(wrong),
        "wrongful_denials": len(wd),
        "wrongful_denials_appealed": sum(1 for r in wd if r["appealed"] == "yes"),
        "appeals": len(ap),
        "appeals_overturned": sum(1 for r in ap if r["appeal_result"] == "overturned"),
        "overrides": len(ov),
        "overrides_blank_reason": sum(1 for r in ov if not r["override_reason"]),
        "agreement_overall": round(1 - len(ov) / len(rows), 3),
        "by_week": by_week,
        "by_doc_form": slice_table(rows, "doc_form", decision_key),
        "by_doc_lang": slice_table(rows, "doc_lang", decision_key),
        "by_age_band": slice_table(rows, "age_band", decision_key),
        "by_channel": slice_table(rows, "channel", decision_key),
        "by_district": slice_table(rows, "district", decision_key),
        "draft_by_doc_form": slice_table(rows, "doc_form", "draft"),
        "draft_by_doc_lang": slice_table(rows, "doc_lang", "draft"),
        "draft_by_channel": slice_table(rows, "channel", "draft"),
        "draft_by_age_band": slice_table(rows, "age_band", "draft"),
        "lazy_caseworkers": {cw: {"overrides": sum(1 for r in rows if r["caseworker"] == cw and r["overridden"] == "yes"),
                                  "median_review_seconds": sorted(r["review_seconds"] for r in rows if r["caseworker"] == cw)[
                                      len([r for r in rows if r["caseworker"] == cw]) // 2]}
                             for cw in ("CW04", "CW09")},
    }


def add_audit(rows, seed, share=0.25):
    """A random quarter of cases re-decided by two senior caseworkers: the audited decision is the truth."""
    rng = random.Random(seed)
    for r in rows:
        r["audit_decision"] = r["truth"] if rng.random() < share else ""


def main():
    p1 = pilot1()
    add_audit(p1, 30111)
    write_csv(FILES / "pilot1" / "pilot1_cases.csv", p1, PILOT_FIELDS)
    write_csv(REF / "pilot1_truth.csv", p1, KEY_FIELDS)
    wl = workload(p1)
    write_csv(FILES / "d2_1" / "workload.csv", wl, list(wl[0].keys()))
    ts = testset()
    write_csv(FILES / "d1_2" / "drafts_v11.csv", ts, TEST_FIELDS)
    write_csv(REF / "drafts_v11_truth.csv", ts, KEY_FIELDS)
    p2 = pilot2()
    add_audit(p2, 30113, share=0.4)
    write_csv(FILES / "capstone" / "pilot2_cases.csv", p2, PILOT_FIELDS)
    write_csv(REF / "pilot2_truth.csv", p2, KEY_FIELDS)
    wl2 = workload(p2)
    write_csv(FILES / "capstone" / "pilot2_workload.csv", wl2, list(wl2[0].keys()))
    au1 = [r for r in p1 if r["audit_decision"]]
    au2 = [r for r in p2 if r["audit_decision"]]
    write_json(REF / "stats.json", {"pilot1": summary(p1), "pilot1_audit": summary(au1),
                                    "pilot2": summary(p2), "pilot2_audit": summary(au2)})
    print("pilot1", len(p1), "testset", len(ts), "pilot2", len(p2))


if __name__ == "__main__":
    main()
