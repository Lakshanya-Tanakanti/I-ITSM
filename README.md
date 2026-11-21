# I-ITSM: Intelligent IT Service Management and Incident Resolution System

A complete incident management platform for an organisation's IT service desk. Employees report problems, the system classifies and prioritises them, assigns the best technician, tracks SLA deadlines, notifies everyone involved and keeps an unchangeable audit trail.

* **Frontend:** React, Vite, React Router, Axios, Recharts
* **Backend:** Python 3.11+, FastAPI, SQLAlchemy, Pydantic, JWT, bcrypt
* **Database:** SQLite (a single file, no installation needed)

---

## 1. Quick start on Windows (PowerShell)

> **Honest note.** Every automated check reported in the project report was run on Linux, and the application was also run on macOS. The commands below are standard PowerShell and Windows is the intended platform, but a complete Windows run has not been recorded in the report. If a step fails, see section 5.

You need two programs installed once:

| Program | Version | Check it with | Download |
|---|---|---|---|
| Python | 3.11 or newer | `python --version` | https://www.python.org/downloads/ (tick **Add python.exe to PATH** in the installer) |
| Node.js | 18 or newer (LTS) | `node --version` | https://nodejs.org |

Unzip the project, for example to `C:\Users\You\Downloads\I-ITSM`. Open **two** PowerShell windows and leave both open while you use the app. Tip: in File Explorer open the `backend` folder, click the address bar, type `powershell` and press Enter.

### Window 1: backend (API on port 8000)

```powershell
cd C:\Users\You\Downloads\I-ITSM\backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --port 8000
```

Wait for `Application startup complete`. Then check http://localhost:8000/docs in your browser.

If PowerShell refuses to run the activation script, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` and activate again. You can also use `py -3 -m venv .venv` if `python` is not found.

### Window 2: frontend (website on port 5173)

```powershell
cd C:\Users\You\Downloads\I-ITSM\frontend
npm install
npm run dev
```

Open **http://localhost:5173** and sign in with a demo account from section 2.

### Initialise or reset the database (demo data)

The database is created automatically on the first start. When it is empty, the start-up code fills it with the demo data in section 2 (12 incidents, 10 users, 8 services, 5 SLA policies). You do not have to do anything. To wipe everything and seed again, stop the backend (Ctrl+C), then inside `backend` with the virtual environment active:

```powershell
python -m app.utils.seed --reset
```

For review without running Python, `database\schema.sql` (15 tables) and `database\sample_data.sql` (the same demo rows) are plain SQLite files: `sqlite3 itsm.db < database\schema.sql` and then `sqlite3 itsm.db < database\sample_data.sql`. The application does not need them.

Optional settings: `Copy-Item .env.example .env` inside `backend`, then edit `.env` (section 4). Everything works without it.

### Run the tests

Stop the server with Ctrl+C first, or open a third PowerShell window. Inside `backend`, with the virtual environment active:

```powershell
python -m pytest -q
```

Expected result with the current code: `264 passed`. The warning count varies between runs (0 to 6) and is harmless, see `docs\evidence\TEST_RESULTS.md`. The tests use an in-memory database and never touch `itsm.db`. For the coverage figure install the extra package first: `pip install pytest-cov`, then `python -m pytest -q --cov=app`.

The front end has no automated tests. To check that it builds: inside `frontend` run `npm run build`.

---

## 2. Demo accounts (development only)

> **These accounts exist only to try the system on your own computer. Never use them or these passwords in a real deployment.** For a real start, see "Going live" in section 4.

| Role | E-mail | Password |
|---|---|---|
| Admin | admin@iitsm.example.com | Admin@123 |
| Technician (network, authentication, cloud; Infrastructure team lead) | arjun.kapoor@iitsm.example.com | Tech@1234 |
| Technician (applications, database, software; Application team lead) | meera.joshi@iitsm.example.com | Tech@1234 |
| Technician (hardware, network) | vikram.singh@iitsm.example.com | Tech@1234 |
| Technician (security, authentication, applications) | pooja.desai@iitsm.example.com | Tech@1234 |
| Technician (storage, cloud, database; set to unavailable) | imran.khan@iitsm.example.com | Tech@1234 |
| Employee | rahul.verma@iitsm.example.com | Employee@123 |
| Employee | sneha.iyer@iitsm.example.com | Employee@123 |
| Employee | karan.malhotra@iitsm.example.com | Employee@123 |
| Employee | divya.nair@iitsm.example.com | Employee@123 |

The login page also has click-to-fill shortcuts. You can register new employee accounts yourself on the Register page. Technician and admin accounts can only be created by an administrator.

The seed creates 12 incidents (INC-1001 to INC-1012) in different states, including one breached P1, one at-risk incident and one unassigned incident, so every dashboard has something to show.

---

## 3. Take a guided tour (10 minutes)

1. Sign in as **rahul.verma** (employee). Choose **Report incident**. Type "Payment application unavailable", describe it, pick the service **Payment Gateway**. A category suggestion and a duplicate warning appear while you type. Submit.
2. Sign in as **admin**. Open the new incident. See the SLA countdown, the risk explanation and the technician recommendations. Reassign if you like.
3. Sign in as the assigned technician (probably **meera.joshi**). Acknowledge, start investigation, ask the reporter for information.
4. Back as **rahul.verma**: the dashboard shows an information request. Reply, then check the notification bell.
5. As the technician: resolve with a summary and root cause.
6. As **rahul.verma**: verify the fix, rate it, close the incident (or reopen it with a reason).
7. As **admin**: open **Audit log**, **Reports**, **SLA monitor** and **E-mail outbox** to see everything that happened.

---

## 4. Configuration

All settings have working defaults. To change them, copy `backend\.env.example` to `backend\.env` and edit it.

| Variable | Default | Meaning |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./itsm.db` | Where data is stored |
| `SECRET_KEY` | development value | Signs login tokens. **Change this in production.** |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 60 | Login lifetime |
| `SLA_MONITOR_ENABLED` | true | Background SLA checks |
| `SLA_MONITOR_INTERVAL_SECONDS` | 60 | How often the monitor runs |
| `SEED_DEMO_DATA` | true | Create demo data when the database is empty |

Business settings (assignment strategy, priority strategy, duplicate threshold, auto-assignment, escalation, default workload limit) are changed by an admin on the **Settings** page, no restart needed.

**Affected users and priority.** The report form has an optional "number of affected users" field. Large numbers raise the impact that is counted in the priority score (10 or more users: at least 2, 50: 3, 250: 4, 1000: 5). The rule never lowers the impact you choose, it is explained on the incident and in the audit log, and an administrator can turn it off with the checkbox on the **Settings** page. See the business rules in Chapter 2 of `docs/FINAL_PROJECT_REPORT.pdf`.

**Upgrading an existing database.** If you already have an `itsm.db` from an earlier version, just restart the backend. New nullable columns (for example `incidents.effective_impact`) are added automatically and no data is lost. Back up the file first if it holds anything you care about.

**Going live (no demo accounts).** In `backend\.env` set `APP_ENV=production`, a long random `SECRET_KEY`, `SEED_DEMO_DATA=false`, and `INITIAL_ADMIN_EMAIL`, `INITIAL_ADMIN_PASSWORD` and `INITIAL_ADMIN_NAME`. On the first start with an empty database the system creates only that administrator plus the standard categories, services and SLA policies. The administrator then adds technicians and employees on the Users page. In production mode the server refuses to start while `SECRET_KEY` still has its default value.

Start again with clean demo data: stop the backend, then inside `backend` run `python -m app.utils.seed --reset`.

---

## 5. Common problems on Windows

| Problem | Fix |
|---|---|
| `python` is not recognised, or opens the Microsoft Store | Install Python from python.org and tick **Add python.exe to PATH**. Then open a new PowerShell. You can also try `py -3 -m venv .venv`. |
| `.venv\Scripts\Activate.ps1 cannot be loaded because running scripts is disabled` | Run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` and activate again. Or use Command Prompt and run `.venv\Scripts\activate.bat`. |
| `pip` is not recognised | The virtual environment is not active. Look for `(.venv)` at the start of the prompt. |
| `No module named 'app'` | You are not inside the `backend` folder. Run `cd backend` first. |
| `Address already in use` / port 8000 busy | Another program uses the port. Find it with `netstat -ano \| findstr :8000` and stop it, or start on another port, for example `--port 8001`, and change the proxy target in `frontend\vite.config.js`. |
| Browser shows "Cannot reach the server" or the terminal shows `ECONNREFUSED` | The backend is not running. Start Window 1 first. |
| `npm` is not recognised | Install Node.js LTS and open a new PowerShell. |
| `npm install` fails with network errors | Check your internet or proxy and retry. Delete the `node_modules` folder and run again. |
| Login says "Incorrect e-mail address or password" | Use an account from the table above. If you changed data, run the seed reset in section 4. |
| Seeing old data or a broken database | Stop the backend, delete `backend\itsm.db`, start again. |
| White page after login | Open the browser developer tools (F12), look at the Console, and check that both windows are still running. |

---

## 6. Project layout

```
I-ITSM/
  backend/
    app/
      main.py            FastAPI app factory, routes, startup
      config.py          Settings
      database.py        Engine and session setup
      domain/            Enums, lifecycle (State pattern), events, exceptions, clock
      models/            SQLAlchemy entities
      repositories/      All database access (Repository pattern)
      strategies/        Priority and assignment algorithms (Strategy pattern)
      observers/         Audit and notification reactions (Observer pattern)
      services/          Business workflows, SLA, intelligence, reports
      schemas/           Pydantic request and response models
      routes/            HTTP endpoints (thin)
      middleware/        Auth dependencies and error handlers
      utils/             Security, text analysis, demo seed
    tests/               264 pytest tests (14 files)
    requirements.txt
  frontend/
    src/pages/           One file per screen
    src/components/      Shared UI pieces
    src/context/         Auth and toast state
    src/services/api.js  Axios client with token handling
  database/              schema.sql (generated from the models) and sample_data.sql (demo rows)
  docs/                  Diagrams, traceability, test evidence, archive
```

Interactive API documentation is available while the backend runs at **http://localhost:8000/docs**.

---

## 7. More documentation

- docs/diagrams/: use case, ER, class and architecture diagrams
- docs/DATA_DICTIONARY.md: every table and column
- docs/REQUIREMENTS_TRACEABILITY.md: each requirement mapped to code and tests
- docs/evidence/TEST_RESULTS.md: test results and coverage
- docs/screenshots/evidence/: screenshots used as test evidence
