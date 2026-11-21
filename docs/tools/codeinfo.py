"""Reads the real code base (classes, attributes, methods, relationships, imports).

Used by generate_diagrams.py (to draw) and verify_diagrams.py (to check the drawings).
Run both from any folder:  python docs/tools/generate_diagrams.py
"""
import ast
import dataclasses
import enum
import importlib
import inspect
import pkgutil
import sys
import textwrap
import typing
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import app  # noqa: E402
from sqlalchemy.orm import configure_mappers  # noqa: E402
from sqlalchemy import inspect as sa_inspect  # noqa: E402


def all_modules():
    out = {}
    for m in pkgutil.walk_packages(app.__path__, "app."):
        if m.name.endswith("__main__"):
            continue
        out[m.name] = importlib.import_module(m.name)
    return out


_MODULES = None
_CLASSES = None


def classes() -> dict:
    """name -> class for every class defined inside the `app` package."""
    global _MODULES, _CLASSES
    if _CLASSES is None:
        _MODULES = all_modules()
        _CLASSES = {}
        for modname, mod in _MODULES.items():
            for name, cls in inspect.getmembers(mod, inspect.isclass):
                if cls.__module__ == modname:
                    _CLASSES[name] = cls
        configure_mappers()
    return _CLASSES


def is_model(cls) -> bool:
    try:
        sa_inspect(cls)
        return hasattr(cls, "__table__")
    except Exception:
        return False


def is_abstract(cls) -> bool:
    return bool(getattr(cls, "__abstractmethods__", None))


def public_methods(cls) -> dict:
    """Methods declared directly on the class (not inherited), without leading underscore."""
    out = {}
    for name, value in cls.__dict__.items():
        if name.startswith("_"):
            continue
        func = value.__func__ if isinstance(value, (staticmethod, classmethod)) else value
        if isinstance(value, property):
            continue
        if inspect.isfunction(func):
            kind = "static" if isinstance(value, staticmethod) else "class" if isinstance(value, classmethod) else "instance"
            out[name] = (func, kind)
    return out


def stereotype(cls) -> str | None:
    if issubclass(cls, enum.Enum):
        return "enumeration"
    if is_abstract(cls) or (inspect.isabstract(cls)):
        pm = public_methods(cls)
        abstract_names = {n for n, (f, _) in pm.items() if getattr(f, "__isabstractmethod__", False)}
        if pm and abstract_names == set(pm):
            return "interface"
        return "abstract"
    return None


def attribute_names(cls) -> set:
    """Every instance or class attribute the class defines (annotations, self.x in methods,
    dataclass fields, ORM columns and relationships), including inherited ones."""
    names = set()
    for klass in cls.__mro__:
        if klass is object:
            continue
        names.update(getattr(klass, "__annotations__", {}).keys())
        if dataclasses.is_dataclass(klass):
            names.update(f.name for f in dataclasses.fields(klass))
        try:
            tree = ast.parse(textwrap.dedent(inspect.getsource(klass)))
        except (OSError, TypeError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Store) \
                    and isinstance(node.value, ast.Name) and node.value.id == "self":
                names.add(node.attr)
        for node in tree.body[0].body:
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        names.add(t.id)
    if is_model(cls):
        mapper = sa_inspect(cls)
        names.update(c.key for c in mapper.column_attrs)
        names.update(r.key for r in mapper.relationships)
    return names


def own_attributes(cls) -> list:
    """Attributes introduced by this class itself, in source order."""
    if is_model(cls):
        return []  # models are handled column by column
    seen = []
    try:
        tree = ast.parse(textwrap.dedent(inspect.getsource(cls)))
    except (OSError, TypeError):
        return seen
    body = tree.body[0].body
    for node in body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id not in seen:
            seen.append(node.target.id)
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id.isidentifier() and not t.id.isupper() and t.id not in seen:
                    seen.append(t.id)
    for node in body:
        if isinstance(node, ast.FunctionDef) and node.name == "__init__":
            for sub in ast.walk(node):
                if isinstance(sub, ast.Attribute) and isinstance(sub.ctx, ast.Store) \
                        and isinstance(sub.value, ast.Name) and sub.value.id == "self" and sub.attr not in seen:
                    seen.append(sub.attr)
    return seen


def short_type(ann) -> str:
    """Compact, Mermaid-safe rendering of a type annotation."""
    if ann is inspect.Signature.empty or ann is None:
        return ""
    if isinstance(ann, str):
        text = ann
    elif isinstance(ann, type):
        return ann.__name__
    else:
        origin = typing.get_origin(ann)
        args = [a for a in typing.get_args(ann) if a is not type(None)]
        if origin is typing.Union and len(args) == 1:
            return short_type(args[0]) + "?"
        if origin in (list, set, tuple, dict) or origin is not None:
            name = getattr(origin, "__name__", str(origin).split(".")[-1])
            return name
        text = str(ann)
    text = text.replace("typing.", "").replace("Optional[", "").replace("]", "")
    text = text.split("|")[0].split("[")[0].split(".")[-1].strip()
    return text.replace("~", "")


def method_signature(func) -> tuple:
    sig = inspect.signature(func)
    params = []
    for name, p in sig.parameters.items():
        if name in ("self", "cls"):
            continue
        prefix = "*" if p.kind is p.VAR_POSITIONAL else "**" if p.kind is p.VAR_KEYWORD else ""
        params.append(prefix + name)
    return params, short_type(sig.return_annotation)


# ---------------------------------------------------------------- database metadata
def tables():
    from app.database import Base
    classes()
    return Base.metadata.sorted_tables


def table_class(table):
    for cls in classes().values():
        if is_model(cls) and cls.__table__ is table:
            return cls
    return None


def model_relationships():
    out = []
    for cls in classes().values():
        if is_model(cls):
            for rel in sa_inspect(cls).relationships:
                out.append((cls, rel))
    return out


# ---------------------------------------------------------------- imports (architecture)
def package_of(module: str):
    parts = module.split(".")
    if parts[0] != "app":
        return None
    return "app" if len(parts) == 1 else parts[1]


def import_graph() -> dict:
    graph: dict = {}
    for path in (BACKEND / "app").rglob("*.py"):
        mod = ".".join(path.relative_to(BACKEND).with_suffix("").parts)
        if mod.endswith(".__init__"):
            mod = mod[:-9]
        src = package_of(mod)
        if not src or src == "app":
            if mod != "app.main":
                continue
            src = "main"
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                names = [node.module]
            elif isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            for name in names:
                dst = package_of(name)
                if dst == "app" and name == "app.main":
                    dst = "main"
                if dst and dst != "app" and dst != src:
                    graph.setdefault(src, set()).add(dst)
    return graph
