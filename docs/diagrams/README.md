# Diagrams

Use the `.png` in documents and the `.svg` when you need to zoom.

| File | What it shows |
|---|---|
| `use_case_diagram.png` | Overview: all actors and all 32 use cases, with include and extend |
| `use_case_employee.png`, `use_case_technician.png`, `use_case_administrator.png` | The same use cases, one actor per picture (easier to read) |
| `er_diagram.png` | Entity relationship diagram of the 15 tables with keys and cardinalities |
| `class_1_lifecycle_state_pattern.png` | State pattern: `IncidentState` and its 8 concrete states, `StateFactory`, `LifecycleManager`, `TransitionRule` |
| `class_2_strategy_pattern.png` | Strategy pattern for priority and assignment, `StrategyFactory`, `AffectedUsersPolicy` |
| `class_3_observer_and_channels.png` | Observer pattern: `EventBus`, `EventObserver`, audit and notification observers, channels |
| `class_4_repository_pattern.png` | `BaseRepository`, the 14 repositories and the `Repositories` bundle |
| `class_5_services_and_wiring.png` | Service layer, `Container` (dependency injection), `SlaMonitor` |
| `class_6_domain_entities.png` | The 15 persistent entities with associations, cardinalities, composition and aggregation |
| `class_7_exceptions_and_clock.png` | Exception hierarchy and the `Clock` abstraction |
| `architecture.png` | Layers and package dependencies (real imports) |

Source files: `*.mmd` (Mermaid) and `*.dot` (Graphviz).

Legend for class diagrams: `<|--` extends, `<|..` implements an interface, filled diamond is composition, hollow diamond is aggregation, plain arrow is association, dashed arrow is dependency (`creates`, `uses`, `returns`, `registers`). `*` after a method marks it abstract.
