"""Executes the automated tests behind every documented test case and writes the case tables into
docs/FINAL_PROJECT_REPORT.md (between the markers  <!-- testcases:start -->  and  <!-- testcases:end -->).

    python docs/tools/build_test_cases.py

The Status of an automated case is the real pytest outcome of the tests listed for it (PASS only if every
listed test passed). Manual and planned cases carry a fixed status and say so in the Type column.
Nothing here is invented: each test reference is checked against the collected test ids before running.
"""
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

DOCS = Path(__file__).resolve().parents[1]
BACKEND = DOCS.parent / "backend"
REPORT = DOCS / "FINAL_PROJECT_REPORT.md"
T = "tests/"

# id, category, scenario, preconditions, input, expected, actual (what the assertions observed), tests
A = [
 ("TC-01", "Normal", "Successful login with valid credentials",
  "Demo administrator account exists", "POST /api/auth/login with the administrator e-mail (upper case) and the correct password",
  "HTTP 200, bearer token and user with role ADMIN; the sign-in is audited",
  "HTTP 200, token_type bearer, user role ADMIN, audit action USER_LOGIN present",
  ["test_auth.py::test_login_success_returns_token_and_user_and_is_audited"]),
 ("TC-02", "Normal", "Employee creates an incident",
  "Employee signed in; service Library System (criticality 2) exists",
  "POST /api/incidents: title and description valid, impact 3, urgency 3",
  "Incident created; priority computed from the service criticality; score 18 and P3",
  "Created with score 18, priority P3, business_criticality 2, criticality not overridden",
  ["test_priority.py::test_api_calculates_priority_and_takes_criticality_from_service"]),
 ("TC-03", "Normal", "Technician acknowledges an assigned incident",
  "Incident created and automatically assigned to a technician; clock advanced 2 minutes",
  "POST transition to ACKNOWLEDGED as the assigned technician",
  "HTTP 200, status ACKNOWLEDGED, acknowledged_at set, response SLA marked MET",
  "HTTP 200, status ACKNOWLEDGED, timestamp 2 minutes after creation, response SLA state MET",
  ["test_lifecycle.py::test_t09_assigned_technician_acknowledges_and_timestamp_is_set"]),
 ("TC-04", "Normal", "Administrator assigns an incident to an eligible technician",
  "Unassigned Storage incident; technician Imran Khan initially unavailable",
  "POST /api/incidents/{n}/assign as administrator, first while unavailable, then after setting is_available true",
  "Refused while unavailable; accepted once available; status ASSIGNED",
  "First call HTTP 409 TECHNICIAN_UNAVAILABLE; second call HTTP 200, technician Imran Khan, status ASSIGNED",
  ["test_assignment.py::test_admin_assigns_manually_after_making_technician_available"]),
 ("TC-05", "Normal", "Resolve an incident with the required resolution details",
  "Incident assigned and in progress", "Transition to RESOLVED with resolution_summary and root_cause, then verify and close",
  "Incident reaches RESOLVED, then VERIFIED and CLOSED through the legal steps",
  "Full lifecycle NEW to CLOSED completed with every step accepted",
  ["test_lifecycle.py::test_full_lifecycle_to_closed"]),
 ("TC-06", "Boundary", "Priority with the minimum valid ratings",
  "None", "calculate(impact 1, urgency 1, criticality 1)",
  "Score 1 and level P4", "Score 1 and level P4 (parametrised case ratings7)",
  ["test_priority.py::test_documented_examples_and_boundaries[ratings7-1-P4]"]),
 ("TC-07", "Boundary", "Priority level at the lower and upper limit of every band",
  "Default thresholds", "level_for_score for 1, 7, 8, 19, 20, 39, 40 and 125",
  "1 and 7 give P4; 8 and 19 give P3; 20 and 39 give P2; 40 and 125 give P1",
  "All eight boundary scores mapped to the expected level; also the products 8, 20 and 40 from ratings give P3, P2 and P1",
  ["test_priority.py::test_t06_t07_threshold_boundaries", "test_priority.py::test_documented_examples_and_boundaries[ratings4-8-P3]",
   "test_priority.py::test_documented_examples_and_boundaries[ratings5-20-P2]", "test_priority.py::test_documented_examples_and_boundaries[ratings6-40-P1]"]),
 ("TC-08", "Boundary", "Priority with the maximum valid ratings",
  "None", "calculate(impact 5, urgency 5, criticality 5)",
  "Score 125 and level P1", "Score 125 and level P1 (parametrised case ratings8)",
  ["test_priority.py::test_documented_examples_and_boundaries[ratings8-125-P1]"]),
 ("TC-09", "Boundary", "Maximum permitted text lengths",
  "Employee signed in; limits in the schema: title 200, description 5000, affected system 200 characters",
  "Create with exactly 200, 5000 and 200 characters; then with 201, 5001 and 201 characters, one field at a time",
  "Maximum lengths accepted with HTTP 201; one character more rejected with HTTP 422 naming the field",
  "Creation with the maximum lengths returned 201 and stored a 200 character title; each over-length field returned 422 with that field named",
  ["test_documented_cases.py::test_tc09_maximum_permitted_text_lengths_are_accepted_and_one_more_is_rejected"]),
 ("TC-10", "Invalid input", "Login with an incorrect password",
  "Registered user exists", "POST /api/auth/login with a wrong password",
  "HTTP 401, no token, error code AUTHENTICATION_FAILED",
  "HTTP 401 without a token in the response",
  ["test_auth.py::test_t03_login_with_wrong_password_returns_401_without_token"]),
 ("TC-11", "Invalid input", "Incident creation with missing mandatory fields",
  "Employee signed in", "POST /api/incidents omitting in turn title, description, service_id, impact, urgency; and an empty body",
  "HTTP 422 each time, with the missing field named",
  "Every omission returned 422 and the response listed the omitted field; the empty body returned 422",
  ["test_documented_cases.py::test_tc11_missing_mandatory_fields_are_rejected_and_named"]),
 ("TC-12", "Invalid input", "Ratings outside the range 1 to 5",
  "None", "calculate with (0,3,3), (6,3,3), (3,0,3), (3,3,6), (-1,1,1); API with impact 6 and urgency 0",
  "InvalidInputError in the strategy; HTTP 422 naming the field through the API",
  "All five strategy calls raised InvalidInputError; API returned 422 with the field impact or urgency named",
  ["test_priority.py::test_invalid_ratings_are_rejected", "test_priority.py::test_incident_validation_errors_are_meaningful"]),
 ("TC-13", "Invalid input", "Resolve without the mandatory resolution details",
  "Incident IN_PROGRESS", "Transition to RESOLVED with nothing; with summary only; with a blank summary and a root cause",
  "HTTP 422 each time; the message mentions the root cause; status stays IN_PROGRESS",
  "All three requests returned 422, the message contained 'root cause', status remained IN_PROGRESS",
  ["test_lifecycle.py::test_t10_resolve_without_summary_or_root_cause_is_rejected"]),
 ("TC-14", "Exception", "Invalid lifecycle transition, NEW directly to CLOSED",
  "An incident exists; for the unit level every pair of statuses is tried", "Request CLOSED from a new incident; and every disallowed pair of statuses at unit level",
  "HTTP 409 INVALID_STATE_TRANSITION and the incident does not change; every disallowed pair raises InvalidTransitionError",
  "HTTP 409, status and audit unchanged; all disallowed pairs were rejected",
  ["test_lifecycle.py::test_t08_new_to_closed_is_rejected_with_409_and_no_mutation", "test_lifecycle.py::test_every_disallowed_transition_is_rejected"]),
 ("TC-15", "Exception", "Assignment when no eligible technician exists",
  "Storage is covered only by a technician on leave", "Create a Cloud Storage incident in category Storage",
  "Incident stays CLASSIFIED and unassigned; administrators are notified; the timeline records NO_TECHNICIAN_AVAILABLE",
  "assigned false, status CLASSIFIED, administrator notification present, internal event hidden from the employee",
  ["test_assignment.py::test_t15_no_eligible_technician_leaves_incident_unassigned_and_notifies_admin"]),
 ("TC-16", "Exception", "Manual assignment to a technician at the workload limit",
  "Technician limit set to 1 and already holding one incident", "Administrator assigns a second incident to that technician, then repeats with override true",
  "Refused with HTTP 409 TECHNICIAN_WORKLOAD_EXCEEDED; with an explicit override accepted and audited",
  "First request HTTP 409 TECHNICIAN_WORKLOAD_EXCEEDED; with override HTTP 200 and the timeline text mentions the override",
  ["test_assignment.py::test_workload_limit_blocks_assignment_unless_admin_overrides"]),
 ("TC-17", "Exception", "Incident processing when the SLA policy is missing",
  "The only P1 SLA policy is deactivated", "Create a P1 incident",
  "HTTP 422 MISSING_SLA_CONFIGURATION and no incident is saved",
  "HTTP 422 with code MISSING_SLA_CONFIGURATION; incident list total 0",
  ["test_sla.py::test_missing_sla_policy_blocks_creation_without_side_effects"]),
 ("TC-18", "Authorisation", "Employee views another employee's incident",
  "Two employees; one has reported an incident", "Second employee requests the incident, its notes and its timeline",
  "HTTP 403 for all three and no incident content in the response",
  "HTTP 403 for incident, notes and timeline; the title was absent from the response",
  ["test_rbac.py::test_t04_employee_cannot_read_another_employees_incident"]),
 ("TC-19", "Authorisation", "Technician changes an incident not assigned to them",
  "Incident assigned to technician A; technician B signed in", "B requests the incident, patches its category and tries to acknowledge it",
  "HTTP 403 each time and the incident is unchanged",
  "HTTP 403 for all three requests; status still ASSIGNED; acknowledgement by B refused",
  ["test_documented_cases.py::test_tc19_technician_cannot_view_or_change_an_incident_not_assigned_to_them",
   "test_lifecycle.py::test_only_assigned_technician_or_admin_can_acknowledge"]),
 ("TC-20", "Authorisation", "Employee or technician uses administrator-only functions",
  "Employee, technician and administrator signed in", "GET users, audit logs, reports, SLA policies, settings, teams, e-mail outbox and SLA lists",
  "HTTP 403 for employee and technician, HTTP 200 for the administrator",
  "Nine administrator endpoints returned 403 to both non-admin roles and 200 to the administrator",
  ["test_rbac.py::test_admin_only_endpoints_reject_other_roles"]),
 ("TC-21", "Authorisation", "Unauthenticated access to protected endpoints",
  "No token", "GET /api/auth/me and /api/incidents without a token; with a malformed token; every probed use-case endpoint anonymously",
  "HTTP 401 in all cases",
  "HTTP 401 for both endpoints, for the malformed token and for every probed use-case endpoint",
  ["test_auth.py::test_protected_routes_require_a_valid_token", "test_use_case_matrix.py::test_anonymous_cannot_use_any_probed_endpoint"]),
 ("TC-22", "Business rule", "Priority equals impact x urgency x business criticality",
  "Default product strategy", "Ratings (4,5,5), (3,3,4), (3,3,2), (1,2,1)",
  "Scores 100, 36, 18 and 2 giving P1, P2, P3 and P4",
  "All documented examples matched, including 100 for P1 and the criticality taken from the service",
  ["test_priority.py::test_t05_impact4_urgency5_criticality5_is_score_100_p1", "test_priority.py::test_documented_examples_and_boundaries"]),
 ("TC-23", "Business rule", "Correct SLA response and resolution deadlines for each priority",
  "Standard SLA policies", "Create one incident per priority (P1 to P4) and read the SLA targets",
  "P1 5 and 30 min, P2 15 and 120, P3 60 and 480, P4 240 and 1440 minutes",
  "All four priorities reported exactly those target minutes",
  ["test_sla.py::test_all_priorities_use_the_specified_targets", "test_sla.py::test_t16_p1_incident_gets_5_and_30_minute_deadlines"]),
 ("TC-24", "Business rule", "An accepted lifecycle transition creates an audit record",
  "Incident taken to RESOLVED", "Read the incident timeline as administrator",
  "Audit rows with previous and new state for each step, in time order",
  "NEW to CLASSIFIED, CLASSIFIED to ASSIGNED, ASSIGNED to ACKNOWLEDGED, ACKNOWLEDGED to IN_PROGRESS and IN_PROGRESS to RESOLVED present, times ascending; actor, action and time present",
  ["test_lifecycle.py::test_every_accepted_transition_is_audited_with_states", "test_notifications_audit.py::test_t21_transition_creates_audit_row_with_actor_action_states_and_time"]),
 ("TC-25", "Business rule", "Creation and assignment trigger the right notifications",
  "Employee, technician and administrator accounts", "Create an incident and move it to RESOLVED; read each inbox and the e-mail outbox",
  "Reporter, technician and administrator receive their messages; each has an in-app record and a simulated e-mail record",
  "Reporter saw reported, classified and assigned messages; technician saw the assignment; administrator saw the report; outbox entries all EMAIL and SENT",
  ["test_notifications_audit.py::test_t20_creation_assignment_and_resolution_create_in_app_and_email_records"]),
 ("TC-26", "Business rule", "Duplicate detection warns but does not merge",
  "A payment incident is open", "Report two further, similarly worded payment incidents by other employees",
  "Warning lists the earlier incident(s) with similarity of at least 0.45; all incidents are still created and open",
  "Second report listed the first as a duplicate; third listed both; three separate open incidents; related incidents can be linked without merging",
  ["test_intelligence.py::test_t24_similar_payment_incident_triggers_a_warning_but_is_not_blocked",
   "test_intelligence.py::test_admin_can_link_related_incident_without_merging"]),
 ("TC-27", "Business rule", "Search and filtering return only matching incidents",
  "Four incidents with different priorities, services and SLA states", "Combine status, priority, service and SLA status filters; try the filters separately",
  "Only incidents that match every selected criterion are returned; contradictory combinations return none",
  "Each combination returned exactly the expected incident numbers and zero results for the contradictory combinations",
  ["test_search_reports.py::test_t23_combined_filters_return_only_matching_incidents", "test_search_reports.py::test_each_of_the_eight_filters_works_on_its_own"]),
]

# Manual and planned cases: fixed status, never counted as automated.
M = [
 ("TC-28", "Business rule", "Live priority preview on the report form",
  "Back end and front end running with demo data", "In the browser enter impact 2 and 300 affected users on the report form and submit",
  "Preview shows the raised priority and a note that impact was raised to 4; the created incident explains it",
  "Preview showed P1 (score 60) with the note that impact was raised to 4; the detail page showed the explanation; no JavaScript errors were logged",
  "Manual (scripted headless Chrome pass on 2026-11-14)", "PASS"),
 ("TC-29", "Exception", "Network failure shown as a readable message",
  "Page open in the browser; the front-end server stopped so that no response can arrive", "Click Sign in or any other action on the open page",
  "A message such as 'Cannot reach the server' in an alert or toast and no blank page. With only the back end stopped behind the Vite proxy the message is 'Request failed (500).'",
  "Not executed in this report", "Planned, not executed (checklist in MANUAL_TASKS.md)", "NOT EXECUTED"),
 ("TC-30", "Business rule", "Full test suite on Windows",
  "Windows computer with Python 3.11 or later and a virtual environment", "pip install -r requirements.txt, then python -m pytest -q in the backend folder",
  "All tests pass", "264 passed, 1 warning in 49.55 s in Windows PowerShell on 2026-11-20 (screenshot SS-31)",
  "Manual (Windows PowerShell, 2026-11-20)", "PASS"),
]


def collect():
    r = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider"],
                       cwd=BACKEND, capture_output=True, text=True)
    return [l.strip() for l in r.stdout.splitlines() if "::" in l]


def run(nodes):
    xml = DOCS / "evidence" / ".cases_junit.xml"
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", f"--junitxml={xml}", *nodes],
                       cwd=BACKEND, capture_output=True, text=True)
    root = ET.parse(xml).getroot()
    suite = root if root.tag == "testsuite" else root[0]
    out = {}
    for tc in suite.iter("testcase"):
        node = f"{tc.get('classname').replace('.', '/')}.py::{tc.get('name')}"
        failed = tc.find("failure") is not None or tc.find("error") is not None
        skipped = tc.find("skipped") is not None
        out[node] = "FAIL" if failed else ("SKIPPED" if skipped else "PASS")
    xml.unlink()
    return out, r.returncode


def status_for(tests, results):
    sts = []
    for t in tests:
        hits = [s for n, s in results.items() if n == T + t or n.startswith(T + t + "[")]
        sts += hits or ["MISSING"]
    if "FAIL" in sts or "MISSING" in sts:
        return "FAIL"
    return "PASS" if all(s == "PASS" for s in sts) else "NOT EXECUTED"


def esc(s):
    s = s.replace("|", "/")
    # long constant-style names (error codes, statuses with underscores) are set as code so they can wrap
    s = re.sub(r"\b([A-Z]{2,}(?:_[A-Z]+)+)\b", r"`\1`", s)
    return re.sub(r"(?<![\w`])(/api/[\w/{}\-]+)", r"`\1`", s)


def main():
    collected = collect()
    cset = set(collected)
    nodes = []
    for *_, tests in A:
        for t in tests:
            ok = any(c == T + t or c.startswith(T + t + "[") for c in cset)
            if not ok:
                sys.exit(f"Test reference does not exist: {t}")
            nodes.append(T + t)
    results, _ = run(sorted(set(nodes)))
    rows, trace, cats = [], [], {}
    final = []
    for tid, cat, scen, pre, inp, exp, act, tests in A:
        st = status_for(tests, results)
        final.append((tid, cat, scen, pre, inp, exp, act if st == "PASS" else "See pytest output: " + st, st))
        trace.append((tid, "Automated", "; ".join(f"`{t}`" for t in tests)))
    for tid, cat, scen, pre, inp, exp, act, typ, st in M:
        final.append((tid, cat, scen, pre, inp, exp, act, st))
        trace.append((tid, typ, "none" if st == "NOT EXECUTED" else "none (not part of the automated suite)"))
    for f in final:
        cats.setdefault(f[1], []).append(f[7])

    out = ["<!-- landscape -->",
           "**Table 6.4: Documented test cases with expected results, actual results, status and automated test reference**", "",
           "| Test ID | Category | Test scenario | Preconditions | Test input or steps | Expected result | Actual result | Status | Automated test reference |",
           "|----|------|-----------|----------|-------------|-----------|-------------|-----|---------------------|"]
    refs = {tid: ref for tid, typ, ref in trace}
    types = {tid: typ for tid, typ, ref in trace}
    for f in final:
        ref = refs[f[0]]
        lead = {"Automated": "Automated: ", }.get(types[f[0]], types[f[0]] + ": ")
        cell = (lead + ref) if types[f[0]] == "Automated" else (types[f[0]] + ". No automated test.")
        out.append("| " + " | ".join(esc(x) for x in f) + " | " + cell.replace("|", "/") + " |")
    out += ["<!-- /landscape -->", ""]
    n_auto = len(A)
    out += ["**Table 6.5: Coverage of the six required categories**", "",
            "| Category | Cases | Passed | Not executed |", "|-------------|------|------|------|"]
    order = ["Normal", "Boundary", "Invalid input", "Exception", "Authorisation", "Business rule"]
    for c in order:
        s_ = cats[c]
        out.append(f"| {c} | {len(s_)} | {s_.count('PASS')} | {s_.count('NOT EXECUTED')} |")
    allst = [f[7] for f in final]
    out.append(f"| **Total** | **{len(final)}** | **{allst.count('PASS')}** | **{allst.count('NOT EXECUTED')}** |")
    block = "\n".join(out)

    text = REPORT.read_text(encoding="utf-8")
    if "<!-- testcases:start -->" not in text or "<!-- testcases:end -->" not in text:
        sys.exit("markers not found in the report")
    new = re.sub(r"<!-- testcases:start -->.*?<!-- testcases:end -->",
                 lambda m: "<!-- testcases:start -->\n" + block + "\n<!-- testcases:end -->", text, flags=re.S)
    REPORT.write_text(new, encoding="utf-8")
    print(f"{n_auto} automated cases: " + ", ".join(f"{k}={allst.count(k)}" for k in sorted(set(allst))))
    bad = [f[0] for f in final if f[7] == "FAIL"]
    if bad:
        print("FAILED:", bad)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
