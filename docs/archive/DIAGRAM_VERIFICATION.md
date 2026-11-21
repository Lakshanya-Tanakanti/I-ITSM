# Diagram verification

The diagrams in `docs/diagrams/` are produced by `docs/tools/generate_diagrams.py` and checked by a separate program, `docs/tools/verify_diagrams.py`. This page records what is checked, what is a human choice, and what the check found.

## How to repeat

```
cd backend
python ../docs/tools/generate_diagrams.py        # needs Graphviz (dot), Mermaid CLI (mmdc) and Chrome; use --no-render for sources only
PYTHONPATH=. python ../docs/tools/verify_diagrams.py
python -m pytest tests/test_use_case_matrix.py   # use case permissions against the live API
```

Result of the last run: **1666 checks, 0 problems**, and 25 use case permission tests passed.

## What comes straight from the code (not typed by hand)

| Diagram | Read from the code |
|---|---|
| Class diagrams 1 to 7 | class names, stereotype (interface, abstract, enumeration), attributes (class level and `self.x` in `__init__`), public methods with parameters and return types, direct base classes (inheritance and realisation), enumeration members, entity columns and primary keys, entity-to-entity links and their cardinalities from the SQLAlchemy mappers |
| ER diagram | every table, column, type, nullability, PK, FK and unique flag from the SQLAlchemy metadata, one relationship per foreign key |
| Architecture diagram | the arrows between backend packages are the real `import` statements of `backend/app` |
| Use case diagrams | the use case list in `backend/tests/use_case_matrix.py`, which is also executed as a test |

## What is a human choice, and how it is still checked

Which classes appear in which view, and whether a link is drawn as composition, aggregation, association or dependency, cannot be derived mechanically. The verifier checks each such edge:

| Edge | Check |
|---|---|
| Inheritance / realisation (`<\|--`, `<\|..`) | the base must be a direct `__bases__` entry of the derived class. The reverse is also checked: every direct base that is inside the same view must be drawn |
| Composition, aggregation, association between non-entity classes | the source class (or a base) must really have an attribute with the name written on the arrow. Composition additionally needs the source to construct or mention the target |
| Entity links | the label must be a mapper relationship to that class. `*` on the far end must agree with `uselist`. A composition requires `delete-orphan` cascade or a NOT NULL foreign key in the child |
| Dependency (`creates`, `uses`, `returns`, `registers`) | the source class's code (or, for `returns` and `uses`, its module) must mention the target. A class built through a factory function (`Container` through `build_container`) is accepted only if that function is annotated to return it. `registers` needs a `Factory.register(Target)` call |
| ER relationships | the set of drawn relationships must equal the set of foreign keys. In addition a real SQLite database is created from the models and `PRAGMA table_info`, `foreign_key_list` and `index_list` are compared with the diagram |
| Architecture | compared with an independent import scan (own AST walk, not the generator's), plus layering rules the diagram implies (for example repositories, models and domain must not import services or routes). Frontend arrows are checked against real imports in `frontend/src` |
| Use cases | actors drawn for each use case equal the matrix, and the matrix is proven against the running API for 25 probes, including anonymous access |
| Rendering | every source has a non-empty SVG and PNG at least as new as the source |

The verifier was itself tested by deliberately damaging diagram sources. It reported a fake method, a wrong inheritance edge, an invented architecture dependency, a stale render and a removed unique-key flag.

## What the first verification run found (all fixed)

The first run reported five inaccuracies in the hand-curated edges of the first draft. Each was real:

1. `SettingsService ..> PriorityStrategy (returns)`: the service goes through `StrategyFactory`, never names `PriorityStrategy`. Edge removed.
2. `ChannelFactory ..> NotificationChannel (creates)`: the factory registers and instantiates the concrete channels. Replaced by `registers` edges to `InAppChannel` and `SimulatedEmailChannel`.
3. `NotificationChannel ..> NotificationRepository (uses)`: channels receive a generic `repo` argument. Edge removed.
4. `SlaMonitor ..> Container (creates)`: it calls `build_container`. Kept, with the factory-function rule above.
5. Architecture: the checker confused front-end arrows with backend packages. The checker was corrected, front-end arrows are now verified separately.

The same review also found documentation errors outside the diagrams, now corrected in `ARCHITECTURE.md`, `REQUIREMENTS_TRACEABILITY.md` and `DESIGN_NOTES.md`: the class name `ProductPriorityStrategy` (the code says `ScoreProductPriorityStrategy`), the abstract base `Observer` (it is `EventObserver`), the method names `state.transitions()` and `channel.send()` (they are `rules()` and `deliver()`), an "Adapter-style" claim for the simulated e-mail channel, and the claim that the application creates database triggers (only `schema.sql` contains them; the application relies on ORM listeners).

## Limits of the check

* A diagram edge being *allowed* by the code does not prove it is the most important relationship, only that it is not false.
* Method and attribute types in Mermaid are shortened for readability.
* Dependency checks are textual (a class mentions another). They catch invented edges but not missing ones. Missing inheritance edges are caught, missing associations are not.
* The starter-pack files `docs/class_diagram.drawio` and `docs/architecture.drawio` are kept as delivered. They are **not** verified and the generated diagrams supersede them.
