# Architecture

Diagrams in `docs/diagrams/` are generated from the code by `docs/tools/generate_diagrams.py` and checked against it by `docs/tools/verify_diagrams.py` (see `docs/DIAGRAM_VERIFICATION.md`): `architecture.png`, `use_case_*.png`, `er_diagram.png` and seven class diagram views `class_1` to `class_7`.

## 1. Overview

```
 Browser (React SPA)
      |  HTTPS/JSON, JWT bearer token
      v
 FastAPI routes ----> Dependencies (auth, role checks)      <- API layer, thin
      |
      v
 Services (workflows, orchestration, transactions)          <- business logic
   |        |            |             |
   |        |            |             +--> Strategies (priority, assignment)
   |        |            +--> Domain (lifecycle states, enums, events, exceptions)
   |        +--> EventBus --> Observers (audit, notifications --> channels)
   v
 Repositories (all SQL)  --->  SQLAlchemy models  --->  SQLite
```

Every request gets its own `Container` (dependency injection) that builds the repositories and services around one database session. A `@transactional` decorator commits when a service method succeeds and rolls everything back when it fails, so a rejected action never leaves half-written data behind.

| Layer | Responsibility | Never does |
|---|---|---|
| `routes/` | HTTP, validation, auth checks, calls one service method | Business rules, SQL |
| `schemas/` | Pydantic input and output models | Persistence |
| `services/` | Workflows, SLA, intelligence, reports | HTTP concerns |
| `domain/` | Enums, lifecycle, events, exceptions, clock | Database access |
| `strategies/` | Pluggable algorithms | UI or HTTP |
| `observers/` | Audit and notification reactions | Own the workflow |
| `repositories/` | Every database read and write | Business decisions |
| `models/` | Tables and relationships | Import FastAPI |

## 2. Design patterns (where to find them)

| Pattern | Purpose | Code |
|---|---|---|
| **Strategy** | Interchangeable priority and assignment algorithms, chosen at run time from Settings | `strategies/priority.py` (`ScoreProductPriorityStrategy`, `WeightedPriorityStrategy`, plus the `AffectedUsersPolicy` helper), `strategies/assignment.py` (`SkillBasedStrategy`, `LoadBasedStrategy`, `SkillThenLoadStrategy`), `strategies/factory.py` |
| **State** | Incident lifecycle; each status object knows its legal next states, who may move there and which fields are required | `domain/lifecycle.py` (`NewState`, `ClassifiedState`, ... `ClosedState`, `LifecycleManager`) |
| **Observer** | Services publish domain events; audit and notification observers react without the service knowing them | `domain/events.py`, `observers/` (`EventBus`, the `EventObserver` interface, `AuditObserver`, `NotificationObserver`) |
| **Repository** | One class per aggregate hides SQL from services | `repositories/` |
| **Factory** | Builds incidents and users with all defaults, and notification channels by name | `services/incident_factory.py`, `observers/channels.py` (`ChannelFactory`) |
| **Polymorphic channels** | `NotificationChannel` interface with `InAppChannel` and `SimulatedEmailChannel`; a real SMTP or SMS channel would be one more subclass registered with `ChannelFactory`. (The e-mail channel only simulates sending, so it is not a full Adapter.) | `observers/channels.py` |
| **Dependency injection** | Services receive their collaborators | `services/container.py` |
| **Unit of work** | One transaction per use case | `services/base.py` (`transactional`) |

The audit observer is **critical**: it runs inside the same transaction, so if an audit row cannot be written the whole action fails. The notification observer is **non-critical**: a notification problem is logged but never blocks an incident update.

## 3. Object-oriented design in practice

* **Encapsulation:** `User` stores the password hash in a private attribute and exposes only `set_password` and `check_password`. State objects hide their transition tables.
* **Abstraction:** `PriorityStrategy`, `AssignmentStrategy`, `NotificationChannel`, `IncidentState`, `EventObserver` and `Clock` are abstract base classes or interfaces. Services depend on them, never on concrete classes.
* **Inheritance:** concrete states, strategies and channels extend those bases. `AppError` is the root of the exception tree.
* **Polymorphism:** `strategy.rank(...)`, `state.rules()` and `channel.deliver(...)` are called without knowing which concrete class answers.
* **Custom exceptions:** `AuthenticationError` (401), `PermissionDeniedError` (403), `NotFoundError` with `IncidentNotFoundError` and `ServiceNotFoundError` (404), `ConflictError` with `DuplicateResourceError`, `InvalidTransitionError`, `TechnicianUnavailableError`, `WorkloadExceededError` and `MissingSkillError` (409), `InvalidInputError` (422), `MissingSlaConfigurationError`, `DatabaseUnavailableError`, plus `AuditImmutableError` raised by the audit model guard. Handlers in `middleware/errors.py` turn each one into safe JSON `{detail, code}`. Unexpected errors return a generic 500 and never leak a stack trace.

## 4. Data model

15 tables, defined in `backend/app/models` and exported to `database/schema.sql` (`docs/tools/export_schema.py`). The full ER diagram is `docs/diagrams/er_diagram.png` and every column is listed in `docs/DATA_DICTIONARY.md`.

```
users --< technician_profiles >-- support_teams (lead_id -> users)
               |
               +--< technician_skills >-- incident_categories
services --< incidents >-- incident_categories
users (reporter, assigned technician) --< incidents
incidents --< investigation_notes
incidents --1 resolutions
incidents --1 employee_feedback
incidents --< sla_violations   (unique per incident and SLA type)
incidents --< notifications >-- users
incidents --< audit_logs       (append-only)
sla_policies >-- services (optional override)
system_settings (key, value)
```

Key constraints: unique e-mail, unique incident number (`INC-1001` upward), unique `(incident_id, sla_type)` on violations so a breach is recorded exactly once, foreign keys enforced, and ORM event listeners (`models/audit.py`) that block `UPDATE` and `DELETE` on `audit_logs`. `database/schema.sql` additionally contains two optional triggers that enforce the same rule inside SQLite when that file is loaded by hand. The running application does not create those triggers itself.

All timestamps are timezone-aware UTC. A custom `UTCDateTime` type guarantees that SQLite returns aware values, and an injectable `Clock` lets the tests move time to exercise SLA behaviour deterministically.

## 5. Incident lifecycle

```
NEW -> CLASSIFIED -> ASSIGNED -> ACKNOWLEDGED -> IN_PROGRESS -> RESOLVED -> VERIFIED -> CLOSED
                                                     ^              |
                                                     +--- reopen ---+  (reporter, reason required)
```

* NEW to CLASSIFIED and CLASSIFIED to ASSIGNED happen automatically at creation (unless no technician is eligible, in which case the incident waits in CLASSIFIED and admins are notified).
* Only the assigned technician (or an admin) acknowledges, investigates and resolves. Resolve requires `resolution_summary` and `root_cause`.
* Only the reporter (or an admin) verifies, reopens and closes.
* Admin reassignment keeps the incident in ASSIGNED and is audited.
* Every illegal jump (for example NEW to CLOSED) is rejected with HTTP 409 and changes nothing. The test suite checks every disallowed pair.

## 6. Key algorithms

**Priority.** `score = impact x urgency x business_criticality`, each 1 to 5. P1 40 to 125, P2 20 to 39, P3 8 to 19, P4 1 to 7. Criticality defaults from the service, an admin may override it. An alternative weighted strategy exists to demonstrate interchangeability.

**Affected users.** The reporter's impact (1 to 5) is a judgement, so the number of affected users acts as a safety net, implemented by `AffectedUsersPolicy`. The impact that is *counted* is `max(reporter impact, floor)`, where the floor is 2 for 10 or more users, 3 for 50 or more, 4 for 250 or more and 5 for 1000 or more. It can raise the impact but never lowers it. The stored `impact` is what the reporter chose, `effective_impact` is what entered the score, and the audit log explains any raise ("Impact raised from 3 to 4 because 300 users are affected"). Editing `affected_users` recalculates priority and SLA deadlines. Administrators can switch the rule off with the `affected_users_adjustment` setting. When it is off, or no count is given, the result equals the original formula. `POST /api/intelligence/preview-priority` lets the report form show the result before submitting.

**SLA.** Policy selection picks a service-specific active policy first, then the standard one for the priority. Deadlines are `created_at + target` in calendar minutes. The response clock stops at acknowledgement, the resolution clock at RESOLVED. The monitor (a background thread, every 60 s, also callable from the admin screen) warns once at 75 percent, records one violation per incident per type and escalates unacknowledged P1 and P2 incidents through three levels named Team Lead, System Administrator and IT Manager, stepping up once per response interval after the deadline. Level 1 notifies the technician's team lead (or the admins when the lead is the assigned technician), levels 2 and 3 notify the active administrators. Late acknowledgements and resolutions are detected even if the monitor did not run in time.

**Assignment eligibility.** Technician must be active, available, have the category skill and be below the workload limit. Active workload counts ASSIGNED, ACKNOWLEDGED and IN_PROGRESS. The system never silently assigns someone without the skill. An admin can override and the override is audited. Strategies rank the eligible list and return a reason for each score.

**Intelligence (all rule based, explainable, no external service).**
1. Category suggestion from admin-editable keywords with synonym normalisation, returning matched keywords and a reason.
2. Duplicate detection using Jaccard similarity on normalised tokens against incidents created in the last 7 days, boosted for the same service or category. It only warns.
3. Technician recommendation (see above).
4. SLA risk: percentage of the active window used, plus points for no technician, P1 or P2 priority, overloaded technician and "acknowledged but not started". HIGH at 75 points or more or already breached, MEDIUM at 50 or more.
5. Correlation of open incidents on the same service within 24 hours, and suggested resolutions from similar resolved incidents.

## 7. Security

* Passwords hashed with bcrypt, never returned by any endpoint.
* JWT bearer tokens with expiry. Deactivated users are rejected even with an old token.
* Role checks are enforced on the server for every endpoint (`require_admin`, `require_technician`, `require_staff`) and object-level checks decide which incidents a user may read. The UI hides buttons, but the server is the authority.
* Public registration always creates an EMPLOYEE, any role sent by the client is ignored.
* Employees cannot see internal investigation notes or other people's incidents. An incident that does not exist returns 404 and one the user may not see returns 403. Both use the same safe JSON shape and reveal no incident data.
* All input is validated by Pydantic. SQL is built only through SQLAlchemy parameters.
* The audit log has no write or delete endpoint and is protected by ORM listeners, and by optional database triggers when `database/schema.sql` is used.
* Errors never expose stack traces or SQL.
* CORS is limited to the configured frontend origin.
* Production start: `APP_ENV=production` refuses the default `SECRET_KEY`, `SEED_DEMO_DATA=false` skips all demo accounts, and `INITIAL_ADMIN_*` creates the first administrator (`utils/seed.py::bootstrap_if_empty`, tested in `test_bootstrap.py`). Also serve over HTTPS and move to PostgreSQL for real load.

## 8. Frontend structure

Single page app. `AuthContext` keeps the user and token, `ToastContext` shows messages, `services/api.js` adds the bearer token and turns errors into readable text, and a 401 anywhere signs the user out. `ProtectedRoute` guards pages by role. Every data screen goes through the shared `Async` component that renders loading, error with retry, and empty states. Dashboards refresh every 30 seconds, SLA countdowns tick every second.
