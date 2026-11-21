# Requirements specification

Version 1.0. Every functional requirement and business rule has an identifier that is used in `REQUIREMENTS_TRACEABILITY.md`, which names the code, the tests and the user interface that satisfy it. Use cases UC01 to UC32 refer to the diagrams in `diagrams/use_case_*.png`.

## 1. Purpose and scope

I-ITSM manages IT incidents from report to closure: classification, prioritisation, assignment, SLA tracking, notification, search, reporting and audit. It is a web application with a REST API backend and a single page frontend.

## 2. User roles (actors)

| Role | Who | Can do | Cannot do |
|---|---|---|---|
| **Employee** | Any staff member who reports problems | Sign in, report incidents (UC04), preview priority, see duplicates, follow own incidents, add replies, verify, reopen or close own resolved incidents, give feedback on own incidents, read notifications, edit own profile | See other employees' incidents or internal notes, assign, resolve, configure |
| **Technician** | Support engineer | Everything a signed-in user can do, plus see and work incidents assigned to them: acknowledge, investigate, add notes (including internal), request information, resolve with summary and root cause, set own availability, see own queue and the workload overview | Report incidents, assign or reassign, change priority fields, administer, verify or close incidents |
| **Administrator** | Service desk manager | Everything: assign and reassign (with audited override), view recommendations, override priority fields, manage users, technician skills, teams, categories, services, SLA policies and strategies, view reports, SLA monitor, audit log and e-mail outbox. May also act in any lifecycle step | Edit or delete audit records (nobody can) |
| **SLA monitor** (system actor) | Background timer | Check deadlines, warn, record violations, escalate, classify and auto-assign new incidents, write audit entries, send notifications | n/a |

The permissions in the use case diagram are enforced by tests: `backend/tests/test_use_case_matrix.py` calls the real API as each role and checks that exactly the listed actors are allowed.

## 3. Functional requirements

| ID | Requirement |
|---|---|
| FR-01 | A person can register (always as employee) and sign in with e-mail and password. Three roles exist. Deactivated accounts cannot sign in or use an old token |
| FR-02 | An administrator can create, edit and deactivate users, set role, department, technician profile (team, skills with proficiency, experience, workload limit). A technician with active incidents cannot be deactivated |
| FR-03 | An employee can report an incident with title (5 to 200 characters), description (10 to 5000), service, impact 1 to 5, urgency 1 to 5, optional affected system, optional number of affected users (0 to 1,000,000) and optional category. The incident gets a unique number (`INC-1001` upward) |
| FR-04 | The system suggests a category from keywords and shows why. Administrators maintain categories and keywords |
| FR-05 | The system calculates the priority score and level P1 to P4 (rules BR-01, BR-02, BR-16) and shows a preview before submission |
| FR-06 | The system selects an SLA policy (service specific first, then standard for the priority) and sets response and resolution deadlines |
| FR-07 | The system assigns automatically with a configurable strategy (skill based, load based, skill then load) when a technician is eligible, otherwise leaves the incident unassigned and notifies administrators. An administrator can assign or reassign manually, with an explicit audited override for ineligible technicians |
| FR-08 | The lifecycle NEW, CLASSIFIED, ASSIGNED, ACKNOWLEDGED, IN_PROGRESS, RESOLVED, VERIFIED, CLOSED is enforced. Illegal transitions are rejected and change nothing. Each transition names who may perform it |
| FR-09 | The assigned technician can acknowledge, start investigation, add notes, request information from the reporter and resolve with summary and root cause |
| FR-10 | The reporter can follow status and timeline, reply to information requests, verify or reopen (with reason) a resolved incident, close a verified one, and rate the resolution once |
| FR-11 | An SLA monitor evaluates all open incidents every 60 seconds (and on demand by an administrator): warning at 75 percent of an interval, one violation per incident per type, escalation of unacknowledged P1 and P2 incidents |
| FR-12 | Notifications are produced for relevant events as in-app messages and simulated e-mail. An administrator can read the e-mail outbox |
| FR-13 | Every state change, assignment, override, priority change and configuration change is written to an append-only audit log with actor, action, previous and new state and time. Administrators can filter it |
| FR-14 | Users can search incidents by free text, number, date range, status, priority, category, service, technician, SLA status, unassigned and awaiting information. Employees see only their own incidents |
| FR-15 | Each role has a dashboard. Administrators have reports: overview, by service, by category, technician workload, trends and category by service matrix |
| FR-16 | Four intelligent features: category suggestion, duplicate detection, technician recommendation with reasons, SLA risk assessment. Also correlation of related open incidents and suggested resolutions |
| FR-17 | Administrators configure categories, services (with business criticality), SLA policies, teams and global settings (strategies, duplicate threshold, auto-assignment, escalation, default workload limit, affected-users rule) without restarting |
| FR-18 | Data is stored persistently and survives a restart |
| FR-19 | Users can edit their own profile and change their password (current password required) |

## 4. Business rules

| ID | Rule |
|---|---|
| BR-01 | Priority score = impact x urgency x business criticality, each from 1 to 5 |
| BR-02 | P1 is 40 to 125, P2 20 to 39, P3 8 to 19, P4 1 to 7 |
| BR-03 | Business criticality defaults from the service. Only an administrator may override it |
| BR-04 | Standard SLA targets (response / resolution): P1 5 min / 30 min, P2 15 min / 2 h, P3 1 h / 8 h, P4 4 h / 24 h |
| BR-05 | Deadlines are creation time plus the target in calendar minutes |
| BR-06 | The response clock stops at acknowledgement, the resolution clock when the incident becomes RESOLVED |
| BR-07 | A warning is raised once when 75 percent of an interval has elapsed (configurable per policy) |
| BR-08 | At most one violation is recorded per incident and SLA type |
| BR-09 | A technician's active workload counts incidents in ASSIGNED, ACKNOWLEDGED and IN_PROGRESS. The default limit is 5 |
| BR-10 | A technician is eligible only if active, available, holding the category skill and below the workload limit |
| BR-11 | The system never silently assigns a technician without the required skill. An administrator may override, and the override is audited |
| BR-12 | Only transitions defined by the lifecycle are allowed, and every accepted transition is audited |
| BR-13 | Resolving requires a resolution summary and a root cause. Reopening requires a reason |
| BR-14 | Duplicate detection only warns. It never blocks, merges or closes |
| BR-15 | Audit records are append-only |
| BR-16 | If the number of affected users is 10 or more, the counted impact is at least 2; 50 or more, 3; 250 or more, 4; 1000 or more, 5. The counted impact is the larger of the reporter's value and this floor, so it is never lowered. The reporter's value and the counted value are both stored and any raise is explained in the audit log. An administrator can disable the rule. Changing the user count recalculates priority and SLA deadlines |
| BR-17 | Only the reporter can give feedback, once, and only when the incident is RESOLVED, VERIFIED or CLOSED |
| BR-18 | Only an administrator can change priority-driving fields (impact, urgency, business criticality, service) after creation. Only the reporter or an administrator can edit the text fields, including the affected-user count (which recalculates priority under BR-16). Only the assigned technician or an administrator can change the category |
| BR-19 | Technicians cannot report incidents |
| BR-20 | Escalation applies to unacknowledged P1 and P2 incidents and steps up once per response interval after the deadline through Team Lead, System Administrator and IT Manager |
| BR-21 | Closed incidents are read-only: no notes, no edits |

## 5. Non-functional requirements

| ID | Category | Requirement | How it is met or checked |
|---|---|---|---|
| NFR-SEC-01 | Authentication | Signed tokens with expiry (default 60 minutes), server verifies on every request | PyJWT, `test_auth.py` |
| NFR-SEC-02 | Password storage | Passwords are hashed with bcrypt (cost 12 by default), never returned. Passwords need 8 to 128 characters with at least one letter and one number. bcrypt considers only the first 72 bytes | `utils/security.py`, fresh-install check |
| NFR-SEC-03 | Authorisation | Role checks on the server for every endpoint and object-level checks for incidents | `test_rbac.py`, `test_use_case_matrix.py` |
| NFR-SEC-04 | Input validation | All input validated with Pydantic, database access only through SQLAlchemy parameters | schemas, `422` tests |
| NFR-SEC-05 | Error safety | Errors return JSON `{detail, code}`. Stack traces and SQL are never shown | `middleware/errors.py` |
| NFR-SEC-06 | Configuration | Production mode refuses the default secret key and can start without demo accounts | `test_bootstrap.py` |
| NFR-AUD-01 | Auditability | Audit log cannot be edited or deleted through the API or the ORM | `test_t22` |
| NFR-PERF-01 | Responsiveness | Ordinary requests complete well under a second on a laptop with the demo data. Dashboards refresh every 30 seconds | observed, not load tested |
| NFR-REL-01 | Atomicity | One transaction per use case. A failure rolls everything back | `@transactional`, tests of rejected actions |
| NFR-REL-02 | Resilience | A failing notification never blocks an incident update. A failing audit write aborts the action | observer criticality |
| NFR-REL-03 | Determinism | Time comes from an injectable clock so SLA behaviour is testable | `domain/clock.py` |
| NFR-USE-01 | Usability | Role-specific navigation, loading, error and empty states on every data screen, readable messages | UI structure, manual test |
| NFR-MAINT-01 | Maintainability | Layered architecture, documented patterns, new strategy, channel or state means adding one class | `ARCHITECTURE.md` |
| NFR-MAINT-02 | Testability | Automated tests for rules, workflow, authorisation and API, with coverage reported | `TESTING_REPORT.md` |
| NFR-PORT-01 | Portability | Runs on Windows, macOS and Linux with Python 3.11 or later and Node 18 or later | README, fresh-install check on Linux |
| NFR-DATA-01 | Compatibility | An existing database gains new nullable columns automatically on start | `test_affected_users.py` migration test |
| NFR-LIM-01 | Scalability limit | Single process and SQLite. Not designed for many concurrent writers | technology report |

## 6. Interfaces

* **User interface:** React web application on port 5173 in development.
* **API:** REST over HTTP, JSON, bearer token, prefix `/api`, interactive documentation at `/docs`.
* **Database:** SQLite file, schema in `database/schema.sql`, data dictionary in `DATA_DICTIONARY.md`.
* **E-mail:** simulated through the notifications table.

## 7. Constraints

Python and FastAPI for the backend, React for the frontend, SQLite for storage, object-oriented design with at least Strategy, Observer, State and Repository patterns, and the 30 acceptance scenarios T01 to T30 (all covered).

## 8. Acceptance

The system is accepted when `python -m pytest` passes in `backend/`, the frontend builds with `npm run build`, and the manual walkthrough in `MANUAL_TASKS.md` has been performed and screenshotted. Current results are in `TESTING_REPORT.md`.
