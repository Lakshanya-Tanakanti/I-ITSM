# Technology selection report

## 1. Why this programming language?

**Python 3.11+** for the backend and **JavaScript (ES2022, JSX)** for the frontend.
Python reads close to plain English, which keeps the business rules (priority bands, lifecycle, SLA arithmetic) easy to review against the specification. It has first-class classes, abstract base classes, properties and decorators, so the required patterns are expressed directly rather than worked around. Its standard library (`datetime`, `threading`, `logging`) covers the SLA monitor and the simulated e-mail without extra dependencies, and pytest makes thorough testing quick. JavaScript is the only practical language for a browser UI.

## 2. Why this frontend technology?

**React with Vite, React Router, Axios and Recharts.**
React's component model suits an application made of many small repeated pieces (badges, tables, dialogs, cards). State stays local to a screen, and two small contexts (authentication and toasts) cover everything shared. Vite starts in seconds and proxies `/api` to the backend, which avoids CORS trouble during development. Recharts gives the dashboards real charts from the database data with little code. Lucide supplies consistent icons.

## 3. Why this backend technology?

**FastAPI with SQLAlchemy and Pydantic.**
FastAPI gives typed request validation and automatic OpenAPI documentation (`/docs`), which doubles as a live API specification. Pydantic rejects bad input before it reaches the business layer and produces precise error messages. Dependency injection fits the layered design: authentication and the per-request service container are plain dependencies. SQLAlchemy provides the ORM mapping and the event hooks used to guard the audit table.

## 4. Why this database?

**SQLite.**
It is a real SQL database with foreign keys, unique constraints and triggers, stored in one file, so a beginner on Windows installs nothing and the project runs anywhere. It is persistent (scenario T28), transactional, and good for a single-organisation service desk with tens of concurrent users. Because all SQL is behind repositories and SQLAlchemy, moving to PostgreSQL is a connection-string change plus a migration tool.

## 5. Why this architecture?

A **layered architecture** (routes, services, domain, repositories, models) with **design patterns at the points of change**:
Strategy where algorithms must be swappable (priority, assignment), State where behaviour depends on status (lifecycle), Observer where side effects must not tangle with the workflow (audit, notifications), Repository to isolate persistence, and dependency injection plus a unit of work to keep each request transactional. Business rules live only in services and the domain, so the HTTP layer and the UI can change without touching them. The structure is described in ARCHITECTURE.md.

## 6. What alternatives were considered?

| Choice | Alternatives | Why not |
|---|---|---|
| FastAPI | Django REST Framework, Flask, Spring Boot, Node.js/Express | Django brings an admin and ORM we would partly bypass. Flask lacks built-in validation. Spring Boot and Node are good but add a second language or heavier setup for this team size. |
| React | Angular, Vue, Flutter web | Angular is heavier for this scope. Vue is comparable, React has the larger ecosystem for charts and routing. |
| SQLite | PostgreSQL, MySQL, MongoDB | PostgreSQL is the right production target but needs an installer. A document database fits poorly with relational data such as incidents, skills and SLA policies. |
| JWT | Server sessions, OAuth | Stateless tokens suit a separate SPA. OAuth needs an identity provider that is out of scope. |
| Rule-based intelligence | Machine learning model, external AI service | Rules are explainable (every suggestion shows its reason), need no training data and work offline. |

## 7. Advantages and limitations

**Advantages:** one language per tier, little boilerplate, automatic API docs, strong validation, zero-install database, 210 automated tests, explainable intelligent features, a clean seam for every future change.
**Limitations:** SQLite allows one writer at a time. The SLA monitor is an in-process thread, so running several server processes would run several monitors (harmless because violations are unique, but wasteful). Python is slower than compiled languages for CPU-heavy work, which this application does not do. Simulated e-mail sends nothing. There is no automated frontend test suite. Duplicate and category intelligence is keyword-based, so it will not understand text it has no vocabulary for.

## 8. How does the technology support object-oriented design?

Python has abstract base classes (`abc`), inheritance, properties and duck typing, so `PriorityStrategy`, `AssignmentStrategy`, `NotificationChannel`, `IncidentState` and the observer interface are real abstractions with several concrete subclasses. SQLAlchemy maps classes to tables (`User`, `Incident`, `SlaPolicy` and so on) with relationships, and the private `_password_hash` attribute shows encapsulation. A custom exception hierarchy rooted in `AppError` carries HTTP status and a stable error code. FastAPI's dependency injection composes these objects per request without global state. See ARCHITECTURE.md sections 2 and 3 for the exact classes.

## 9. How would the system evolve with many more users?

1. **Database:** move from SQLite to PostgreSQL (same SQLAlchemy models), add Alembic migrations and indexes on the filter columns already used by the search.
2. **Run several API processes** behind a load balancer. Because tokens are stateless, no session store is needed.
3. **Move the SLA monitor** into one scheduled worker (a separate process or a task queue such as Celery or APScheduler with a lock) so exactly one instance runs checks.
4. **Move notifications** to a queue and add real adapters (SMTP, SMS, push). The `NotificationChannel` abstraction already isolates this.
5. **Caching** of read-heavy report queries (for example Redis) and pre-aggregated daily statistics.
6. **Containerise** with Docker, add CI/CD, central logging and metrics, and serve the built frontend from a CDN.
7. **Split into services** only if team size demands it: notifications and reporting are the natural first candidates because they are already event-driven.
