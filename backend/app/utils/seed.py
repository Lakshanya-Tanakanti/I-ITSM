"""Demo data.

The seeder does not insert incident rows by hand. It drives the real services with a
movable clock, so the audit trail, notifications, SLA deadlines and violations are exactly
what the application itself would have produced.

Run manually (from the `backend` folder):
    python -m app.utils.seed            # seed only when the database is empty
    python -m app.utils.seed --reset    # wipe everything and seed again

DEMO ACCOUNTS ARE FOR DEVELOPMENT ONLY. Change or deactivate them before any real deployment.
"""
import argparse
import logging
from datetime import timedelta

from sqlalchemy import update

from app.config import Settings, get_settings
from app.domain.clock import MutableClock, utcnow
from app.domain.enums import Priority, Role
from app.models import (
    IncidentCategory, Notification, Service, SlaPolicy, SupportTeam, TechnicianSkill,
)
from app.services.auth_service import new_user
from app.services.container import build_container

logger = logging.getLogger("iitsm.seed")

ADMIN_PASSWORD = "Admin@123"
TECH_PASSWORD = "Tech@1234"
EMPLOYEE_PASSWORD = "Employee@123"

CATEGORIES = {
    "Hardware": ("Physical devices and peripherals",
                 "laptop, desktop, monitor, keyboard, mouse, printer, hardware, battery, screen, boot, projector, jam, jammed, toner, kiosk"),
    "Software": ("Installed software and licences",
                 "software, install, installation, licence, license, upgrade, patch, office, antivirus"),
    "Network": ("Connectivity and network equipment",
                "network, wifi, lan, vpn, router, switch, internet, bandwidth, dns, connectivity, access point"),
    "Database": ("Database servers and queries",
                 "database, sql, query, deadlock, replication, schema, oracle, mysql, postgres"),
    "Cloud": ("Cloud platforms and virtual infrastructure",
              "cloud, aws, azure, bucket, vm, instance, kubernetes, container, sync"),
    "Security": ("Security incidents and threats",
                 "security, phishing, malware, virus, breach, ransomware, suspicious, vulnerability, unauthorized"),
    "Authentication": ("Sign-in, passwords and access",
                       "login, password, sso, authentication, mfa, otp, locked out, credentials, access denied"),
    "Application": ("Business applications and web portals",
                    "application, portal, erp, payment, checkout, website, api, transaction, catalogue, gateway, email"),
    "Storage": ("Disks, file shares and quotas",
                "storage, disk, quota, nas, san, file share, shared drive, volume, capacity"),
}

SERVICES = [
    ("Payment Gateway", "Online payment processing", 5),
    ("Single Sign-On", "Campus-wide authentication", 5),
    ("Student ERP", "Enrolment, timetable and grades", 4),
    ("E-mail", "Staff and student mail", 4),
    ("Campus Wi-Fi", "Wireless network", 3),
    ("Cloud Storage", "Shared cloud file storage", 3),
    ("Library System", "Catalogue and lending", 2),
    ("Printing", "Managed print service", 1),
]

SLA_DEFAULTS = {Priority.P1: (5, 30), Priority.P2: (15, 120), Priority.P3: (60, 480), Priority.P4: (240, 1440)}

TECHNICIANS = [
    # name, email, experience, available, team, {category: proficiency}
    ("Arjun Kapoor", "arjun.kapoor", 8, True, "Infrastructure Support",
     {"Network": 5, "Authentication": 4, "Cloud": 3}),
    ("Meera Joshi", "meera.joshi", 6, True, "Application Support",
     {"Application": 5, "Database": 4, "Software": 4}),
    ("Vikram Singh", "vikram.singh", 4, True, "Infrastructure Support",
     {"Hardware": 5, "Network": 3}),
    ("Pooja Desai", "pooja.desai", 5, True, "Application Support",
     {"Security": 5, "Authentication": 4, "Application": 3, "Software": 3}),
    ("Imran Khan", "imran.khan", 10, False, "Infrastructure Support",
     {"Storage": 5, "Cloud": 4, "Database": 3}),
]

EMPLOYEES = [
    ("Rahul Verma", "rahul.verma", "Finance"),
    ("Sneha Iyer", "sneha.iyer", "Library"),
    ("Karan Malhotra", "karan.malhotra", "Engineering"),
    ("Divya Nair", "divya.nair", "Human Resources"),
]

DOMAIN = "iitsm.example.com"


def _create_reference_data(c, now):
    repos = c.repos
    admin = new_user(repos, full_name="Anita Rao", email=f"admin@{DOMAIN}", password=ADMIN_PASSWORD,
                     role=Role.ADMIN, department="IT Management", now=now)
    cats = {}
    for name, (desc, keywords) in CATEGORIES.items():
        cats[name] = repos.categories.add(IncidentCategory(name=name, description=desc, keywords=keywords, is_active=True))
    for name, desc, crit in SERVICES:
        repos.services.add(Service(name=name, description=desc, business_criticality=crit, is_active=True))
    for prio, (resp, resol) in SLA_DEFAULTS.items():
        repos.sla_policies.add(SlaPolicy(name=f"Standard {prio.value} ({prio.label})", priority=prio,
                                         response_minutes=resp, resolution_minutes=resol, warning_percent=75))
    erp = repos.services.get_by_name("Student ERP")
    repos.sla_policies.add(SlaPolicy(name="Student ERP stricter P2", priority=Priority.P2, service_id=erp.id,
                                     response_minutes=10, resolution_minutes=90, warning_percent=75))
    teams = {n: repos.teams.add(SupportTeam(name=n, description=d, is_active=True)) for n, d in (
        ("Infrastructure Support", "Network, cloud, storage and hardware"),
        ("Application Support", "Business applications, databases and security"))}
    techs = {}
    for name, local, exp, available, team, skills in TECHNICIANS:
        user = new_user(repos, full_name=name, email=f"{local}@{DOMAIN}", password=TECH_PASSWORD,
                        role=Role.TECHNICIAN, department=team, now=now)
        profile = user.technician_profile
        profile.experience_years, profile.is_available = exp, available
        profile.team, profile.team_id = teams[team], teams[team].id
        for cname, prof in skills.items():
            profile.skills.append(TechnicianSkill(category_id=cats[cname].id, proficiency=prof))
        techs[name] = user
    teams["Infrastructure Support"].lead = techs["Arjun Kapoor"]
    teams["Application Support"].lead = techs["Meera Joshi"]
    employees = {}
    for name, local, dept in EMPLOYEES:
        employees[name] = new_user(repos, full_name=name, email=f"{local}@{DOMAIN}", password=EMPLOYEE_PASSWORD,
                                   role=Role.EMPLOYEE, department=dept, now=now)
    c.session.commit()
    return admin, employees, techs


# Each scenario: age of creation in minutes, reporter, text, service, impact, urgency,
# then a list of (minutes after creation, action, payload).
def _scenarios(emp):
    R, S, K, D = emp["Rahul Verma"], emp["Sneha Iyer"], emp["Karan Malhotra"], emp["Divya Nair"]
    day = 24 * 60
    return [
        dict(age=5 * day, who=S, service="Library System", impact=3, urgency=3,
             title="Library catalogue search returns no results",
             desc="Searching the library catalogue for any book title shows an empty list since this morning.",
             steps=[(20, "ack"), (30, "start"),
                    (120, "resolve", "Rebuilt the catalogue search index and restarted the search service.",
                     "The nightly index job failed after a disk-space warning."),
                    (300, "verify"), (360, "close"), (370, "feedback", 5, "Quick fix, thank you.")]),
        dict(age=4 * day, who=D, service="Printing", impact=1, urgency=2,
             title="Office printer on floor 2 keeps jamming",
             desc="The shared printer on the second floor jams on every second print job and shows a roller error.",
             steps=[(60, "ack"), (80, "start"),
                    (180, "resolve", "Replaced the paper feed roller and cleaned the paper path.",
                     "Worn feed roller."),
                    (400, "verify"), (420, "close"), (430, "feedback", 4, "Works well now.")]),
        dict(age=3 * day, who=K, service="Cloud Storage", impact=2, urgency=3,
             title="Cannot sync files to Cloud Storage",
             desc="The sync client on my laptop shows an upload error for every file in the project folder.",
             steps=[(30, "ack"), (45, "start"),
                    (240, "resolve", "Re-authorised the sync client and cleared the stuck upload queue.",
                     "Expired sync token after a password policy change."),
                    (1500, "verify"), (1560, "close"), (1570, "feedback", 4, "Solved, took a while.")]),
        dict(age=2 * day, who=R, service="Single Sign-On", impact=3, urgency=4,
             title="Single Sign-On rejects valid passwords for some staff",
             desc="Several finance staff cannot log in with their correct passwords. Login fails with access denied.",
             steps=[(3, "ack"), (5, "start"),
                    (25, "resolve", "Synchronised the directory replica and cleared the cached credentials.",
                     "A stale directory replica rejected newly changed passwords."),
                    (120, "verify"), (180, "close"), (190, "feedback", 5, "Very fast, thank you!")]),
        dict(age=30 * 60, who=K, service="Student ERP", impact=3, urgency=3,
             title="Student ERP timetable page extremely slow",
             desc="The timetable page of the student portal takes over a minute to load for the whole engineering department.",
             steps=[(7, "ack"), (10, "start"),
                    (80, "resolve", "Added a missing index on the timetable query and recycled the application pool.",
                     "Full table scan caused by a missing index."),
                    (600, "verify"), (620, "close")]),
        dict(age=20 * 60, who=D, service="E-mail", impact=2, urgency=3,
             title="Email delivery delayed by about 30 minutes",
             desc="Incoming mail for the HR team arrives with a delay of roughly half an hour since yesterday evening.",
             steps=[(9, "ack"), (15, "start"),
                    (90, "resolve", "Cleared the stuck outbound queue and restarted the mail relay.",
                     "A large message blocked the relay queue."),
                    (400, "verify")]),
        dict(age=6 * 60, who=S, service="Campus Wi-Fi", impact=3, urgency=3,
             title="Campus Wi-Fi keeps dropping in the library reading room",
             desc="The wireless connection disconnects every few minutes in the reading room on the first floor.",
             steps=[(10, "ack"), (20, "start"),
                    (90, "resolve", "Replaced the faulty access point and moved clients to the new radio channel.",
                     "Failing access point firmware.")]),
        dict(age=3 * 60, who=R, service="E-mail", impact=2, urgency=2,
             title="Email attachments larger than 5 MB bounce",
             desc="Whenever I send an attachment bigger than 5 MB the message bounces back with a size error.",
             steps=[(20, "ack"), (30, "start"),
                    (60, "resolve", "Increased the outbound message size limit to 25 MB.",
                     "Limit was reset to a default after the last server update."),
                    (100, "reopen", "The bounce still happens for messages to external recipients.")]),
        dict(age=25, who=R, service="Payment Gateway", impact=4, urgency=5,
             title="Payment application is unavailable",
             desc="The organisation's payment application is unavailable and users are unable to complete transactions.",
             steps=[(2, "ack"), (4, "start")]),
        dict(age=12, who=S, service="Payment Gateway", impact=5, urgency=5,
             title="Unable to make payments on the checkout page",
             desc="Every payment attempt fails on the checkout page, the transaction keeps failing for all customers.",
             steps=[]),
        dict(age=20, who=D, service="Library System", impact=2, urgency=3,
             title="Library self-checkout kiosk screen is frozen",
             desc="The touch screen of the self-checkout kiosk near the entrance is frozen and does not react.",
             steps=[]),
        dict(age=30, who=K, service="Cloud Storage", impact=2, urgency=2,
             title="Storage quota exceeded for the research department",
             desc="The research department share has reached its quota and nobody can save new files.",
             steps=[]),
    ]


def _run_steps(c, clock, incident_number, created_at, steps, reporter):
    for step in steps:
        minutes, action, *args = step
        clock.set(created_at + timedelta(minutes=minutes))
        incident = c.repos.incidents.get_by_number(incident_number)
        tech = incident.assigned_technician
        if action == "ack":
            c.incidents.transition(tech, incident_number, "ACKNOWLEDGED")
        elif action == "start":
            c.incidents.transition(tech, incident_number, "IN_PROGRESS")
        elif action == "resolve":
            c.incidents.transition(tech, incident_number, "RESOLVED", resolution_summary=args[0], root_cause=args[1])
        elif action == "verify":
            c.incidents.transition(reporter, incident_number, "VERIFIED")
        elif action == "close":
            c.incidents.transition(reporter, incident_number, "CLOSED", closure_note="Confirmed working.")
        elif action == "feedback":
            c.incidents.submit_feedback(reporter, incident_number, args[0], args[1])
        elif action == "reopen":
            c.incidents.transition(reporter, incident_number, "IN_PROGRESS", reason=args[0])


def run_seed(session_factory, settings: Settings) -> None:
    real_now = utcnow()
    clock = MutableClock(real_now - timedelta(days=8))
    session = session_factory()
    try:
        c = build_container(session, clock, settings)
        admin, employees, techs = _create_reference_data(c, clock.now())
        for scenario in sorted(_scenarios(employees), key=lambda s: -s["age"]):
            created_at = real_now - timedelta(minutes=scenario["age"])
            clock.set(created_at)
            service = c.repos.services.get_by_name(scenario["service"])
            result = c.incidents.create_incident(scenario["who"], {
                "title": scenario["title"], "description": scenario["desc"], "service_id": service.id,
                "impact": scenario["impact"], "urgency": scenario["urgency"],
            })
            _run_steps(c, clock, result.incident.number, created_at, scenario["steps"], scenario["who"])

        clock.set(real_now)
        # Old notifications are marked as read; recent ones stay unread so the bell is not empty.
        session.execute(update(Notification).where(Notification.created_at < real_now - timedelta(hours=2))
                        .values(is_read=True))
        session.commit()
        c.sla.run_check()
        logger.info("Demo data created: %s users, %s incidents", c.repos.users.count(), c.repos.incidents.count())
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def bootstrap_if_empty(session_factory, settings: Settings) -> bool:
    """Production start: no demo people or incidents. Creates the first administrator from
    INITIAL_ADMIN_EMAIL / INITIAL_ADMIN_PASSWORD plus the standard categories, services and
    SLA policies, so the system is usable straight away. Does nothing when users already exist."""
    session = session_factory()
    try:
        c = build_container(session, MutableClock(), settings)
        if c.repos.users.count() > 0:
            return False
        if not settings.initial_admin_email or not settings.initial_admin_password:
            logger.warning("The database is empty and demo data is switched off. Set INITIAL_ADMIN_EMAIL and "
                           "INITIAL_ADMIN_PASSWORD in backend/.env and restart to create the first administrator.")
            return False
        repos, now = c.repos, utcnow()
        new_user(repos, full_name=settings.initial_admin_name, email=settings.initial_admin_email,
                 password=settings.initial_admin_password, role=Role.ADMIN, department="IT Management", now=now)
        for name, (desc, keywords) in CATEGORIES.items():
            repos.categories.add(IncidentCategory(name=name, description=desc, keywords=keywords, is_active=True))
        for name, desc, crit in SERVICES:
            repos.services.add(Service(name=name, description=desc, business_criticality=crit, is_active=True))
        for prio, (resp, resol) in SLA_DEFAULTS.items():
            repos.sla_policies.add(SlaPolicy(name=f"Standard {prio.value} ({prio.label})", priority=prio,
                                             response_minutes=resp, resolution_minutes=resol, warning_percent=75))
        session.commit()
        logger.info("Bootstrap complete: administrator %s created.", settings.initial_admin_email)
        return True
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def seed_if_empty(session_factory, settings: Settings) -> bool:
    with session_factory() as session:
        if build_container(session, MutableClock(), settings).repos.users.count() > 0:
            return False
    run_seed(session_factory, settings)
    return True


def main() -> None:  # pragma: no cover - command line helper
    from app.database import Base, get_default_engine, get_default_session_factory, init_db

    parser = argparse.ArgumentParser(description="Create I-ITSM demo data")
    parser.add_argument("--reset", action="store_true", help="drop all tables first")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    engine = get_default_engine()
    if args.reset:
        from app import models  # noqa: F401
        Base.metadata.drop_all(engine)
    init_db(engine)
    created = seed_if_empty(get_default_session_factory(), get_settings())
    print("Demo data created." if created else "Database already contains data. Use --reset to start again.")


if __name__ == "__main__":  # pragma: no cover
    main()
