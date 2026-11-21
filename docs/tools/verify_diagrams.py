"""Independent check that the diagram SOURCES match the code. Exit code 1 on any discrepancy.

    python docs/tools/generate_diagrams.py && python docs/tools/verify_diagrams.py

It parses docs/diagrams/*.mmd and *.dot as text (it does not reuse the generator's data) and
compares them with the live code: classes, stereotypes, attributes, methods, direct inheritance,
relationship attributes, ORM cardinalities, tables, columns, keys, foreign keys, the package
import graph, and the use case actors against the permission matrix.
"""
import ast
import inspect
import re
import sys
from pathlib import Path

import codeinfo as ci
from sqlalchemy import inspect as sa_inspect

D = ci.ROOT / "docs" / "diagrams"
problems, checks = [], 0
FACTORY_RETURNS = {"Container": "build_container"}   # a class built through a module level factory function


def check(ok, message):
    global checks
    checks += 1
    if not ok:
        problems.append(message)


# ------------------------------------------------------------------------------ class diagrams
def parse_class_file(path):
    text = path.read_text()
    blocks = {}
    for m in re.finditer(r"^    class (\w+) \{\n(.*?)^    \}", text, re.S | re.M):
        blocks[m.group(1)] = [l.strip() for l in m.group(2).splitlines() if l.strip()]
    edges = re.findall(r'^    (\w+)(?: "([^"]*)")? (<\|--|<\|\.\.|\*--|o--|-->|\.\.>)(?: "([^"]*)")? (\w+)(?: : (.+))?$',
                       text, re.M)
    return blocks, edges


def verify_class_views():
    code = ci.classes()
    all_attrs_cache = {}
    for path in sorted(D.glob("class_*.mmd")):
        blocks, edges = parse_class_file(path)
        tag = path.stem
        names = set(blocks)
        for name, lines in blocks.items():
            cls = code.get(name)
            check(cls is not None, f"{tag}: class {name} does not exist in the code")
            if cls is None:
                continue
            stereo = next((l[2:-2] for l in lines if l.startswith("<<")), None)
            check(stereo == ci.stereotype(cls), f"{tag}: {name} stereotype {stereo!r} but code says {ci.stereotype(cls)!r}")
            members = [l for l in lines if not l.startswith("<<")]
            methods = {re.match(r"\+(\w+)\(", l).group(1) for l in members if re.match(r"\+\w+\(", l)}
            attrs = {re.match(r"[+-](\w+)", l).group(1) for l in members if re.match(r"[+-]\w+(?!\()", l) and "(" not in l}
            if hasattr(cls, "__members__"):
                check({m.strip() for m in members} == set(cls.__members__), f"{tag}: enum {name} members differ")
                continue
            real_methods = set(ci.public_methods(cls))
            check(methods == real_methods, f"{tag}: {name} methods drawn {sorted(methods)} vs code {sorted(real_methods)}")
            if ci.is_model(cls):
                cols = {c.key for c in sa_inspect(cls).column_attrs}
                check(attrs <= cols, f"{tag}: {name} draws unknown columns {sorted(attrs - cols)}")
            else:
                real = set(ci.own_attributes(cls))
                check(attrs == real, f"{tag}: {name} attributes drawn {sorted(attrs)} vs code {sorted(real)}")
        # edges
        for a, ca, kind, cb, b, label in edges:
            check(a in code and b in code, f"{tag}: edge {a} {kind} {b} uses an unknown class")
            if a not in code or b not in code:
                continue
            check(a in names and b in names, f"{tag}: edge {a} {kind} {b} points outside the view")
            if kind in ("<|--", "<|.."):
                # drawn as BASE kind DERIVED
                check(code[a] in code[b].__bases__, f"{tag}: {b} does not directly extend {a}")
                if kind == "<|..":
                    check(ci.stereotype(code[a]) == "interface", f"{tag}: {a} drawn as interface but is not")
                continue
            label = (label or "").strip()
            if kind == "..>":
                check(label in {"creates", "uses", "returns", "registers"}, f"{tag}: bad dependency label {label!r}")
                src = inspect.getsource(sys.modules[code[a].__module__]) if label != "creates" else None
                # the dependency must be visible in the source of class a (or its module for abstract returns)
                try:
                    body = inspect.getsource(code[a])
                except OSError:
                    body = ""
                mentioned = re.search(rf"\b{b}\b", body) is not None
                if label == "returns":
                    mentioned = mentioned or re.search(rf"\b{b}\b", inspect.getsource(sys.modules[code[a].__module__])) is not None
                if label == "uses" and not mentioned:
                    mentioned = re.search(rf"\b{b}\b", inspect.getsource(sys.modules[code[a].__module__])) is not None
                if label == "registers":
                    mentioned = re.search(rf"{a}\.register\({b}\)", inspect.getsource(sys.modules[code[a].__module__])) is not None
                if not mentioned and b in FACTORY_RETURNS:
                    fn = FACTORY_RETURNS[b]
                    func = getattr(sys.modules[code[b].__module__], fn, None)
                    returns_b = func is not None and getattr(func, "__annotations__", {}).get("return") in (code[b], b)
                    mentioned = returns_b and re.search(rf"\b{fn}\(", body) is not None
                check(mentioned, f"{tag}: {a} ..> {b} ({label}) but {a}'s source never mentions {b}")
            else:
                if ci.is_model(code[a]):
                    rels = {r.key: r for r in sa_inspect(code[a]).relationships}
                    r = rels.get(label)
                    check(r is not None and r.mapper.class_ is code[b], f"{tag}: {a}.{label} is not a relationship to {b}")
                    if r is not None:
                        many = r.uselist
                        check(("*" in cb) == bool(many) if kind != "-->" else True,
                              f"{tag}: cardinality {cb!r} on {a}.{label} disagrees with uselist={many}")
                        if kind == "*--":
                            fkcols = [c for c in r.mapper.local_table.columns
                                      if any(fk.column.table is code[a].__table__ for fk in c.foreign_keys)]
                            check("delete-orphan" in r.cascade or all(not c.nullable for c in fkcols),
                                  f"{tag}: {a} *-- {b} drawn as composition but the child may outlive the parent")
                else:
                    holders = ci.attribute_names(code[a])
                    check(label in holders, f"{tag}: {a} has no attribute {label!r} (edge to {b})")
                    # the attribute must plausibly hold the target type (annotation or constructor argument)
                    if label in holders:
                        src_text = ""
                        for k in code[a].__mro__:
                            try:
                                src_text += inspect.getsource(k)
                            except (OSError, TypeError):
                                pass
                        if kind == "*--":
                            check(re.search(rf"\b{b}\(", src_text) is not None or re.search(rf"\b{b}\b", src_text) is not None,
                                  f"{tag}: {a} *-- {b} drawn as composition but {a} never builds/mentions {b}")
    # every direct base inside a view must be drawn
    for path in sorted(D.glob("class_*.mmd")):
        blocks, edges = parse_class_file(path)
        drawn = {(a, b) for a, _, k, _, b, _ in edges if k in ("<|--", "<|..")}
        for name in blocks:
            cls = code[name]
            for base in cls.__bases__:
                if base.__name__ in blocks:
                    check((base.__name__, name) in drawn, f"{path.stem}: inheritance {base.__name__} -> {name} missing")


# ------------------------------------------------------------------------------ ER diagram
def verify_er():
    text = (D / "er_diagram.mmd").read_text()
    drawn = {}
    for m in re.finditer(r"^    (\w+) \{\n(.*?)^    \}", text, re.S | re.M):
        cols = {}
        for l in m.group(2).splitlines():
            parts = l.strip().split()
            if len(parts) >= 2:
                keys = parts[2] if len(parts) > 2 and not parts[2].startswith('"') else ""
                cols[parts[1]] = (parts[0], set(filter(None, keys.split(","))), "NOT NULL" in l)
        drawn[m.group(1)] = cols
    rels = {(m.group(1), m.group(2), m.group(3)) for m in
            re.finditer(r'^    (\w+) [|o}{]+--[|o}{]+ (\w+) : "(\w+)"$', text, re.M)}
    tables = {t.name: t for t in ci.tables()}
    check(set(drawn) == set(tables), f"ER: tables differ: {set(drawn) ^ set(tables)}")
    expected_rels = set()
    for name, t in tables.items():
        check(set(drawn.get(name, {})) == {c.name for c in t.columns}, f"ER: columns of {name} differ")
        for c in t.columns:
            d = drawn.get(name, {}).get(c.name)
            if not d:
                continue
            check(("PK" in d[1]) == c.primary_key, f"ER: PK flag wrong for {name}.{c.name}")
            check(("FK" in d[1]) == bool(c.foreign_keys), f"ER: FK flag wrong for {name}.{c.name}")
            if not c.primary_key:
                check(d[2] == (not c.nullable), f"ER: NOT NULL flag wrong for {name}.{c.name}")
            for fk in c.foreign_keys:
                expected_rels.add((fk.column.table.name, name, c.name))
    check(rels == expected_rels, f"ER: relationships differ: missing {expected_rels - rels}, extra {rels - expected_rels}")
    # cross check against a real SQLite database created from the models
    import sqlite3
    from sqlalchemy import create_engine
    from app.database import init_db
    eng = create_engine("sqlite://")
    init_db(eng)
    raw = eng.raw_connection()
    cur = raw.cursor()
    for name in tables:
        info = cur.execute(f"PRAGMA table_info({name})").fetchall()
        check({r[1] for r in info} == set(drawn.get(name, {})), f"ER: live SQLite columns of {name} differ from the diagram")
        uniq = set()
        for idx in cur.execute(f"PRAGMA index_list({name})").fetchall():
            if idx[2]:
                cols_ = [r[2] for r in cur.execute(f"PRAGMA index_info({idx[1]})").fetchall()]
                if len(cols_) == 1:
                    uniq.add(cols_[0])
        for cname, d in drawn.get(name, {}).items():
            pk_single = sum(1 for r in info if r[5]) == 1 and any(r[1] == cname and r[5] for r in info)
            if "PK" in d[1]:
                continue
            check(("UK" in d[1]) == (cname in uniq), f"ER: UK flag wrong for {name}.{cname} (live SQLite says unique={cname in uniq})")
        fks = {(r[3], r[2]) for r in cur.execute(f"PRAGMA foreign_key_list({name})").fetchall()}
        want = {(c, p) for (p, t, c) in rels if t == name}
        check(fks == {(c, p) for (c, p) in want}, f"ER: live SQLite foreign keys of {name} differ from the diagram")
    raw.close()


# ------------------------------------------------------------------------------ architecture
def independent_import_graph():
    pkgs = {"main", "routes", "middleware", "schemas", "services", "strategies", "observers", "domain",
            "repositories", "models", "database", "config", "utils"}
    graph = {}
    app = ci.BACKEND / "app"
    for py in app.rglob("*.py"):
        rel = py.relative_to(app)
        src_pkg = rel.parts[0].removesuffix(".py") if len(rel.parts) > 1 or py.name != "__init__.py" else None
        if src_pkg not in pkgs:
            continue
        tree = ast.parse(py.read_text())
        for node in ast.walk(tree):
            mods = []
            if isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                mods.append(node.module)
            elif isinstance(node, ast.Import):
                mods += [a.name for a in node.names]
            for mod in mods:
                parts = mod.split(".")
                if parts[0] == "app" and len(parts) > 1 and parts[1] in pkgs and parts[1] != src_pkg:
                    graph.setdefault(src_pkg, set()).add(parts[1])
    return graph


def verify_architecture():
    text = (D / "architecture.dot").read_text()
    drawn = {}
    backend = {"main", "routes", "middleware", "schemas", "services", "strategies", "observers", "domain",
               "repositories", "models", "database", "config", "utils"}
    for a, b in re.findall(r"^  (\w+) -> (\w+);$", text, re.M):
        if a in backend and b in backend:
            drawn.setdefault(a, set()).add(b)
    # frontend edges are checked against the real source folders and imports
    fe = ci.ROOT / "frontend" / "src"
    page_src = "".join(p.read_text() for p in (fe / "pages").glob("*.jsx"))
    check("../services/api" in page_src, "architecture: pages no longer import services/api")
    check("../components/" in page_src and "../context/" in page_src, "architecture: pages no longer import components/context")
    check((fe / "layouts").is_dir() and (fe / "services" / "api.js").exists(), "architecture: frontend folders changed")
    api_js = (fe / "services" / "api.js").read_text()
    check("axios" in api_js and "Authorization" in api_js, "architecture: api.js is no longer an Axios client with a JWT header")
    real = independent_import_graph()
    real.pop("utils", None)   # utils/seed.py is drawn separately as a dotted edge
    drawn.pop("utils", None)
    for src in sorted(set(real) | set(drawn)):
        check(real.get(src, set()) == drawn.get(src, set()),
              f"architecture: {src} imports {sorted(real.get(src, set()))} but diagram draws {sorted(drawn.get(src, set()))}")
    seed = (ci.BACKEND / "app" / "utils" / "seed.py").read_text()
    check("app.services" in seed or "from app.services" in seed, "architecture: seed.py no longer imports services")
    # layering rules the diagram claims
    for forbidden in (("repositories", "services"), ("models", "services"), ("domain", "services"),
                      ("repositories", "routes"), ("services", "routes"), ("domain", "routes")):
        check(forbidden[1] not in real.get(forbidden[0], set()), f"architecture: {forbidden[0]} must not import {forbidden[1]}")


# ------------------------------------------------------------------------------ use cases
def verify_use_cases():
    sys.path.insert(0, str(ci.BACKEND))
    from tests.use_case_matrix import USE_CASES
    text = (D / "use_case_diagram.dot").read_text()
    drawn_edges = {}
    for actor, uc in re.findall(r"^  (EMPLOYEE|TECHNICIAN|ADMIN|TIMER) -> (UC\d+) \[dir=none\];$", text, re.M):
        drawn_edges.setdefault(uc, set()).add(actor)
    for u in USE_CASES:
        check(drawn_edges.get(u["id"], set()) == set(u["actors"]), f"use case {u['id']}: actors drawn differ from the matrix")
        check(f'{u["id"]} [shape=ellipse' in text, f"use case {u['id']} missing from the diagram")
    check(len(re.findall(r"\[shape=ellipse", text)) == len(USE_CASES), "use case count differs")
    for name in ("employee", "technician", "administrator"):
        check((D / f"use_case_{name}.dot").exists(), f"per actor diagram missing: {name}")


def verify_rendered():
    for src in list(D.glob("*.mmd")) + list(D.glob("*.dot")):
        for ext in ("svg", "png"):
            check(src.with_suffix("." + ext).exists() and src.with_suffix("." + ext).stat().st_size > 1000,
                  f"rendered file missing or empty: {src.stem}.{ext}")
            check(src.with_suffix("." + ext).stat().st_mtime >= src.stat().st_mtime - 1, f"{src.stem}.{ext} older than its source")


if __name__ == "__main__":
    for fn in (verify_class_views, verify_er, verify_architecture, verify_use_cases, verify_rendered):
        fn()
    print(f"{checks} checks, {len(problems)} problems")
    for p in problems:
        print(" -", p)
    sys.exit(1 if problems else 0)
