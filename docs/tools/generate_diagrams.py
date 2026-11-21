"""Generates every diagram source from the real code, then renders SVG and PNG.

    python docs/tools/generate_diagrams.py            (sources + rendering)
    python docs/tools/generate_diagrams.py --no-render (sources only)

Outputs go to docs/diagrams/. Class members, inheritance, tables, columns, keys and package
dependencies are READ FROM THE CODE. Only the choice of which classes to show per view, and
the use of composition / aggregation / dependency, is curated here (and checked by
verify_diagrams.py).
"""
import enum
import subprocess
import sys
from pathlib import Path

import codeinfo as ci
from codeinfo import classes
from sqlalchemy import inspect as sa_inspect

OUT = ci.ROOT / "docs" / "diagrams"
OUT.mkdir(parents=True, exist_ok=True)

# =============================================================================== class views
# edge kinds: composition *-- | aggregation o-- | association --> | dependency ..>
# For composition / aggregation / association the label is the attribute name that holds the link.
# For dependency the label is a verb: creates | uses | returns.
CLASS_VIEWS = {
    "class_1_lifecycle_state_pattern": dict(
        title="Incident lifecycle (State pattern)",
        classes=["IncidentState", "NewState", "ClassifiedState", "AssignedState", "AcknowledgedState", "InProgressState",
                 "ResolvedState", "VerifiedState", "ClosedState", "StateFactory", "LifecycleManager", "TransitionRule",
                 "IncidentStatus", "ActorKind"],
        edges=[
            ("LifecycleManager", "dependency", "StateFactory", "uses", "", ""),
            ("StateFactory", "dependency", "IncidentState", "creates", "", "1..*"),
            ("IncidentState", "dependency", "TransitionRule", "creates", "", "1..*"),
            ("IncidentState", "association", "IncidentStatus", "status", "", ""),
            ("TransitionRule", "association", "IncidentStatus", "target", "", ""),
            ("TransitionRule", "association", "ActorKind", "allowed", "", "1..*"),
        ]),
    "class_2_strategy_pattern": dict(
        title="Priority and assignment (Strategy pattern)",
        classes=["PriorityStrategy", "ScoreProductPriorityStrategy", "WeightedPriorityStrategy", "PriorityResult",
                 "AffectedUsersPolicy", "AssignmentStrategy", "SkillBasedStrategy", "LoadBasedStrategy",
                 "SkillThenLoadStrategy", "EligibilityPolicy", "AssignmentContext", "TechnicianCandidate",
                 "Recommendation", "Ineligibility", "StrategyFactory", "SettingsService", "AssignmentService"],
        edges=[
            ("PriorityStrategy", "dependency", "PriorityResult", "returns", "", ""),
            ("AssignmentStrategy", "dependency", "Recommendation", "returns", "", ""),
            ("AssignmentStrategy", "dependency", "TechnicianCandidate", "uses", "", ""),
            ("AssignmentStrategy", "dependency", "AssignmentContext", "uses", "", ""),
            ("EligibilityPolicy", "dependency", "Ineligibility", "returns", "", ""),
            ("AssignmentService", "composition", "EligibilityPolicy", "policy", "1", "1"),
            ("StrategyFactory", "dependency", "PriorityStrategy", "creates", "", ""),
            ("StrategyFactory", "dependency", "AssignmentStrategy", "creates", "", ""),
            ("SettingsService", "dependency", "StrategyFactory", "uses", "", ""),
        ]),
    "class_3_observer_and_channels": dict(
        title="Events, observers and notification channels (Observer pattern)",
        classes=["DomainEvent", "EventType", "EventObserver", "EventBus", "AuditObserver", "NotificationObserver",
                 "Message", "NotificationChannel", "InAppChannel", "SimulatedEmailChannel", "ChannelFactory",
                 "AuditRepository", "NotificationRepository", "BaseService"],
        edges=[
            ("BaseService", "dependency", "DomainEvent", "creates", "", ""),
            ("BaseService", "aggregation", "EventBus", "bus", "", "1"),
            ("EventBus", "aggregation", "EventObserver", "_observers", "1", "0..*"),
            ("EventBus", "dependency", "DomainEvent", "uses", "", ""),
            ("DomainEvent", "association", "EventType", "type", "", "1"),
            ("AuditObserver", "aggregation", "AuditRepository", "audit_repo", "", "1"),
            ("NotificationObserver", "aggregation", "NotificationChannel", "channels", "", "1..*"),
            ("NotificationObserver", "dependency", "Message", "creates", "", ""),
            ("ChannelFactory", "dependency", "InAppChannel", "registers", "", ""),
            ("ChannelFactory", "dependency", "SimulatedEmailChannel", "registers", "", ""),
        ]),
    "class_4_repository_pattern": dict(
        title="Data access (Repository pattern)",
        classes=["BaseRepository", "UserRepository", "TeamRepository", "TechnicianRepository", "CategoryRepository",
                 "ServiceRepository", "SlaPolicyRepository", "SettingRepository", "IncidentRepository",
                 "NoteRepository", "ResolutionRepository", "FeedbackRepository", "SlaViolationRepository",
                 "NotificationRepository", "AuditRepository", "IncidentFilters", "Repositories"],
        edges=[("Repositories", "composition", r, a, "1", "1") for r, a in [
            ("UserRepository", "users"), ("TeamRepository", "teams"), ("TechnicianRepository", "technicians"),
            ("CategoryRepository", "categories"), ("ServiceRepository", "services"),
            ("SlaPolicyRepository", "sla_policies"), ("SettingRepository", "settings"),
            ("IncidentRepository", "incidents"), ("NoteRepository", "notes"), ("ResolutionRepository", "resolutions"),
            ("FeedbackRepository", "feedback"), ("SlaViolationRepository", "violations"),
            ("NotificationRepository", "notifications"), ("AuditRepository", "audit")]]
        + [("IncidentRepository", "dependency", "IncidentFilters", "uses", "", "")]),
    "class_5_services_and_wiring": dict(
        title="Service layer and dependency injection",
        classes=["Container", "BaseService", "AuthService", "UserService", "ConfigService", "SettingsService",
                 "SlaService", "IncidentService", "AssignmentService", "IntelligenceService", "NotificationService",
                 "ReportService", "IncidentPresenter", "SlaMonitor", "IncidentFactory", "CreateResult",
                 "LifecycleManager", "Repositories", "EventBus", "Clock"],
        edges=[("Container", "composition", s, a, "1", "1") for s, a in [
            ("SettingsService", "settings"), ("SlaService", "sla"), ("AssignmentService", "assignment"),
            ("IntelligenceService", "intelligence"), ("IncidentService", "incidents"),
            ("IncidentPresenter", "presenter"), ("AuthService", "auth"), ("UserService", "users"),
            ("ConfigService", "config"), ("NotificationService", "notifications"), ("ReportService", "reports")]]
        + [("Container", "composition", "EventBus", "bus", "1", "1"),
           ("Container", "composition", "Repositories", "repos", "1", "1"),
           ("Container", "aggregation", "Clock", "clock", "1", "1"),
           ("BaseService", "aggregation", "Repositories", "repos", "", "1"),
           ("BaseService", "aggregation", "EventBus", "bus", "", "1"),
           ("BaseService", "aggregation", "Clock", "clock", "", "1"),
           ("IncidentService", "aggregation", "SlaService", "sla", "", "1"),
           ("IncidentService", "aggregation", "AssignmentService", "assignment", "", "1"),
           ("IncidentService", "aggregation", "IntelligenceService", "intelligence", "", "1"),
           ("IncidentService", "dependency", "IncidentFactory", "uses", "", ""),
           ("IncidentService", "dependency", "CreateResult", "creates", "", ""),
           ("IncidentService", "dependency", "LifecycleManager", "uses", "", ""),
           ("SlaMonitor", "dependency", "Container", "creates", "", "")]),
    "class_6_domain_entities": dict(
        title="Persistent entities (SQLAlchemy models)",
        classes=["User", "TechnicianProfile", "TechnicianSkill", "SupportTeam", "IncidentCategory", "Service",
                 "SlaPolicy", "Incident", "InvestigationNote", "Resolution", "EmployeeFeedback", "SlaViolation",
                 "Notification", "AuditLog", "SystemSetting"],
        edges="from_orm"),
    "class_7_exceptions_and_clock": dict(
        title="Exceptions and clock abstraction",
        classes=["AppError", "AuthenticationError", "PermissionDeniedError", "NotFoundError", "IncidentNotFoundError",
                 "ServiceNotFoundError", "ConflictError", "DuplicateResourceError", "InvalidTransitionError",
                 "TechnicianUnavailableError", "WorkloadExceededError", "MissingSkillError", "InvalidInputError",
                 "MissingSlaConfigurationError", "DatabaseUnavailableError", "Clock", "SystemClock", "MutableClock"],
        edges=[]),
}

# attributes shown for entities that have many columns (everything else: primary key + plain columns)
MODEL_ATTRIBUTES = {
    "Incident": ["id", "number", "title", "status", "priority", "priority_score", "impact", "effective_impact", "urgency",
                 "business_criticality", "affected_users", "response_deadline", "resolution_deadline", "sla_status",
                 "escalation_level"],
    "User": ["id", "employee_code", "full_name", "email", "role", "department", "is_active"],
    "AuditLog": ["id", "action", "description", "previous_state", "new_state", "created_at"],
}
MAX_MODEL_ATTRS = 9


def fmt_method(name, func, kind) -> str:
    params, ret = ci.method_signature(func)
    mark = "*" if getattr(func, "__isabstractmethod__", False) else "$" if kind == "static" else ""
    ret = f" {ret}" if ret else ""
    return f"+{name}({', '.join(params)}){ret}{mark}"


def class_block(name: str) -> list:
    cls = classes()[name]
    lines = [f"    class {name} {{"]
    st = ci.stereotype(cls)
    if st:
        lines.append(f"        <<{st}>>")
    if issubclass(cls, enum.Enum):
        for member in cls:
            lines.append(f"        {member.name}")
        lines.append("    }")
        return lines
    if ci.is_model(cls):
        mapper = sa_inspect(cls)
        cols = {c.key: c for c in mapper.column_attrs}
        wanted = MODEL_ATTRIBUTES.get(name)
        if wanted is None:
            fk_cols = {c.name for t in [cls.__table__] for c in t.columns if c.foreign_keys}
            wanted = [k for k in cols if k not in fk_cols][:MAX_MODEL_ATTRS]
        for key in wanted:
            col = cls.__table__.columns[key]
            tag = " PK" if col.primary_key else ""
            lines.append(f"        +{key}: {col.type.__class__.__name__}{tag}")
    else:
        for attr in ci.own_attributes(cls):
            vis = "-" if attr.startswith("_") else "+"
            ann = getattr(cls, "__annotations__", {}).get(attr)
            t = ci.short_type(ann) if ann is not None else ""
            lines.append(f"        {vis}{attr}{': ' + t if t else ''}")
    for mname, (func, kind) in ci.public_methods(cls).items():
        lines.append("        " + fmt_method(mname, func, kind))
    lines.append("    }")
    return lines


def inheritance_edges(selected: list) -> list:
    out = []
    for name in selected:
        cls = classes()[name]
        for base in cls.__bases__:
            if base.__name__ in selected and base is not object:
                kind = "<|.." if ci.stereotype(base) == "interface" else "<|--"
                out.append(f"    {base.__name__} {kind} {name}")
    return out


ARROW = {"composition": "*--", "aggregation": "o--", "association": "-->", "dependency": "..>"}


def orm_edges(selected: list) -> list:
    """Relationships between entities, read from the SQLAlchemy mappers."""
    lines = []
    done = set()
    for cls, rel in ci.model_relationships():
        a, b = cls.__name__, rel.mapper.class_.__name__
        if a not in selected or b not in selected:
            continue
        direction = rel.direction.name
        if direction == "MANYTOONE" and rel.back_populates:
            continue  # drawn from the owning (one) side
        if direction == "ONETOMANY":
            child_fk_cols = [c for c in rel.mapper.local_table.columns
                             if any(fk.column.table is cls.__table__ for fk in c.foreign_keys)]
            not_null = all(not c.nullable for c in child_fk_cols)
            delete_orphan = "delete-orphan" in rel.cascade
            kind = "composition" if (delete_orphan or not_null) else "aggregation"
            mult_b = "0..*" if rel.uselist else ("1" if not_null and False else "0..1")
            mult_a = "1"
        else:
            kind = "association"
            fk_cols = [c for c in cls.__table__.columns if c.foreign_keys and rel.mapper.local_table in
                       {fk.column.table for fk in c.foreign_keys}]
            nullable = any(c.nullable for c in fk_cols)
            mult_a, mult_b = "*", ("0..1" if nullable else "1")
        key = (a, b, rel.key)
        if key in done:
            continue
        done.add(key)
        lines.append(f'    {a} "{mult_a}" {ARROW[kind]} "{mult_b}" {b} : {rel.key}')
    return lines


def render_class_view(slug: str, spec: dict) -> str:
    sel = spec["classes"]
    lines = ["---", f"title: {spec['title']}", "---", "classDiagram", "    direction TB"]
    for name in sel:
        lines += class_block(name)
    lines += inheritance_edges(sel)
    if spec["edges"] == "from_orm":
        lines += orm_edges(sel)
    else:
        for src, kind, dst, label, ca, cb in spec["edges"]:
            ca_s = f' "{ca}"' if ca else ""
            cb_s = f' "{cb}"' if cb else ""
            lines.append(f"    {src}{ca_s} {ARROW[kind]}{cb_s} {dst} : {label}")
    return "\n".join(lines) + "\n"


# =============================================================================== ER diagram
def sql_type(col) -> str:
    text = col.type.compile(dialect=__import__("sqlalchemy.dialects.sqlite", fromlist=["x"]).dialect())
    return text.lower().replace(" ", "")


def er_diagram() -> str:
    lines = ["---", "title: I-ITSM database (ER diagram)", "---", "erDiagram"]
    rels = []
    for table in ci.tables():
        lines.append(f"    {table.name} {{")
        for col in table.columns:
            keys = []
            if col.primary_key:
                keys.append("PK")
            if col.foreign_keys:
                keys.append("FK")
            if col.unique or any(len(i.columns) == 1 and col in i.columns.values() and i.unique for i in table.indexes):
                keys.append("UK")
            note = "" if col.nullable or col.primary_key else "NOT NULL"
            key_s = (" " + ",".join(keys)) if keys else ""
            note_s = f' "{note}"' if note else ""
            lines.append(f"        {sql_type(col)} {col.name}{key_s}{note_s}")
        lines.append("    }")
        for col in table.columns:
            for fk in col.foreign_keys:
                parent = fk.column.table.name
                unique = bool(col.unique) or any(i.unique and list(i.columns) == [col] for i in table.indexes)
                left = "||"
                right = ("|o" if col.nullable else "||") if unique else ("o{" if not col.nullable else "|{")
                if not unique:
                    right = "o{"  # zero or many children for every parent
                left_sym = "|o" if col.nullable else "||"
                rels.append(f'    {parent} {left_sym}--{right} {table.name} : "{col.name}"')
    return "\n".join(lines + rels) + "\n"


def data_dictionary() -> str:
    out = ["# Data dictionary", "",
           "Generated from the SQLAlchemy models by `docs/tools/generate_diagrams.py`. Do not edit by hand.", ""]
    for table in ci.tables():
        cls = ci.table_class(table)
        out += [f"## {table.name}", "", f"Entity class: `{cls.__name__ if cls else '?'}`", "",
                "| Column | Type | Null | Key | Notes |", "|---|---|---|---|---|"]
        uniques = {c.name for i in table.indexes if i.unique for c in i.columns}
        for col in table.columns:
            key = []
            if col.primary_key:
                key.append("PK")
            for fk in col.foreign_keys:
                key.append(f"FK to {fk.column.table.name}.{fk.column.name}")
            if col.unique or col.name in uniques:
                key.append("unique")
            notes = []
            if col.default is not None and getattr(col.default, "arg", None) is not None and not callable(col.default.arg):
                notes.append(f"default {col.default.arg}")
            out.append(f"| {col.name} | {sql_type(col)} | {'yes' if col.nullable else 'no'} | {', '.join(key)} | {'; '.join(notes)} |")
        checks = [c for c in table.constraints if c.__class__.__name__ == "CheckConstraint"]
        uq = [c for c in table.constraints if c.__class__.__name__ == "UniqueConstraint"]
        if checks or uq:
            out += ["", "Constraints:"]
            for c in uq:
                out.append(f"* unique ({', '.join(col.name for col in c.columns)})")
            for c in checks:
                out.append(f"* check `{c.sqltext}`")
        out.append("")
    return "\n".join(out)


# =============================================================================== architecture (DOT)
LAYERS = [
    ("Presentation (React SPA)", "#e0e7ff", []),
    ("API layer", "#dbeafe", ["main", "routes", "middleware", "schemas"]),
    ("Business layer", "#dcfce7", ["services", "strategies", "observers"]),
    ("Domain", "#fef3c7", ["domain"]),
    ("Data access", "#fce7f3", ["repositories", "models", "database"]),
    ("Cross-cutting", "#f1f5f9", ["config", "utils"]),
]
PKG_LABEL = {
    "main": "main.py\\nFastAPI app factory", "routes": "routes\\nHTTP endpoints", "middleware": "middleware\\nauth deps, error handlers",
    "schemas": "schemas\\nPydantic models", "services": "services\\nworkflows, SLA, intelligence,\\nreports, DI container",
    "strategies": "strategies\\npriority, assignment", "observers": "observers\\nevent bus, audit,\\nnotifications",
    "domain": "domain\\nenums, lifecycle, events,\\nexceptions, clock", "repositories": "repositories\\nall database access",
    "models": "models\\nSQLAlchemy entities", "database": "database.py\\nengine, session", "config": "config.py\\nsettings",
    "utils": "utils\\nsecurity, text, seed",
}


def architecture_dot() -> str:
    graph = ci.import_graph()
    lines = ["digraph arch {", '  graph [rankdir=TB, fontname="Helvetica", fontsize=12, nodesep=0.5, ranksep=0.7, labelloc=t, '
             'label="I-ITSM architecture (backend edges are the real import dependencies between packages)"];',
             '  node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=11, margin="0.15,0.08"];',
             '  edge [color="#475569", arrowsize=0.7];']
    lines.append('  subgraph cluster_ui { label="Presentation (React SPA, browser)"; style="rounded,filled"; fillcolor="#e0e7ff"; color="#818cf8";')
    lines.append('    pages [label="pages\\nlogin, dashboards, incidents,\\nadmin screens", fillcolor="#c7d2fe"];')
    lines.append('    ui [label="components, context, layouts\\nbadges, tables, dialogs,\\nauth and toasts", fillcolor="#c7d2fe"];')
    lines.append('    axios [label="services/api.js\\nAxios client + JWT header", fillcolor="#c7d2fe"]; }')
    for i, (title, color, pkgs) in enumerate(LAYERS[1:], start=1):
        lines.append(f'  subgraph cluster_{i} {{ label="{title}"; style="rounded,filled"; fillcolor="{color}"; color="#94a3b8";')
        for p in pkgs:
            lines.append(f'    {p} [label="{PKG_LABEL[p]}", fillcolor="white"];')
        lines.append("  }")
    lines.append('  db [label="SQLite file\\nitsm.db", shape=cylinder, fillcolor="#fde68a"];')
    lines.append('  monitor [label="SLA monitor thread\\n(every 60 s)", shape=component, fillcolor="#fecaca"];')
    lines += ['  pages -> ui [arrowhead=none];', '  pages -> axios;',
              '  axios -> routes [label="HTTP /api (JSON, JWT)", style=bold, color="#4f46e5"];',
              '  models -> db [label="SQL", style=bold, color="#b45309"];',
              '  monitor -> services [label="run_check()", style=dashed];']
    for src in sorted(graph):
        for dst in sorted(graph[src]):
            if src == "utils":      # utils/seed.py is a command line helper, shown separately
                continue
            lines.append(f"  {src} -> {dst};")
    lines.append('  utils -> services [style=dotted, label="seed.py only"];')
    lines.append("}")
    return "\n".join(lines) + "\n"


# =============================================================================== use case (DOT)
def use_case_dot(only=None) -> str:
    sys.path.insert(0, str(ci.BACKEND / "tests"))
    from use_case_matrix import USE_CASES, GROUPS
    actors = {"EMPLOYEE": "Employee", "TECHNICIAN": "Technician", "ADMIN": "Administrator"}
    all_uc = USE_CASES
    if only:
        keep = {u["id"] for u in all_uc if only in u["actors"]}
        keep |= {t for u in all_uc if u["id"] in keep for t in u.get("includes", []) + u.get("extends", [])}
        use_cases = [u for u in all_uc if u["id"] in keep]
        actors = {k: v for k, v in actors.items() if k == only}
    else:
        use_cases = all_uc
    lines = ["digraph uc {",
             '  graph [rankdir=LR, fontname="Helvetica", fontsize=13, nodesep=0.18, ranksep=2.2, splines=line, compound=true, '
             'labelloc=t, label="I-ITSM use case diagram"];',
             '  node [fontname="Helvetica", fontsize=10];',
             '  edge [arrowsize=0.6, color="#64748b"];']
    for key, label in actors.items():
        lines.append(f'  {key} [shape=none, label=<<TABLE BORDER="0" CELLBORDER="0"><TR><TD><IMG SRC="actor.png"/></TD></TR>'
                     f'<TR><TD><B>{label}</B></TD></TR></TABLE>>];')
    if not only:
        lines.append('  TIMER [shape=none, label=<<TABLE BORDER="0" CELLBORDER="0"><TR><TD><IMG SRC="actor.png"/></TD></TR>'
                     '<TR><TD><B>SLA monitor</B><BR/>(system timer)</TD></TR></TABLE>>];')
    lines.append('  subgraph cluster_system { label="I-ITSM system"; style="rounded"; color="#334155"; fontsize=12;')
    for g_i, (gid, gtitle, color) in enumerate(GROUPS):
        lines.append(f'    subgraph cluster_g{g_i} {{ label="{gtitle}"; style="rounded,filled"; fillcolor="{color}"; color="#cbd5e1"; fontsize=10;')
        for uc in use_cases:
            if uc["group"] == gid:
                lines.append(f'      {uc["id"]} [shape=ellipse, style=filled, fillcolor="white", label="{uc["name"]}"];')
        lines.append("    }")
    lines.append("  }")
    for uc in use_cases:
        for actor in uc["actors"]:
            if actor != "TIMER" and actor not in actors:
                continue
            lines.append(f"  {actor} -> {uc['id']} [dir=none];")
        for target in uc.get("includes", []):
            lines.append(f'  {uc["id"]} -> {target} [style=dashed, label="«include»", fontsize=8, fontcolor="#475569"];')
        for target in uc.get("extends", []):
            lines.append(f'  {target} -> {uc["id"]} [style=dashed, label="«extend»", fontsize=8, fontcolor="#475569"];')
    lines.append("}")
    return "\n".join(lines) + "\n"


ACTOR_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="48" height="76" viewBox="0 0 48 76">
<g fill="none" stroke="#1e293b" stroke-width="2.5" stroke-linecap="round">
<circle cx="24" cy="12" r="9" fill="#fff"/><line x1="24" y1="21" x2="24" y2="46"/><line x1="8" y1="31" x2="40" y2="31"/>
<line x1="24" y1="46" x2="10" y2="70"/><line x1="24" y1="46" x2="38" y2="70"/></g></svg>
"""


# =============================================================================== main
def render_mermaid(src: Path):
    cfg = OUT / ".puppeteer.json"
    cfg.write_text('{"executablePath":"/usr/bin/google-chrome","args":["--no-sandbox","--disable-setuid-sandbox"]}')
    for ext, extra in (("svg", []), ("png", ["-s", "2", "-b", "white"])):
        target = src.with_suffix("." + ext)
        subprocess.run(["mmdc", "-p", str(cfg), "-i", str(src), "-o", str(target), "-w", "1800", *extra],
                       check=True, capture_output=True, timeout=180)
    cfg.unlink()


def render_dot(src: Path):
    for ext in ("svg", "png"):
        extra = ["-Gdpi=130"] if ext == "png" else []
        subprocess.run(["dot", f"-T{ext}", *extra, str(src), "-o", str(src.with_suffix('.' + ext))],
                       check=True, capture_output=True, cwd=OUT, timeout=120)


def main():
    render = "--no-render" not in sys.argv
    written = []
    for slug, spec in CLASS_VIEWS.items():
        path = OUT / f"{slug}.mmd"
        path.write_text(render_class_view(slug, spec))
        written.append(path)
    er = OUT / "er_diagram.mmd"
    er.write_text(er_diagram())
    written.append(er)
    (ci.ROOT / "docs" / "DATA_DICTIONARY.md").write_text(data_dictionary())
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", (96, 152), (255, 255, 255, 0))
    d = ImageDraw.Draw(img)
    for xy in ([(48, 42), (48, 92)], [(16, 62), (80, 62)], [(48, 92), (20, 140)], [(48, 92), (76, 140)]):
        d.line(xy, fill="#1e293b", width=5)
    d.ellipse((30, 4, 66, 40), fill="white", outline="#1e293b", width=5)
    img.save(OUT / "actor.png")
    arch = OUT / "architecture.dot"
    arch.write_text(architecture_dot())
    uc = OUT / "use_case_diagram.dot"
    uc.write_text(use_case_dot())
    per_actor = []
    for key, name in (("EMPLOYEE", "employee"), ("TECHNICIAN", "technician"), ("ADMIN", "administrator")):
        f = OUT / f"use_case_{name}.dot"
        f.write_text(use_case_dot(key).replace("I-ITSM use case diagram", f"I-ITSM use cases: {name}"))
        per_actor.append(f)
    print("sources written:", len(written) + 3)
    if render:
        for p in written:
            render_mermaid(p)
        render_dot(arch)
        render_dot(uc)
        for f in per_actor:
            render_dot(f)
        print("rendered SVG and PNG")


if __name__ == "__main__":
    main()
