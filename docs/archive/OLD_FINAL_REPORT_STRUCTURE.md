# Final project report: structure and source map

Use this as the skeleton of the report you submit. Each chapter says which file in this repository supplies its content. Items in [square brackets] are for your group to fill in. Paste or adapt the text, and insert the PNG diagrams from `docs/diagrams/`.

## Front matter

* Title: I-ITSM, Intelligent IT Service Management System
* [Course, assignment number, date]
* [Group members, student numbers, who did what]
* [Repository link] and [demonstration video link] (see `MANUAL_TASKS.md`)
* Abstract (150 words): take the opening paragraph of `PROBLEM_ANALYSIS.md` section 1 and the solution summary of section 4.

## Chapters

| # | Chapter | Content | Source |
|---|---|---|---|
| 1 | Introduction | Purpose, context, objectives, scope | `PROBLEM_ANALYSIS.md` sections 1 and 4 (scope) |
| 2 | Problem analysis | Problem, stakeholders, existing challenges, proposed solution, assumptions, risks | `PROBLEM_ANALYSIS.md` |
| 3 | Requirements | Roles, functional requirements, business rules, non-functional requirements, constraints | `REQUIREMENTS_SPECIFICATION.md` |
| 4 | Use case model | Actors, 32 use cases, include and extend. Insert the overview and the three per-actor diagrams, add one fully written scenario (suggested: UC04 Report incident, UC17 Resolve incident, UC19 Assign technician) | `diagrams/use_case_diagram.png`, `use_case_employee.png`, `use_case_technician.png`, `use_case_administrator.png`. Scenario steps can be taken from `ARCHITECTURE.md` section 5 and the walkthrough in `README.md` |
| 5 | Architecture | Layers, package dependencies, request flow, dependency injection, transactions, SLA monitor thread | `ARCHITECTURE.md` sections 1 and 8, `diagrams/architecture.png` |
| 6 | Object-oriented design | Class diagrams per pattern, OOP principles, design patterns with justification | `diagrams/class_1` to `class_7`, `ARCHITECTURE.md` sections 2 and 3, `DESIGN_NOTES.md` |
| 7 | Data design | ER diagram, data dictionary, constraints, schema | `diagrams/er_diagram.png`, `DATA_DICTIONARY.md`, `database/schema.sql`, `ARCHITECTURE.md` section 4 |
| 8 | Key algorithms | Priority (with affected users rule), SLA, assignment eligibility and strategies, intelligent features | `ARCHITECTURE.md` section 6, `REQUIREMENTS_SPECIFICATION.md` BR-01 to BR-20 |
| 9 | Technology selection | The nine questions of the assignment | `TECHNOLOGY_SELECTION_REPORT.md` |
| 10 | Implementation notes | Project structure, configuration, security measures, exception handling | `README.md` sections 4 and 6, `ARCHITECTURE.md` section 7, `DESIGN_NOTES.md` |
| 11 | Testing | Strategy, test catalogue with expected and actual results, coverage, categories, fresh-install verification, known gaps | `TESTING_REPORT.md` (regenerate with `python docs/tools/build_testing_report.py` just before submission) |
| 12 | Verification of design against code | How diagrams are generated and checked, what was found | `DIAGRAM_VERIFICATION.md` |
| 13 | Requirements traceability | Every requirement to code, test and screen | `REQUIREMENTS_TRACEABILITY.md` |
| 14 | User guide | How to install, run and use each role | `README.md` sections 1 to 5, [your screenshots] |
| 15 | Limitations and future work | Known gaps, upgrade path | `REQUIREMENTS_TRACEABILITY.md` section 5, `PROBLEM_ANALYSIS.md` section 6, `TESTING_REPORT.md` sections 5 and 6 |
| 16 | Conclusion | [Your reflection: what worked, what you would change, what you learned] | write yourselves |
| | References | FastAPI, SQLAlchemy, React, Vite, Pydantic, PyJWT, bcrypt documentation; the assignment brief; [any books or papers you cite for the design patterns] | [list] |
| | Appendices | A. Full test catalogue (`TESTING_REPORT.md` section 7). B. API list (`http://localhost:8000/docs`). C. Source listing or repository link | |

## Suggested lengths

Chapters 1 to 3 about 6 pages, 4 to 8 about 15 pages with diagrams, 9 to 13 about 8 pages, rest 4 pages. Diagrams are wide, so place them on their own page in landscape.

## Before you submit (checklist)

1. Run `python -m pytest` in `backend/` and `npm run build` in `frontend/`. Run the report generator so the testing chapter matches your final code.
2. Run `python docs/tools/generate_diagrams.py` and `python docs/tools/verify_diagrams.py` if you changed any code.
3. Check that your report states which parts you wrote and which are generated, and be ready to explain the patterns in your own words, because the code was delivered to you and you are accountable for understanding it.
4. Complete `MANUAL_TASKS.md`.
