# Problem analysis

## 1. The problem

Organisations depend on IT services such as e-mail, payment systems, networks and printers. When one of them fails, employees report it by phone, chat or e-mail. In an unmanaged service desk this causes predictable trouble:

* Reports are incomplete, scattered over several channels, and nobody owns them.
* Urgency is judged by whoever happens to read the message, so a printer jam can be handled before a payment outage.
* Work is given to whoever is nearest, not to the person with the right skill and spare capacity.
* Nobody notices that a deadline is about to be missed until the user complains.
* The same fault is reported many times and investigated many times.
* There is no trustworthy record of who did what and when, so nothing can be learned or audited.

I-ITSM (Intelligent IT Service Management) replaces that with one controlled workflow: report, classify, prioritise, assign, investigate, resolve, verify, close, with every step recorded.

## 2. Stakeholders

| Stakeholder | Interest | How the system serves them |
|---|---|---|
| Employee (reporter) | Gets the problem fixed quickly and knows the status | Simple report form, live priority preview, duplicate warning, timeline, notifications, verify or reopen, feedback |
| Technician | Clear, fair workload that matches skills | Personal queue, availability switch, only incidents they can handle are assigned, notes, information requests, resolution form |
| Administrator (service desk manager) | Control, visibility, SLA compliance | Assignment with ranked recommendations and override, dashboards and reports, SLA monitor, configuration, audit log |
| Management and auditors | Evidence and trends | Append-only audit log, reports by service and category, SLA compliance figures |
| Business owners of services | Critical services are restored first | Business criticality per service feeds the priority score |
| Developers and maintainers (the student group, later maintainers) | Code that can be extended safely | Layered design, documented patterns, tests, generated and verified diagrams |

## 3. Existing challenges and how each is addressed

| Challenge in a manual process | Consequence | Design response |
|---|---|---|
| Inconsistent urgency judgement | Wrong order of work | Priority score = impact x urgency x business criticality, P1 to P4 bands (BR-01, BR-02). Number of affected users raises the counted impact when large (BR-16) |
| Wrong person assigned | Slow or failed resolution | Eligibility policy (active, available, has the category skill, under workload limit) and three ranking strategies chosen by the admin; an override is possible but audited |
| Missed deadlines | Unhappy users, contractual penalties | SLA policy per priority or service, deadlines at creation, warning at 75 percent, one violation per type, escalation of unacknowledged P1 and P2 through three levels |
| Duplicate reports | Wasted effort | Similarity check warns while the employee types (never blocks); related-incident correlation for admins |
| Wrong category | Wrong team, wrong statistics | Rule-based category suggestion from admin-editable keywords, with a visible reason |
| Missing history | No accountability | Append-only audit log of every state change and override, with actor, time, previous and new state |
| No feedback loop | No quality measure | Employee rating after resolution; reports by service, category and technician |
| Illegal shortcuts | Incidents closed without a fix | State machine allows only defined transitions, requires resolution summary and root cause, requires a reason to reopen |
| Information stuck in people's heads | Resolutions not reused | Suggested resolutions from similar resolved incidents |

## 4. Proposed solution

A three-tier web application.

* **Frontend:** React single page application. Each role sees its own dashboard and only the actions it may perform.
* **Backend:** FastAPI REST API, thin routes, a service layer for business workflows, and a domain layer holding the lifecycle, events and exceptions. Each request gets its own dependency-injection container and one database transaction.
* **Persistence:** SQLAlchemy with SQLite (15 tables), repositories hide all SQL.
* **Object-oriented design:** Strategy (priority, assignment), State (lifecycle), Observer (audit, notifications), Repository, Factory, dependency injection and unit of work. See `ARCHITECTURE.md` and the class diagrams in `diagrams/`.
* **Intelligence without external services:** all four features (category suggestion, duplicate detection, technician recommendation, SLA risk) are rule based and explain themselves, so an administrator can see and change why the system decided something.
* **Background monitoring:** a monitor thread checks SLA deadlines every 60 seconds.

### Scope

In scope: everything in the assignment's functional list (see `REQUIREMENTS_SPECIFICATION.md`). Out of scope: real e-mail or SMS delivery (simulated), multi-organisation tenancy, machine-learning models, mobile apps, integration with monitoring tools, attachment uploads, password reset by e-mail, login lockout and rate limiting.

## 5. Assumptions

1. One organisation, one service desk, one time zone for display. All stored times are UTC.
2. Every employee, technician and administrator has an account created by an administrator or by self-registration (self-registration always creates an employee).
3. SLA targets are measured in calendar minutes, not working hours, and the clock does not pause when information is requested from the reporter (DESIGN_NOTES item 7).
4. An incident has exactly one category, one service and at most one assigned technician at a time.
5. Impact and urgency are chosen by the reporter on a 1 to 5 scale. Business criticality comes from the service and may be overridden by an administrator only.
6. "Critical" on dashboards means an open P1 incident.
7. A technician belongs to at most one team and has a personal workload limit (default 5 active incidents).
8. SQLite and one server process are enough for the intended load. The upgrade path is PostgreSQL and a process manager (see the technology selection report).
9. The system runs inside the organisation's network or on a developer's machine. It is not exposed to the public internet in this submission.
10. Users have a modern browser (Chromium based browsers were tested).
11. The affected-user thresholds (10, 50, 250, 1000) are reasonable defaults for a mid-sized organisation. They are constants in code and the rule can be switched off in Settings.
12. E-mail is simulated: messages are stored in the outbox and logged.

## 6. Risks and limitations

| Risk or limitation | Mitigation or status |
|---|---|
| Single SQLite file, no concurrent write scaling | Acceptable for the assignment, documented upgrade path |
| No login lockout or rate limiting | Not implemented, listed as a gap |
| Passwords only use the first 72 bytes (bcrypt) | Explicit truncation, documented; limit of 128 characters is enforced by validation |
| No automated UI tests | Manual test script in `MANUAL_TASKS.md`; scripted walkthrough performed |
| Frontend development dependencies have known advisories (Vite, esbuild, react-router) | Listed in `TESTING_REPORT.md` section 6; major upgrades deferred because the stack is fixed |
| Rule-based intelligence is less flexible than a trained model | Chosen for explainability and for running with no external service |
