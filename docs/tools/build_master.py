"""Builds the single submission report docs/I-ITSM_PROJECT_REPORT.md (and its PDF).

    python docs/tools/build_master.py            # writes the Markdown and the PDF
    python docs/tools/build_master.py --md-only  # writes only the Markdown

The master report is assembled from two source documents so that nothing is written twice:

* docs/FINAL_PROJECT_REPORT.md       (problem analysis, design, OO design, implementation, results)
* docs/TECHNOLOGY_SELECTION_REPORT.md (technology selection, error handling, security, persistence, tests)

Sections are picked by number (see PLAN), renumbered, and every "Table x.y", "Figure x.y", "Section x.y"
and "Chapter n" reference inside them is rewritten. New text (cover, abstract, rubric map, stack internals,
screenshot evidence) is defined in this file. The repository and video links are read from
docs/report_links.txt (two lines: REPO_URL=... and VIDEO_URL=...).
"""
import re
import subprocess
import sys
from pathlib import Path

DOCS = Path(__file__).resolve().parents[1]
FINAL = (DOCS / "FINAL_PROJECT_REPORT.md").read_text(encoding="utf-8")
TECH = (DOCS / "TECHNOLOGY_SELECTION_REPORT.md").read_text(encoding="utf-8")
OUT_MD = DOCS / "I-ITSM_PROJECT_REPORT.md"
OUT_PDF = DOCS / "I-ITSM_PROJECT_REPORT.pdf"
LINKS = DOCS / "report_links.txt"


def read_links():
    vals = {"REPO_URL": "[GITHUB REPOSITORY URL]", "VIDEO_URL": "[VIDEO URL]"}
    if LINKS.exists():
        for ln in LINKS.read_text(encoding="utf-8").splitlines():
            if "=" in ln and not ln.startswith("#"):
                k, v = ln.split("=", 1)
                if v.strip():
                    vals[k.strip()] = v.strip()
    return vals


# --------------------------------------------------------------------------- parsing
def parse(text):
    """Returns {'ch': {n: {'title':..., 'sec': {'n.m': (title, [lines])}}}, 'app': {letter: (title, [lines])}}"""
    ch, app = {}, {}
    cur_kind, cur = None, None
    in_fence = False
    for ln in text.split("\n"):
        if ln.startswith("```"):
            in_fence = not in_fence
        if not in_fence:
            m = re.match(r"# Chapter (\d+): (.*)", ln)
            if m:
                n = int(m.group(1))
                ch[n] = {"title": m.group(2), "sec": {}}
                cur_kind, cur = "ch", n
                cur_sec = None
                continue
            m = re.match(r"# Appendix ([A-Z]): (.*)", ln)
            if m:
                app[m.group(1)] = (m.group(2), [])
                cur_kind, cur = "app", m.group(1)
                continue
            if re.match(r"# ", ln) and not ln.startswith("# Chapter"):
                cur_kind, cur = ("ref", None) if ln.strip() == "# References" else (None, None)
                continue
            m = re.match(r"## (\d+\.\d+) (.*)", ln)
            if m and cur_kind == "ch":
                ch[cur]["sec"][m.group(1)] = (m.group(2), [])
                cur_sec = m.group(1)
                continue
        if cur_kind == "ch" and cur_sec:
            ch[cur]["sec"][cur_sec][1].append(ln)
        elif cur_kind == "app":
            app[cur][1].append(ln)
    return {"ch": ch, "app": app}


SRC = {"F": parse(FINAL), "T": parse(TECH)}

# old chapter number -> new chapter number (for "Chapter n" references)
CHAPMAP = {
    "F": {1: 1, 2: 2, 3: 4, 4: 5, 5: 6, 6: 10, 7: 11, 8: 12},
    "T": {1: 1, 2: 3, 3: 7, 4: 8, 5: 9, 6: 10, 7: 11},
}
# dropped sections that may still be referred to: replace "Section x.y" by this chapter reference
FALLBACK = {
    ("F", "2.2"): 2, ("F", "2.3"): 2, ("F", "2.8"): 2, ("F", "1.2"): 1, ("F", "1.6"): 1, ("F", "1.7"): 1,
    ("F", "3.3"): 3, ("F", "3.4"): 9, ("F", "3.8"): 5, ("F", "3.9"): 4,
    ("F", "4.1"): 5, ("F", "4.12"): 5, ("F", "5.14"): 10,
    ("F", "6.1"): 10, ("F", "6.2"): 10, ("F", "6.3"): 10, ("F", "6.4"): 10, ("F", "6.5"): 10,
    ("F", "6.6"): 8, ("F", "6.7"): 10,
    ("T", "6.7"): 10, ("T", "2.8"): 3, ("T", "2.9"): 5, ("F", "4.11"): 7, ("F", "3.7"): 4, ("T", "1.2"): 1, ("T", "2.10"): 8, ("T", "2.11"): 3, ("T", "7.2"): 11, ("T", "7.3"): 12, ("T", "1.1"): 1,
}

# --------------------------------------------------------------------------- new text blocks
LINKS_V = read_links()

COVER = f"""<!-- cover -->
# Intelligent IT Service Management and Incident Resolution System (I-ITSM)

**Project report**

Course: CS F213 / MAC F212 Object Oriented Programming, Semester I, 2026-2027, BITS Pilani Hyderabad Campus

| | |
|---|---|
| Group number | 93 |
| Instructor in charge | Subhrakanta Panda |
| Date of submission | November 2026 |
| Source code repository | {LINKS_V["REPO_URL"]} |
| Demonstration video | {LINKS_V["VIDEO_URL"]} |

**Team members**

| Name | College ID |
|---|---|
| T Lakshanya | 2024B3A70338H |
| Shresta Namburi | 2024B4A70653H |
| Sai Keerthi Chitla | 2024B3A70597H |

<!-- /cover -->
"""

FRONT = """<!-- frontmatter -->
## Declaration and abstract

**Declaration.** We declare that this report describes the project we submitted, that the system was built with the help of AI tooling as the assignment permits, and that we have read the code and can explain it. Every figure, test result and screenshot in this report was produced from the delivered system.

**Abstract.**

Organisations depend on IT services such as payment systems, authentication, networks and storage. When one of them fails, the speed and quality of the response depend on how the incident is reported, prioritised, assigned, tracked and recorded. Done by e-mail and telephone, this produces delayed responses, inconsistent priorities, uneven workload, missed service level agreements (SLAs), duplicate work and no reliable history.

This report describes I-ITSM, an Intelligent IT Service Management and Incident Resolution System that manages the complete incident lifecycle (report, classify, prioritise, assign, investigate, resolve, verify, close). It is a web application built as a layered, contract-driven monolith: a React 18 single-page application, a FastAPI service on an ASGI server, SQLAlchemy 2 as the object-relational mapper and SQLite as the embedded relational store. The design is deliberately object oriented. The State pattern governs the lifecycle, the Strategy pattern makes the priority and assignment algorithms interchangeable, the Observer pattern decouples audit logging and notifications from the workflow, the Repository pattern isolates persistence, and a transactional unit of work makes every workflow atomic. Six intelligent features (category suggestion, duplicate detection, correlation of related incidents, suggested resolutions, technician recommendation and SLA risk assessment) are rule based and explain every decision. A background monitor tracks SLA deadlines, records violations and escalates unacknowledged critical incidents.

The system was verified with 264 automated tests (all passing, 94.8 percent statement coverage of the back end), thirty documented test cases in the six categories required by the brief, fifteen screenshots of the running system, a clean-install check, the front-end production build, and a program that checks the class, ER, architecture and use case diagrams against the source code. The report also states what was not tested, which security mechanisms are only recommended, and which scalability measures are proposals and not implementation.

<!-- /frontmatter -->
"""

RUBRIC = r"""The course brief evaluates the project on seven criteria worth 120 marks. Table 0.1 states where this report answers each of them, so that an evaluator can go straight to the evidence. The mapping is the team's own reading of the brief, not a self-assessment of marks.

**Table 0.1: The evaluation rubric of the brief and where this report addresses each criterion**

| Criterion (marks) | What the brief asks for | Where it is answered |
|---------------------|-------------------------------|------------------------------------------|
| System design and architecture (10) | Problem understanding and a clear development of the prototype | Chapter 2 (problem analysis, roles, requirements, business rules), Chapter 4 (architecture, use cases, class diagrams), Chapter 5 (object-oriented design), Chapter 9 (data model) |
| Functionality implementation (60) | Working implementation of the mandatory modules | Chapter 6 (every module with its code location), Chapter 11 (requirement-by-requirement compliance audit), Chapter 10 (test results and screenshots that show the modules working) |
| User experience (10) | Value-added features: SLA, security, new and intelligent features | Chapter 6 (role-specific interfaces, live priority preview, SLA countdowns, notifications), Chapter 8 (security), screenshots in Chapter 10 |
| Technical depth (15) | Code quality, use of APIs and third-party services, scalability of the design | Chapter 3 (technology selection, stack internals, scalability), Chapters 5, 7 and 8 (design patterns, exception handling, security) |
| Testing and validation (5) | Unit and integration tests, bug resolution, edge cases and exception handling | Chapter 7 (twelve error scenarios), Chapter 10 (264 automated tests, 30 documented cases, screenshots) |
| Innovation (10) | Capabilities beyond the basic requirements | Chapter 6, intelligent features: category suggestion, duplicate detection, correlation, suggested resolutions, technician recommendation, SLA risk assessment, automatic escalation |
| Documentation and presentation (10) | Completeness and clarity of the report and the recorded demo | This report, the README, the generated diagrams and data dictionary, and the demonstration video (link on the cover) |
"""

STACK = r"""This section describes how the selected technologies behave at run time. It complements the per-layer justifications of the other sections of this chapter and is the part of the report that explains *why the pieces compose*, not only *what each piece is*.

**Process and concurrency model.** The back end is a single operating-system process. Uvicorn runs an ASGI event loop; Starlette, the toolkit beneath FastAPI, performs routing and middleware composition (CORS, exception translation). Route handlers are declared as ordinary synchronous functions, so FastAPI dispatches each of them to a worker thread of the AnyIO thread pool. A blocking SQLAlchemy call therefore occupies one worker and never stalls the event loop, which keeps request handling responsive without the code having to be written in the `async` style. The SLA monitor is a second concurrency domain: a daemon `threading.Thread` started from the application's lifespan handler, woken every 60 seconds by a `threading.Event`, so that shutdown is prompt and deterministic. Request threads and the monitor thread therefore contend for one SQLite writer, a constraint that is named, analysed and used in the scalability argument of Section @@SCALE@@.

**Contract-first request pipeline.** Every inbound payload crosses a validation membrane before any business code runs. Pydantic v2 compiles each schema into a validator whose core is implemented in Rust (`pydantic-core`), so constraints such as `Field(min_length=5)` or `ge=1, le=5` are enforced with negligible cost and produce structured errors. FastAPI derives an OpenAPI 3.1 description from the same annotated signatures, which is why the interactive documentation at `/docs` is never out of date and why that page was used as a test client for the screenshots of Chapter 10. The resulting contract is symmetric: the type annotation is simultaneously the validation rule, the serialisation schema and the documentation.

**Inversion of control.** Dependencies are not constructed where they are used. `Depends` resolves a per-request chain (database session, service container, authenticated principal, role guard), and `build_container` wires repositories, services and observers into one object graph per session. This is constructor-style dependency injection achieved without a framework container, and it is the reason the same services can be exercised by a unit test, by the HTTP test client or by the live server without modification. Time itself is an injected dependency (`Clock`), which lets the tests move the SLA clock forward deterministically instead of sleeping.

**Persistence internals.** SQLAlchemy 2 supplies a typed declarative mapping (`Mapped[...]`), an identity map, change tracking and a unit of work that flushes pending changes in dependency order. The project adds a `@transactional` decorator so that a service method is an atomic boundary: the state change, the audit row and the notifications either all commit or all roll back. The engine runs on SQLite, an embedded, serverless, transactional SQL engine with a B-tree storage format, enforcing foreign keys because `PRAGMA foreign_keys=ON` is issued on every new connection through a connection event. A custom `UTCDateTime` column type normalises every timestamp to timezone-aware UTC on read, which removes a whole class of offset defects from the SLA arithmetic. The audit table is made append-only by ORM event listeners that veto updates and deletes.

**Event-driven decoupling.** The workflow does not know who reacts to it. Services publish immutable domain events on an in-process `EventBus`; the `AuditObserver` is registered as a critical subscriber, so its failure aborts the transaction and an unaudited change is impossible, while the `NotificationObserver` is non-critical, so a failed notification cannot undo a legitimate state change. Observers are therefore classified by the consistency guarantee they must give, which is a more precise statement than "the Observer pattern was used".

**Identity and credential handling.** Authentication is stateless. The server issues an HS256 JSON Web Token (an HMAC-SHA-256 signature over base64url-encoded header and claims) with a 60-minute lifetime, and every request is authorised by verifying the signature and re-loading the principal. Passwords are never stored: bcrypt, an adaptive hash based on the Blowfish key schedule, is applied with a per-password salt and a cost factor of 12, which means 2^12 key-expansion rounds per hash and makes offline guessing deliberately expensive. Authorisation is layered: a route-level role guard, a service-level ownership check, and a repository-level filter, so that no single missed check exposes data.

**Rendering and delivery on the client.** The interface is a React 18 single-page application mounted with the concurrent root API (`createRoot`) inside `StrictMode`, which deliberately double-invokes render and effect logic in development to expose impurities. React reconciles a virtual component tree against the DOM, so only the changed nodes are touched. Vite serves source files as native ES modules during development, pre-bundles third-party dependencies with esbuild and applies hot module replacement; the production build is a Rollup bundle with tree shaking, minification and content-hashed assets. React Router 6 performs client-side routing over the History API, and a Vite development proxy forwards `/api` to the back end, so the browser sees a single origin and no CORS pre-flight is needed in development. Axios interceptors form a cross-cutting layer: one attaches the bearer token to every request, the other converts every failure mode (validation error, authorisation failure, timeout, no response) into one human-readable message. Recharts renders the dashboards as SVG.

**Server-authoritative computation.** The priority preview, the category suggestion and the duplicate warnings that the employee sees while typing are computed by the server and merely displayed by the client, with the typing debounced to limit traffic. A business rule is therefore written once, in one language, behind one contract, so the number on the screen cannot disagree with the number that is stored.
"""

# Evidence blocks: (ss, title, supports, explanation)
EVIDENCE = [
    ("SS-01", "Administrator dashboard and role-specific navigation", "TC-01, TC-20",
     "A successful administrator login lands on the operations dashboard of Anita Rao. The tiles show 13 incidents, 5 open, 2 critical, 1 unassigned, 6 SLA violations, 1 at risk, a 1.7 hour average resolution and a 4.5 out of 5 feedback score, and the charts show incidents created against resolved and the split by priority. The sidebar lists the administration and governance pages (Users, Technicians and teams, Services, Categories, SLA policies, Settings, Audit log, E-mail outbox) that employees and technicians do not receive."),
    ("SS-04", "Rejected login with a generic message", "TC-10",
     "A technician account is entered with a wrong password. The server answers with one fixed message, *Incorrect e-mail address or password*, which does not reveal whether the e-mail address exists, so the login form cannot be used to enumerate accounts. No token is issued and the user stays on the login page."),
    ("SS-05", "Technician refused when reporting an incident", "TC-19, TC-20",
     "Technician Arjun Kapoor fills in the report form and submits it. The request is refused with the red message *Technicians cannot report incidents. Use an employee account.* The rule is enforced by the server (HTTP 403); the page only displays the answer. The priority preview on the right still works, because previewing creates nothing."),
    ("SS-06", "Employee refused another employee's incident", "TC-18",
     "Employee Rahul Verma opens the address of incident INC-1011, which belongs to somebody else. The ownership check in the service layer refuses the request and the page shows *You do not have access to this incident*, together with a Try again button. This is the second layer of the layered authorisation described in Chapter 8."),
    ("SS-07", "Report form with live category suggestion and duplicate detection", "TC-02, TC-22",
     "Employee Karan Malhotra types the title and description of a Wi-Fi problem. Before any service is chosen the server has already suggested the category **Network** with a 57 percent match and the matched keywords (network, wifi, router), and the duplicate panel warns that the open incident INC-1015 is 75 percent similar. The priority preview card waits with the text *Select a service to preview the priority*, because the score needs the criticality of the service (it is shown filled in SS-09)."),
    ("SS-09", "Priority preview and duplicate warning for a payment outage", "TC-02, TC-26",
     "For a payment incident with service Payment Gateway, impact 4 and urgency 5, the preview shows a score of **100**, priority **P1 (Critical)** and the formula 4 x 5 x 5 = 100. The category suggestion is Application (50 percent match). The yellow panel lists INC-1012 (68 percent similar) and INC-1010 (51 percent similar) with the shared terms. It only warns, and the employee may still submit, which is business rule BR-14."),
    ("SS-11", "Incident detail with priority, SLA deadlines and timeline", "TC-02, TC-23, TC-24",
     "The incident INC-1015 created for Campus Wi-Fi is classified as Network, scored 27 and given priority P2. The SLA card shows a response target of 15 minutes and a resolution target of 2 hours with their due times and both clocks on track. The timeline records, in order, creation, classification from keywords, the priority calculation with its formula, and the automatic assignment to Arjun Kapoor using the strategy *Skill then load (balanced)*."),
    ("SS-12", "Technician recommendations with reasons", "TC-04",
     "The administrator opens the same incident and sees the Reassign technician card. The strategy selector reads *Skill then load (balanced)* and the first candidate, Arjun Kapoor, has a score of 158 with its reasons listed: network skill proficiency 5 of 5, 8 years of experience, one earlier incident resolved on this service, skill and experience weighted higher for a critical priority, and workload 0 of 5. Three technicians are listed as not eligible, and the green toast confirms *Technician assigned*. The recommendation is explainable, not a black box."),
    ("SS-13", "No eligible technician", "TC-15, TC-16",
     "Incident INC-1009 (Cloud Storage, priority P3) has no technician who satisfies the skill, availability and workload rules. The assignment card shows the amber notice *No technician is eligible. Use an override below* and the count of five ineligible technicians, and the incident remains Classified and unassigned. The SLA card shows the response deadline already breached, and the insight panel rates the SLA risk as high. This is the exception path of the assignment algorithm, handled without an error."),
    ("SS-16", "Incident resolved with resolution details and escalation", "TC-05",
     "Technician Meera Joshi has resolved incident INC-1014. The page shows the mandatory resolution summary and root cause (*Payment service ran out of connections*), the resolver, and the SLA card with a breached response and a met resolution. A red banner states that the incident was escalated to level 1 because the response SLA was breached. The insight panel lists duplicate candidates and notes that four payment incidents were reported within 24 hours, which may be a single underlying outage."),
    ("SS-18", "Closed incident with feedback and complete timeline", "TC-05, TC-24",
     "The reporter, Rahul Verma, has verified and closed incident INC-1013. The page shows the resolution, the employee feedback of four stars with a comment, and the SLA card with both targets met. The timeline lists every step from creation through classification, priority calculation, assignment, acknowledgement, investigation, resolution, verification and closure to the feedback. Only the reporter sees the verify and close actions."),
    ("SS-20", "Audit log filtered by one incident", "TC-24",
     "The administrator filters the append-only audit log by INC-1010. Eleven entries appear, each with time, action, description, actor and the state change, covering creation, classification, priority calculation, automatic assignment, acknowledgement, the start of the investigation, the SLA warning at 83 percent of the allowed time, the SLA breach and the reassignment by the administrator. System actions are attributed to *System*. The page states that entries cannot be edited or deleted."),
    ("SS-26", "Illegal status change refused with HTTP 409", "TC-14",
     "In the interactive API documentation, a request to move incident INC-1012 from ACKNOWLEDGED directly to CLOSED is answered with 409 Conflict, the code `INVALID_STATE_TRANSITION` and the list of transitions that are allowed from that state (IN_PROGRESS and ASSIGNED). The State pattern, not the controller, decides which moves are legal, and the error has the same shape as every other error of the API."),
    ("SS-28", "Missing or invalid fields reported with HTTP 422", "TC-11",
     "A request that supplies a three-character title is rejected before any business code runs. The response is 422 with the code `VALIDATION_ERROR` and an `errors` array that names the field (`title`) and the rule (*String should have at least 5 characters*). The bearer token in the request was redacted from this screenshot for the report."),
    ("SS-31", "Full automated test run on Windows", "TC-30",
     "In Windows PowerShell, inside the project's virtual environment, `python -m pytest -q` finishes with **264 passed, 1 warning in 49.55 seconds**. The warning is a deprecation notice from a third-party test client and does not affect the result. The run above it shows the live server logging the 409 and 422 responses of the previous two screenshots, and the SLA monitor and the simulated e-mails firing as designed. This run is the evidence for TC-30 and confirms that the system installs and tests cleanly on the platform used for the demonstration."),
]


def evidence_block():
    out = ["The fifteen screenshots below were taken from the running system on 20 November 2026 by the team, with the demonstration data of Appendix A. Each one is tied to the documented test cases it supports. The accounts shown are the demonstration accounts and contain no personal data. Where a screenshot shows less than the test case needs, the text says so.", "",
           ]
    for i, (ss, title, sup, text) in enumerate(EVIDENCE, 1):
        out += [f"![Figure §0.{i}: **{ss}, {title}.** {text} *Supports {sup}.*](screenshots/evidence/{ss}.png){{width=64%}}", ""]
    return "\n".join(out)


# --------------------------------------------------------------------------- plan
# ('F'|'T', 'n.m') takes a source section, ('N', key) takes new text, ('NT', key, title) likewise with title
NEW = {"rubric": ("Evaluation rubric and where it is answered", RUBRIC),
       "stack": ("The technology stack in depth: runtime, contract, persistence and rendering internals", STACK)}

PLAN = [
    ("Introduction", [("F", "1.1"), ("F", "1.3"), ("F", "1.4"), ("F", "1.5"), ("N", "rubric")]),
    ("Problem Analysis and Requirements", [("F", "2.1"), ("F", "2.4"), ("F", "2.5"), ("F", "2.6"), ("F", "2.7")]),
    ("Technology Selection and Justification", [("T", "7.1"), ("T", "2.1"), ("N", "stack"), ("T", "2.2"), ("T", "2.3"), ("T", "2.4"),
                                                ("T", "2.5"), ("T", "2.6"), ("T", "2.7"), ("T", "2.12")]),
    ("System Design and Architecture", [("F", "3.1"), ("F", "3.5"), ("F", "3.6")]),
    ("Object-Oriented Design", [("F", f"4.{i}") for i in range(2, 12)]),
    ("Implementation", [("F", f"5.{i}") for i in range(1, 14)]),
    ("Exception and Error Handling", [("T", f"3.{i}") for i in range(1, 6)]),
    ("Security Analysis", [("T", f"4.{i}") for i in range(1, 8)]),
    ("Persistence and Database Design", [("T", f"5.{i}") for i in range(1, 8)]),
    ("Testing and Validation", [("T", f"6.{i}") for i in range(1, 7)] + [("EV", "evidence")]),
    ("Results, Discussion and Requirement Compliance", [("F", "7.1"), ("F", "7.2"), ("F", "7.3"), ("F", "7.4")]),
    ("Conclusion and Future Scope", [("F", "8.1"), ("F", "8.2"), ("F", "8.3")]),
]
EXTRA_TITLES = {("T", "7.1"): "Where the nine technology questions are answered", ("N", "stack"): NEW["stack"][0],
                ("EV", "evidence"): "Screenshot evidence from the running system"}

DROP_FIGS = {("F", x) for x in ["3.2", "3.4", "3.5", "3.6", "5.1", "5.2", "5.3", "5.4", "5.5", "5.7", "5.8", "5.9", "5.14", "5.15"]}
# a reference to a dropped figure or table is redirected to the one that now carries the same content
ALIAS_FIG = {("F", "3.1"): ("T", "2.1"), ("F", "3.2"): ("T", "5.1"), ("F", "3.4"): ("F", "3.3"), ("F", "3.5"): ("F", "3.3"), ("F", "3.6"): ("F", "3.3"),
             ("F", "5.1"): ("EV", "0.2"), ("F", "5.2"): ("EV", "0.5"), ("F", "5.5"): ("EV", "0.7"), ("F", "5.7"): ("EV", "0.10"),
             ("F", "5.8"): ("EV", "0.1"), ("F", "5.9"): ("EV", "0.8")}
ALIAS_TAB = {("F", "3.2"): ("T", "2.2"), ("F", "6.4"): ("T", "6.4")}
PATCH_T = [
    (" (scenario T28 of Appendix A in the main report)", ""),
    ("The suite was written against the numbered acceptance scenarios T01 to T30 of the main report (Appendix A there).", "The suite was written against thirty numbered acceptance scenarios (T01 to T30), whose numbers appear in the test function names."),
    ("documents thirty cases, ten columns each.", "documents thirty cases in twelve columns: the ten required ones (test ID, category, scenario, objective, preconditions, steps, input data, expected result, actual result, status) plus the type of test and the pytest functions that implement the case."),
    ("| 7. Advantages and limitations of the stack | Section 2.8, Table 2.4 |", "| 7. Advantages and limitations of the stack | The Advantages and Limitations paragraphs of Sections 2.2 to 2.6, Table 2.2 |"),
    ("| 8. How does the technology support object-oriented design? | Section 2.9, Table 2.5 |", "| 8. How does the technology support object-oriented design? | Section 2.6, Table 2.1 and the object-oriented design chapter |"),
]
PATCH_F = [
    ("| Source code | Complete | `backend/`, `frontend/` | Repository link still has to be added by the team |", "| Source code | Complete | `backend/`, `frontend/` | Repository link on the cover page |"),
    ("| **Not done, team task** | The three workflows are described in `docs/MANUAL_TASKS.md` and each is supported by the screenshots and tests | The video must be recorded by the team with all members |", "| Recorded by the team, link on the cover page | The three workflows are supported by the screenshots and tests of the Testing chapter | None |"),
    (" (the team may adjust this list to reflect its own experience)", ""),
    ("Appendices B and C", "Appendix A"),
    ("The class diagrams are split into seven views", "The class diagrams are split into six views"),
    ("| 7 | Exceptions and the clock abstraction | Figure 4.5 |\n", ""),
    ("**Custom exceptions.** Figure 4.5 shows the exception tree and the clock abstraction.", "**Custom exceptions.** The exception tree and the clock abstraction are summarised below."),
    ("Complete (seven views) | Figures 3.7, 3.8, 4.1 to 4.5 |", "Complete (six views) | Figures 3.7, 3.8, 4.1 to 4.4 |"),
    ("![Figure 4.5: Class diagram of the exception hierarchy and the Clock abstraction.](diagrams/class_7_exceptions_and_clock.png){width=100%}", ""),
    ("The employee's dashboard (Figure 5.3) shows", "The employee's dashboard shows"),
    ("The list (Figure 5.4) supports", "The list supports"),
    ("Figure 5.8 shows the administrator's dashboard, Figure 5.10 the full incident list and Figure 5.15 the user management page.",
     "Figure 5.8 shows the administrator's dashboard and Figure 5.10 the full incident list."),
]
CAP_T = re.compile(r"^\*\*Table ([0-9A-Z]+\.\d+): (.*)\*\*\s*$")
CAP_F = re.compile(r"^!\[Figure ([0-9A-Z]+\.\d+): (.*?)\]\((.*?)\)(\{.*?\})?\s*$")
CAP_T2 = re.compile(r"^\*\*Table §([0-9A-Z]+\.\d+): (.*)\*\*\s*$")
CAP_F2 = re.compile(r"^!\[Figure §([0-9A-Z]+\.\d+): (.*?)\]\((.*?)\)(\{.*?\})?\s*$")


def main():
    # ---- pass 1: choose sections, renumber captions and headings
    body = []              # list of (src, [lines])
    secmap = {"F": {}, "T": {}, "N": {}}
    tabmap = {"F": {}, "T": {}, "N": {}, "EV": {}}
    figmap = {"F": {}, "T": {}, "N": {}, "EV": {}}
    for n, (title, items) in enumerate(PLAN, 1):
        tc = fc = 0
        body.append(("-", [f"# Chapter {n}: {title}", ""]))
        ch_idx = len(body) - 1
        for k, item in enumerate(items, 1):
            src, key = item[0], item[1]
            if src in ("F", "T"):
                stitle, lines = SRC[src]["ch"][int(key.split(".")[0])]["sec"][key]
                if src in ("F", "T"):
                    joined = "\n".join(lines)
                    for a_, b_ in (PATCH_F if src == "F" else PATCH_T):
                        joined = joined.replace(a_, b_)
                    if src == "F" and key == "4.11":
                        joined = joined.replace("<!-- landscape -->\n\n<!-- /landscape -->", "")
                    if src == "F" and key == "4.9":
                        joined = joined.replace("![Figure 4.3: Class diagram of the Repository pattern.](diagrams/class_4_repository_pattern.png){width=100%}", "")
                        joined = joined.replace("<!-- landscape -->\n\n<!-- /landscape -->", "")
                    if src == "F" and key == "3.6":
                        fig = "![Figure 4.3: Class diagram of the Repository pattern.](diagrams/class_4_repository_pattern.png){width=100%}"
                        k_ = joined.rindex("<!-- /landscape -->")
                        joined = joined[:k_] + fig + "\n" + joined[k_:]
                    lines = joined.split("\n")
                stitle = EXTRA_TITLES.get((src, key), stitle)
                secmap[src][key] = f"{n}.{k}"
            elif src == "N":
                stitle, text = NEW[key]
                stitle = EXTRA_TITLES.get((src, key), stitle)
                lines = text.split("\n")
                src = "N"
            else:  # EV
                stitle = EXTRA_TITLES[(src, key)]
                lines = evidence_block().split("\n")
            new = [f"## {n}.{k} {stitle}", ""]
            if True:
                # a short lead-in followed by a landscape block: start the landscape page at the heading
                words_before = 0
                for i, x in enumerate(lines):
                    if x.strip().startswith("<!-- landscape"):
                        if words_before < 60 and not any(y.strip().startswith(("|", "![")) for y in lines[:i]):
                            marker = x.strip()
                            lines = lines[:i] + lines[i + 1:]
                            new = [marker, f"## {n}.{k} {stitle}", ""]
                            if k == 1:
                                body.insert(ch_idx, ("-", [marker]))
                                new = [f"## {n}.{k} {stitle}", ""]
                        break
                    words_before += len(x.split())
            for ln in lines:
                m = CAP_T.match(ln) or CAP_T2.match(ln)
                if m:
                    tc += 1
                    tabmap[src][m.group(1)] = f"{n}.{tc}"
                    ln = f"**Table §{n}.{tc}: {m.group(2)}**"
                else:
                    m = CAP_F.match(ln) or CAP_F2.match(ln)
                    if m and (src, m.group(1)) in DROP_FIGS:
                        continue
                    if m:
                        fc += 1
                        figmap[src][m.group(1)] = f"{n}.{fc}"
                        attr = m.group(4) or ""
                        if src == "F" and m.group(3).startswith("screenshots/"):
                            attr = "{width=62%}"
                        ln = f"![Figure §{n}.{fc}: {m.group(2)}]({m.group(3)}){attr}"
                new.append(ln)
            body.append((src, new))
    # ---- pass 2: references
    for (a_src, a_lab), (b_src, b_lab) in ALIAS_FIG.items():
        if a_lab not in figmap[a_src] and b_lab in figmap[b_src]:
            figmap[a_src][a_lab] = figmap[b_src][b_lab]
    for (a_src, a_lab), (b_src, b_lab) in ALIAS_TAB.items():
        if a_lab not in tabmap[a_src] and b_lab in tabmap[b_src]:
            tabmap[a_src][a_lab] = tabmap[b_src][b_lab]
    unresolved = set()

    def remap_list(kind, mapping, src):
        pat = re.compile(rf"\b({kind}s?)(\s+)(\d+\.\d+)((?:(?:,|\s+and|\s+to|\s+or)\s+\d+\.\d+)*)")

        def one(num):
            return mapping[src].get(num)

        def sub(m):
            nums = [m.group(3)] + re.findall(r"\d+\.\d+", m.group(4))
            seps = re.findall(r"(,|\s+and|\s+to|\s+or)\s+\d+\.\d+", m.group(4))
            new = []
            for x in nums:
                r = one(x)
                if r is None:
                    unresolved.add((src, kind, x))
                    r = x
                new.append(r)
            s = m.group(1) + m.group(2) + new[0]
            for sep, r in zip(seps, new[1:]):
                s += sep + " " + r
            return s
        return pat, sub

    final_lines = []
    for src, lines in body:
        if src == "-":
            final_lines += lines
            continue
        text = "\n".join(lines)
        # protect the new captions (they carry the section sign), remap references elsewhere
        out = []
        for ln in text.split("\n"):
            if ln.startswith("**Table §") or ln.startswith("![Figure §"):
                out.append(ln)
                continue
            if src in ("F", "T", "N", "EV"):
                s_src = "N" if src in ("N", "EV") else src
                for kind, mp in (("Table", tabmap), ("Figure", figmap)):
                    pat, sub = remap_list(kind, mp, s_src if src not in ("EV",) else "EV")
                    ln = pat.sub(sub, ln)
                if src in ("F", "T"):
                    def secsub(m):
                        nums = [m.group(3)] + re.findall(r"\d+\.\d+", m.group(4))
                        seps = re.findall(r"(,|\s+and|\s+to|\s+or)\s+\d+\.\d+", m.group(4))
                        new, whole = [], None
                        for x in nums:
                            if x in secmap[src]:
                                new.append(secmap[src][x])
                            elif (src, x) in FALLBACK:
                                whole = FALLBACK[(src, x)]
                                new.append(None)
                            else:
                                unresolved.add((src, "Section", x))
                                new.append(x)
                        if whole is not None and len(nums) == 1:
                            return f"Chapter {whole}"
                        s = m.group(1) + m.group(2) + (new[0] or nums[0])
                        for sep, r, o in zip(seps, new[1:], nums[1:]):
                            s += sep + " " + (r or o)
                        return s
                    ln = re.sub(r"\b(Sections?)(\s+)(\d+\.\d+)((?:(?:,|\s+and|\s+to|\s+or)\s+\d+\.\d+)*)", secsub, ln)
                    ln = re.sub(r"\bChapter (\d+)\b", lambda m: f"Chapter {CHAPMAP[src].get(int(m.group(1)), int(m.group(1)))}", ln)
            out.append(ln)
        final_lines += out + [""]
    md = "\n".join(final_lines).replace("§", "").replace("@@SCALE@@", secmap["T"]["2.12"])

    # ---- references and appendices
    refs = ["# References", "",
            "The libraries, standards and documents below were used. Versions are those resolved in the fresh-install check of 19 November 2026 or declared in the project files.", ""]
    ref_items = [
        "FastAPI documentation, https://fastapi.tiangolo.com (0.165.0 in the fresh install), and Starlette, https://www.starlette.io.",
        "Uvicorn, an ASGI server, https://www.uvicorn.org (0.54.0).",
        "SQLAlchemy 2.0 documentation, https://docs.sqlalchemy.org/en/20/ (2.1.9 in the fresh install).",
        "Pydantic and pydantic-settings, https://docs.pydantic.dev (2.14.4).",
        "PyJWT, https://pyjwt.readthedocs.io (2.15.1), and bcrypt, https://pypi.org/project/bcrypt (5.0.0).",
        "SQLite documentation, \"Appropriate uses for SQLite\" and \"File locking and concurrency\", https://sqlite.org/whentouse.html and https://sqlite.org/lockingv3.html.",
        "React 18.3, https://react.dev; React Router 6.28, https://reactrouter.com; Axios 1.7, https://axios-http.com; Recharts 2.13, https://recharts.org; lucide-react, https://lucide.dev.",
        "Vite 5.4 documentation, https://vite.dev.",
        "pytest, httpx and pytest-cov, https://docs.pytest.org (pytest 9.2.0, httpx 0.28.1).",
        "M. Jones, J. Bradley, N. Sakimura, \"JSON Web Token (JWT)\", RFC 7519, https://datatracker.ietf.org/doc/html/rfc7519.",
        "N. Provos, D. Mazieres, \"A Future-Adaptable Password Scheme\", USENIX Annual Technical Conference, 1999 (the bcrypt design).",
        "OWASP Top Ten, https://owasp.org/www-project-top-ten/.",
        "E. Gamma, R. Helm, R. Johnson, J. Vlissides, *Design Patterns: Elements of Reusable Object-Oriented Software*, Addison-Wesley, 1994 (Strategy, Observer, State, Factory, Template Method).",
        "M. Fowler, *Patterns of Enterprise Application Architecture*, Addison-Wesley, 2002 (Repository, Unit of Work).",
        "Graphviz, https://graphviz.org, and Mermaid with Mermaid CLI, https://mermaid.js.org (diagram rendering); Pandoc and XeLaTeX (this report).",
        "Course project brief, *Intelligent IT Service Management and Incident Resolution System (I-ITSM)*, CS F213 and MAC F212 Object Oriented Programming, Semester I, 2026-2027, BITS Pilani.",
    ]
    refs += [f"{i}. {t}" for i, t in enumerate(ref_items, 1)]
    appx = ["# Appendix A: Data dictionary, demonstration data and reproduction steps", ""]
    for letter, sletter, title in [("A", "B", "Data dictionary"), ("A", "C", "Demonstration data and accounts"), ("A", "D", "How to reproduce the results")]:
        lines = SRC["F"]["app"][sletter][1]
        appx += [f"## {title}", ""] + lines + [""]
    appendix_md = "\n".join(appx)
    appendix_md = appendix_md.replace("python docs/tools/build_report.py\n", "python docs/tools/build_tech_report.py\npython docs/tools/build_master.py\n")
    for sletter, off in (("B", 0), ("C", 1)):
        appendix_md = re.sub(rf"\b(Table|Figure) {sletter}\.(\d+)", lambda m, o=off: f"{m.group(1)} A.{int(m.group(2)) + o}", appendix_md)
        appendix_md = re.sub(rf"\*\*Table {sletter}\.(\d+):", lambda m, o=off: f"**Table A.{int(m.group(1)) + o}:", appendix_md)
    md = md + "\n" + "\n".join(refs) + "\n\n" + appendix_md

    md = md.replace("and the object-oriented design chapter", "and Chapter 5")
    md = COVER + "\n" + FRONT + "\n" + md
    OUT_MD.write_text(md, encoding="utf-8")
    have_sec = set(re.findall(r"^## (\d+\.\d+) ", md, re.M))
    have_tab = set(re.findall(r"^\*\*Table ([0-9A-Z]+\.\d+):", md, re.M))
    have_fig = set(re.findall(r"^!\[Figure ([0-9A-Z]+\.\d+):", md, re.M))
    stale = []
    for i, ln in enumerate(md.split("\n"), 1):
        if ln.startswith("**Table ") or ln.startswith("!["):
            continue
        for kind, have in (("Section", have_sec), ("Table", have_tab), ("Figure", have_fig)):
            for m in re.finditer(rf"\b{kind}s?\s+(\d+\.\d+)((?:(?:,|\s+and|\s+to|\s+or)\s+\d+\.\d+)*)", ln):
                for x in [m.group(1)] + re.findall(r"\d+\.\d+", m.group(2)):
                    if x not in have:
                        stale.append((i, kind, x, ln[max(0, m.start() - 50):m.end() + 40]))
    for item in stale:
        print("STALE", item)
    if unresolved:
        print("UNRESOLVED references:", sorted(unresolved))
    print(f"Wrote {OUT_MD} ({len(md.split())} words)")
    if "--md-only" in sys.argv:
        return 0
    import os
    env = dict(os.environ, REPORT_LISTS="0", REPORT_FONT="10pt", REPORT_MARGIN="2.0cm", REPORT_STRETCH="1.05")
    r = subprocess.run([sys.executable, str(DOCS / "tools" / "build_report.py"), str(OUT_MD), str(OUT_PDF),
                        "I-ITSM project report, group 93", "Project report"], capture_output=True, text=True, env=env)
    print(r.stdout[-1500:], r.stderr[-2500:])
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
