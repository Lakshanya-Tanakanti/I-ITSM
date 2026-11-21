"""Single source of truth for the use case diagram.

Each use case lists the actors that take part. When a `probe` is given, test_use_case_matrix.py
calls the real API as every role and checks that exactly the listed actors are allowed in.
`{n}` in a probe path is replaced by the number of a freshly reported incident.
"""

GROUPS = [
    ("acct", "Account", "#eef2ff"),
    ("report", "Report and follow incidents", "#ecfdf5"),
    ("work", "Resolve incidents", "#fffbeb"),
    ("assign", "Assignment and priority", "#fdf2f8"),
    ("admin", "Administration", "#f1f5f9"),
    ("insight", "Monitoring and reports", "#fef2f2"),
    ("system", "Automatic behaviour", "#f8fafc"),
]

E, T, A, S = "EMPLOYEE", "TECHNICIAN", "ADMIN", "TIMER"
ALL = [E, T, A]


def uc(id_, name, group, actors, probe=None, includes=(), extends=()):
    return dict(id=id_, name=name, group=group, actors=list(actors), probe=probe,
                includes=list(includes), extends=list(extends))


USE_CASES = [
    uc("UC01", "Sign in", "acct", ALL, probe=("GET", "/api/auth/me", None)),
    uc("UC02", "Manage own profile\\nand password", "acct", ALL, probe=("PATCH", "/api/auth/me", {"department": "IT"})),
    uc("UC03", "Receive and read\\nnotifications", "acct", ALL, probe=("GET", "/api/notifications", None)),

    uc("UC04", "Report incident", "report", [E, A], probe=("POST", "/api/incidents", "NEW_INCIDENT"),
       includes=["UC05", "UC06"]),
    uc("UC05", "Preview priority\\n(affected users rule)", "report", ALL, probe=("POST", "/api/intelligence/preview-priority", "PREVIEW")),
    uc("UC06", "Check duplicates and\\nsuggest category", "report", ALL, probe=("POST", "/api/intelligence/check-duplicates", "DUPES")),
    uc("UC07", "View incident list\\nand details", "report", ALL, probe=("GET", "/api/incidents", None)),
    uc("UC08", "Track timeline and SLA", "report", ALL, probe=("GET", "/api/incidents/{n}/timeline", None)),
    uc("UC09", "Add comment or\\nprovide information", "report", [E, T, A], probe=None),
    uc("UC10", "Verify, reopen\\nor close resolved incident", "report", [E, A], probe=None),
    uc("UC11", "Give feedback", "report", [E], probe=("POST", "/api/incidents/{n}/feedback", {"rating": 5})),

    uc("UC12", "View my work queue", "work", [T], probe=("GET", "/api/technicians/me/queue", None)),
    uc("UC13", "Set availability", "work", [T], probe=("PATCH", "/api/technicians/me/availability", {"is_available": True})),
    uc("UC14", "Acknowledge and\\ninvestigate incident", "work", [T, A], probe=None),
    uc("UC15", "Add investigation note", "work", [T, A], probe=None),
    uc("UC16", "Request more information", "work", [T, A], probe=None, extends=["UC09"]),
    uc("UC17", "Resolve incident\\n(summary and root cause)", "work", [T, A], probe=None),
    uc("UC18", "View technician workload", "work", [T, A], probe=("GET", "/api/technicians/workload", None)),

    uc("UC19", "Assign or reassign\\ntechnician", "assign", [A], probe=("POST", "/api/incidents/{n}/assign", {"technician_id": 1}),
       includes=["UC20"]),
    uc("UC20", "View ranked\\nrecommendations", "assign", [A], probe=("GET", "/api/incidents/{n}/recommendations", None)),
    uc("UC21", "Override priority\\nand criticality", "assign", [A], probe=("PATCH", "/api/incidents/{n}", {"impact": 5})),

    uc("UC22", "Manage users and\\ntechnician skills", "admin", [A], probe=("GET", "/api/users", None)),
    uc("UC23", "Manage categories\\nand services", "admin", [A], probe=("POST", "/api/categories", {"name": "Probe category"})),
    uc("UC24", "Manage SLA policies", "admin", [A], probe=("GET", "/api/sla-policies", None)),
    uc("UC25", "Manage teams", "admin", [A], probe=("GET", "/api/teams", None)),
    uc("UC26", "Configure system\\nstrategies and rules", "admin", [A], probe=("GET", "/api/settings", None)),

    uc("UC27", "View reports\\nand analytics", "insight", [A], probe=("GET", "/api/reports/overview", None)),
    uc("UC28", "Monitor SLA risk\\nand violations", "insight", [A], probe=("GET", "/api/sla/at-risk", None)),
    uc("UC29", "Review audit log\\nand email outbox", "insight", [A], probe=("GET", "/api/audit-logs", None)),

    uc("UC30", "Classify and assign\\nnew incident", "system", [S], includes=["UC20"]),
    uc("UC31", "Detect SLA breach\\nand escalate", "system", [S]),
    uc("UC32", "Write audit entries\\nand send notifications", "system", [S]),
]
