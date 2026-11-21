"""Fills the generated blocks of docs/TECHNOLOGY_SELECTION_REPORT.md from real data.

    python docs/tools/build_tech_report.py

1. Runs the complete pytest suite once and writes Tables 6.2 (results) and 6.3 (tests per file)
   between the markers  <!-- testsummary:start -->  and  <!-- testsummary:end -->.
2. Writes the ten-column documented test-case table (Table 6.4) and the category coverage table
   (Table 6.5) between  <!-- testcases:start -->  and  <!-- testcases:end -->.  The cases themselves come
   from build_test_cases.py (the same data the main report uses). The Status of an automated case is the real
   pytest outcome of the functions listed for it. Objective, steps, test data and type of testing are written
   here for each case. Nothing is invented: every test reference is checked against the collected tests.
3. Reads docs/SCREENSHOT_CHECKLIST.md and writes Table 6.6 and the figure placeholders between
   <!-- screenshots:start -->  and  <!-- screenshots:end -->.
"""
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_test_cases as btc  # noqa: E402

DOCS = btc.DOCS
BACKEND = btc.BACKEND
REPORT = DOCS / "TECHNOLOGY_SELECTION_REPORT.md"
CHECKLIST = DOCS / "SCREENSHOT_CHECKLIST.md"

UNIT = "Automated, unit"
API = "Automated, API"
BOTH = "Automated, unit and API"

# id: (objective, test steps, test input or data, type of testing)
EXTRA = {
 "TC-01": ("Show that a registered user can sign in and receives a token that carries the role",
           "1. Send the login request. 2. Read the status, token and user in the response. 3. Read the audit records.",
           "Administrator demo e-mail in upper case, correct demo password", API),
 "TC-02": ("Show that an employee can report an incident and that the priority is calculated from the service criticality",
           "1. Sign in as an employee. 2. Create the incident. 3. Read the stored score and priority.",
           "Title and description of valid length, impact 3, urgency 3, service Library System", API),
 "TC-03": ("Show that the assigned technician can acknowledge and that the response SLA is met",
           "1. Create an incident that is assigned automatically. 2. Advance the clock 2 minutes. 3. Acknowledge as the technician.",
           "Incident for an assigned technician, transition to ACKNOWLEDGED", API),
 "TC-04": ("Show that an administrator can assign an incident, and that an unavailable technician is refused first",
           "1. Try to assign while the technician is unavailable. 2. Make the technician available. 3. Assign again.",
           "Unassigned Storage incident, technician Imran Khan", API),
 "TC-05": ("Show that an incident can be taken through the whole lifecycle to closure with the required resolution data",
           "1. Create and assign. 2. Acknowledge and start work. 3. Resolve with summary and root cause. 4. Verify. 5. Close.",
           "Resolution summary and root cause text, closure by the reporter", API),
 "TC-06": ("Check the lowest valid combination of ratings",
           "1. Call the priority strategy with the minimum ratings. 2. Compare score and level.",
           "Impact 1, urgency 1, criticality 1", UNIT),
 "TC-07": ("Check the first and last score of every priority band",
           "1. Map each boundary score to a level. 2. Map the ratings that produce 8, 20 and 40.",
           "Scores 1, 7, 8, 19, 20, 39, 40 and 125", UNIT),
 "TC-08": ("Check the highest valid combination of ratings",
           "1. Call the priority strategy with the maximum ratings. 2. Compare score and level.",
           "Impact 5, urgency 5, criticality 5", UNIT),
 "TC-09": ("Check the exact text length limits of the incident form on the server",
           "1. Create with the maximum lengths. 2. Create again with one extra character in one field at a time.",
           "Title 200 and 201, description 5000 and 5001, affected system 200 and 201 characters", API),
 "TC-10": ("Show that a wrong password is refused without a token",
           "1. Send the login request with a wrong password. 2. Read the status and body.",
           "Existing e-mail, wrong password", API),
 "TC-11": ("Show that every missing mandatory field is rejected and named",
           "1. Create an incident with one field removed at a time. 2. Create with an empty body.",
           "Title, description, service, impact or urgency omitted", API),
 "TC-12": ("Show that ratings outside 1 to 5 are rejected by the strategy and by the API",
           "1. Call the strategy with out-of-range ratings. 2. Send the same through the API.",
           "Ratings 0, 6 and -1 in different positions; API impact 6 and urgency 0", BOTH),
 "TC-13": ("Show that an incident cannot be resolved without a resolution summary and a root cause",
           "1. Request RESOLVED with no details. 2. With only a summary. 3. With a blank summary and a root cause.",
           "Empty, partial and blank resolution fields", API),
 "TC-14": ("Show that an illegal status change is refused and changes nothing",
           "1. Request CLOSED for a new incident. 2. Try every disallowed pair of statuses at unit level.",
           "Transition NEW to CLOSED, and all other illegal pairs", BOTH),
 "TC-15": ("Show the behaviour when no technician is eligible",
           "1. Make the only Storage technician unavailable. 2. Create a Storage incident. 3. Read the status, notifications and timeline.",
           "Cloud Storage incident, category Storage", API),
 "TC-16": ("Show that the workload limit blocks assignment unless an administrator overrides",
           "1. Set the limit to 1 and fill it. 2. Assign a second incident. 3. Repeat with the override.",
           "Technician limit 1, second incident, override false then true", API),
 "TC-17": ("Show that an incident is not created when no SLA policy exists for its priority",
           "1. Deactivate the only P1 policy. 2. Create a P1 incident. 3. Count the incidents.",
           "Payment incident with impact 4, urgency 5", API),
 "TC-18": ("Show that an employee cannot read another employee's incident",
           "1. Employee A reports an incident. 2. Employee B requests it, its notes and its timeline.",
           "Incident number of employee A", API),
 "TC-19": ("Show that a technician cannot read or change an incident assigned to someone else",
           "1. Assign an incident to technician A. 2. Technician B reads it, patches its category and tries to acknowledge.",
           "Incident number, category change, acknowledge request", API),
 "TC-20": ("Show that administrator-only endpoints refuse employees and technicians",
           "1. Call each administrator endpoint as an employee, a technician and the administrator.",
           "Users, audit logs, reports, SLA policies, settings, teams, e-mail outbox and SLA lists", API),
 "TC-21": ("Show that protected endpoints require a valid token",
           "1. Call endpoints without a token. 2. With a malformed token. 3. Probe every use-case endpoint anonymously.",
           "No token, malformed token", API),
 "TC-22": ("Check that priority equals impact x urgency x business criticality",
           "1. Calculate the documented examples. 2. Create incidents through the API and read the score.",
           "Ratings (4,5,5), (3,3,4), (3,3,2), (1,2,1)", BOTH),
 "TC-23": ("Check the response and resolution targets of every priority",
           "1. Create one incident per priority. 2. Read the SLA target minutes.",
           "Priorities P1 to P4 with the standard policies", API),
 "TC-24": ("Show that every accepted status change is audited with both states",
           "1. Take an incident to RESOLVED. 2. Read the timeline as administrator.",
           "Incident moved through five transitions", API),
 "TC-25": ("Show that creation, assignment and resolution notify the right people on both channels",
           "1. Create an incident and resolve it. 2. Read the inbox of each user and the e-mail outbox.",
           "Employee, technician and administrator accounts", API),
 "TC-26": ("Show that similar incidents are flagged but never blocked or merged",
           "1. Report a payment incident. 2. Report two similar ones from other employees. 3. Read the warnings and the incident list.",
           "Three similarly worded payment incidents, similarity threshold 0.45", API),
 "TC-27": ("Show that combined search filters return only matching incidents",
           "1. Create four different incidents. 2. Apply the filters alone and in combination.",
           "Status, priority, service and SLA status filters", API),
 "TC-28": ("Check the live priority preview in the browser",
           "1. Open the report form. 2. Enter impact 2 and 300 affected users. 3. Read the preview. 4. Submit and open the incident.",
           "Impact 2, 300 affected users", "Manual (headless Chrome, 14 Nov 2026)"),
 "TC-29": ("Check that a lost connection is shown as a readable message",
           "1. Open the page. 2. Stop the front-end server. 3. Click Sign in or another action.",
           "No response from the server", "Planned, not executed"),
 "TC-30": ("Check that the whole suite passes on Windows",
           "1. Install the requirements. 2. Run python -m pytest -q in the backend folder.",
           "Windows computer with Python 3.11 or later", "Manual (Windows, 20 Nov 2026)"),
}


def full_run():
    xml = DOCS / "evidence" / ".full_junit.xml"
    subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", f"--junitxml={xml}"],
                   cwd=BACKEND, capture_output=True, text=True)
    root = ET.parse(xml).getroot()
    suite = root if root.tag == "testsuite" else root[0]
    results, per_file = {}, {}
    for tc in suite.iter("testcase"):
        file_ = tc.get("classname").split(".")[-1] + ".py"
        node = f"tests/{file_}::{tc.get('name')}"
        failed = tc.find("failure") is not None or tc.find("error") is not None
        skipped = tc.find("skipped") is not None
        st = "FAIL" if failed else ("SKIPPED" if skipped else "PASS")
        results[node] = st
        d = per_file.setdefault(file_, [0, 0])
        d[0] += 1
        d[1] += st == "PASS"
    info = {"time": float(suite.get("time", "0")), "tests": len(results)}
    xml.unlink()
    return results, per_file, info


def summary_block(results, per_file, info):
    n = len(results)
    p = sum(1 for s in results.values() if s == "PASS")
    f = sum(1 for s in results.values() if s == "FAIL")
    sk = sum(1 for s in results.values() if s == "SKIPPED")
    out = [f"**Table 6.2: Result of the complete automated suite (run of {date.today().isoformat()})**", "",
           "| Measure | Value |", "|----------------|----------------|",
           f"| Tests collected and run | {n} |", f"| Passed | {p} |", f"| Failed | {f} |", f"| Skipped | {sk} |",
           f"| Test files | {len(per_file)} |", f"| Duration of the run | {info['time']:.0f} seconds |", "",
           "**Table 6.3: Number of tests in each test file**", "",
           "| Test file | Tests | Passed |", "|----------------------------|------|------|"]
    for k in sorted(per_file):
        out.append(f"| `{k}` | {per_file[k][0]} | {per_file[k][1]} |")
    out.append(f"| **Total** | **{n}** | **{p}** |")
    return "\n".join(out), (n, p, f, sk)


def cases_block(results):
    collected = set(btc.collect())
    for *_, tests in btc.A:
        for t in tests:
            if not any(c == btc.T + t or c.startswith(btc.T + t + "[") for c in collected):
                sys.exit(f"Test reference does not exist: {t}")
    rows = []
    for tid, cat, scen, pre, inp, exp, act, tests in btc.A:
        st = btc.status_for(tests, results)
        obj, steps, data, typ = EXTRA[tid]
        ref = "; ".join(f"`{t}`" for t in tests)
        rows.append((tid, cat, scen, obj, pre, steps, data, exp, act if st == "PASS" else "See pytest output: " + st, st, typ, ref))
    for tid, cat, scen, pre, inp, exp, act, typ, st in btc.M:
        obj, steps, data, typ2 = EXTRA[tid]
        rows.append((tid, cat, scen, obj, pre, steps, data, exp, act, st, typ2, "None. " + ("Not part of the automated suite." if st == "PASS" else "Not executed.")))
    assert len(rows) == 30, len(rows)
    out = ["<!-- landscape tiny -->",
           "**Table 6.4: Documented test cases (Test ID, category, scenario, objective, preconditions, steps, input data, expected result, actual result, status, type of testing, automated test reference)**", "",
           "| Test ID | Category | Test scenario | Objective | Preconditions | Test steps | Input or test data | Expected result | Actual result | Status | Type of testing | Automated test reference |",
           "|----|-------|------------|--------------|------------|----------------|------------|--------------|--------------|-----|----------|----------------|"]
    for r in rows:
        cells = [btc.esc(x) for x in r[:11]] + [r[11].replace("|", "/")]
        out.append("| " + " | ".join(cells) + " |")
    out += ["<!-- /landscape -->", ""]
    cats = {}
    for r in rows:
        cats.setdefault(r[1], []).append(r[9])
    out += ["**Table 6.5: Coverage of the six required categories**", "",
            "| Category | Cases | Passed | Not executed | Automated | Manual or planned |", "|----------|-----|-----|-----|-----|-----|"]
    auto_ids = {a[0] for a in btc.A}
    for c in ["Normal", "Boundary", "Invalid input", "Exception", "Authorisation", "Business rule"]:
        ids = [r for r in rows if r[1] == c]
        sts = [r[9] for r in ids]
        na = sum(1 for r in ids if r[0] in auto_ids)
        out.append(f"| {c} | {len(ids)} | {sts.count('PASS')} | {sts.count('NOT EXECUTED')} | {na} | {len(ids) - na} |")
    allst = [r[9] for r in rows]
    na = sum(1 for r in rows if r[0] in auto_ids)
    out.append(f"| **Total** | **{len(rows)}** | **{allst.count('PASS')}** | **{allst.count('NOT EXECUTED')}** | **{na}** | **{len(rows) - na}** |")
    bad = [r[0] for r in rows if r[9] == "FAIL"]
    return "\n".join(out), bad, allst


def screenshot_block():
    if not CHECKLIST.exists():
        return "<!-- checklist not found -->"
    text = CHECKLIST.read_text(encoding="utf-8")
    items = []
    for m in re.finditer(r"^## (SS-(\d+)): (.*?)\n(.*?)(?=^## SS-|\Z)", text, re.S | re.M):
        body = m.group(4)
        def field(name):
            mm = re.search(rf"^- \*\*{name}:\*\* (.*)$", body, re.M)
            return mm.group(1).strip() if mm else ""
        items.append((m.group(1), int(m.group(2)), m.group(3).strip(), field("Priority"), field("Supports"), field("Caption")))
    if not items:
        sys.exit("No screenshot sections found in the checklist")
    out = ["**Table 6.6: Screenshots, the test cases or requirements they support and their report figures**", "",
           "| Screenshot | What it shows | Supports | Priority | Figure |", "|-------|--------------------------|----------------|-----------|-----|"]
    figno, nums = 0, {}
    for ss, n, title, prio, sup, cap in items:
        if (DOCS / "screenshots" / "evidence" / f"{ss}.png").exists():
            figno += 1
            nums[ss] = f"6.{figno}"
        out.append(f"| {ss} | {title} | {sup} | {prio} | {nums.get(ss, 'not captured')} |")
    have = 0
    out += ["", "Each figure below is filled in automatically when the file `SS-NN.png` exists in `docs/screenshots/evidence`. "
            "A shaded line is a placeholder for an image that has not been captured.", ""]
    for ss, n, title, prio, sup, cap in items:
        img = DOCS / "screenshots" / "evidence" / f"{ss}.png"
        if img.exists():
            have += 1
            out.append(f"![Figure {nums[ss]}: {cap}](screenshots/evidence/{ss}.png){{width=95%}}")
        else:
            out.append(f"> **{ss}, image not captured:** {cap}")
        out.append("")
    print(f"screenshots present: {have} of {len(items)}")
    return "\n".join(out)


def replace_block(text, name, block):
    pat = re.compile(rf"<!-- {name}:start -->.*?<!-- {name}:end -->", re.S)
    if not pat.search(text):
        sys.exit(f"markers for {name} not found")
    return pat.sub(lambda m: f"<!-- {name}:start -->\n{block}\n<!-- {name}:end -->", text)


def main():
    results, per_file, info = full_run()
    sblock, (n, p, f, sk) = summary_block(results, per_file, info)
    cblock, bad, allst = cases_block(results)
    text = REPORT.read_text(encoding="utf-8")
    text = replace_block(text, "testsummary", sblock)
    text = replace_block(text, "testcases", cblock)
    text = replace_block(text, "screenshots", screenshot_block())
    REPORT.write_text(text, encoding="utf-8")
    print(f"suite: {n} tests, {p} passed, {f} failed, {sk} skipped; documented cases: "
          + ", ".join(f"{k}={allst.count(k)}" for k in sorted(set(allst))))
    if bad or f:
        print("FAILED:", bad)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
