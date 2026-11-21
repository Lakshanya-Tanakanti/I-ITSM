# Requirements traceability

Test files are in `backend/tests/`. "UI" names the frontend page in `frontend/src/pages/` (or component) that exposes the feature. Every row below was checked against the code, and the test column names real tests that run in the suite (`python -m pytest -q`, the current count is in `evidence/TEST_RESULTS.md`).

The table in section 1 maps the acceptance scenarios T01 to T30 to the tests that cover them.

## 1. Acceptance scenarios T01 to T30

| ID | Scenario | Test | Implementation |
|---|---|---|---|
| T01 | Register valid employee, password hashed | `test_auth.py::test_t01_register_valid_employee_and_password_is_hashed` | `services/auth_service.py`, `utils/security.py`, UI Register |
| T02 | Public registration cannot create ADMIN | `test_auth.py::test_t02_public_registration_cannot_create_admin` | `schemas/user.py` (`RegisterRequest` has no role), `new_user` factory |
| T03 | Wrong password gives 401, no token | `test_auth.py::test_t03_login_with_wrong_password_returns_401_without_token` | `routes/auth.py` |
| T04 | Employee cannot read another's incident | `test_rbac.py::test_t04_employee_cannot_read_another_employees_incident` | `incident_service.can_view`, `get_for_actor` |
| T05 | Impact 4, urgency 5, criticality 5 gives 100, P1 | `test_priority.py::test_t05_impact4_urgency5_criticality5_is_score_100_p1` | `strategies/priority.py` |
| T06 | Boundary 39 is P2 | `test_priority.py::test_t06_t07_threshold_boundaries` | `PriorityStrategy.level_for_score` |
| T07 | Boundary 8 is P3 | same test | same |
| T08 | NEW to CLOSED rejected 409, no mutation | `test_lifecycle.py::test_t08_new_to_closed_is_rejected_with_409_and_no_mutation` | `domain/lifecycle.py` |
| T09 | Technician acknowledges, timestamp set | `test_lifecycle.py::test_t09_assigned_technician_acknowledges_and_timestamp_is_set` | `incident_service.transition` |
| T10 | Resolve without summary or root cause rejected | `test_lifecycle.py::test_t10_resolve_without_summary_or_root_cause_is_rejected` | `TransitionRule.required_fields` |
| T11 | Reopen with reason, audited | `test_lifecycle.py::test_t11_reopen_requires_reason_and_reason_is_audited` | `ResolvedState` |
| T12 | No skill means not eligible | `test_assignment.py::test_t12_technician_without_skill_is_not_eligible` | `strategies/assignment.py` (`EligibilityPolicy`) |
| T13 | Unavailable or full means not eligible | `test_assignment.py::test_t13_unavailable_inactive_or_full_technicians_are_not_eligible` | same |
| T14 | Skill and load strategies rank with reasons | `test_assignment.py::test_t14_skill_based_ranks_by_proficiency_then_experience`, `test_t14_load_based_ranks_by_free_capacity`, `test_t14_recommendations_endpoint_for_each_strategy` | `SkillBasedStrategy`, `LoadBasedStrategy` |
| T15 | No eligible technician, stays unassigned, admin notified | `test_assignment.py::test_t15_no_eligible_technician_leaves_incident_unassigned_and_notifies_admin` | `assignment_service.py`, `notification_observer.py` |
| T16 | P1 deadlines +5 m and +30 m | `test_sla.py::test_t16_p1_incident_gets_5_and_30_minute_deadlines` | `sla_service.apply_policy` |
| T17 | Warning once at 75 percent | `test_sla.py::test_t17_warning_is_generated_once_at_75_percent` | `sla_service.evaluate` |
| T18 | One RESPONSE violation | `test_sla.py::test_t18_response_breach_records_exactly_one_violation` | `SlaViolation` unique constraint |
| T19 | No duplicate violation on repeat runs | `test_sla.py::test_t19_repeated_monitor_runs_never_duplicate_violations` | same |
| T20 | In-app and simulated e-mail records | `test_notifications_audit.py::test_t20_creation_assignment_and_resolution_create_in_app_and_email_records` | `observers/notification_observer.py`, `channels.py` |
| T21 | Audit row with actor, action, states, time | `test_notifications_audit.py::test_t21_transition_creates_audit_row_with_actor_action_states_and_time` | `observers/audit_observer.py` |
| T22 | Audit cannot be edited or deleted via API | `test_notifications_audit.py::test_t22_audit_records_cannot_be_edited_or_deleted_via_api`, `test_audit_rows_are_immutable_at_orm_level` | `models/audit.py` listeners, no write route (optional triggers in `database/schema.sql`) |
| T23 | Combined filters | `test_search_reports.py::test_t23_combined_filters_return_only_matching_incidents` | `incident_repository.search` |
| T24 | Similar payment incident warns, not blocked | `test_intelligence.py::test_t24_similar_payment_incident_triggers_a_warning_but_is_not_blocked` | `intelligence_service.find_duplicates` |
| T25 | Network keywords suggest Network with reason | `test_intelligence.py::test_t25_network_keywords_suggest_network_with_reason` | `intelligence_service.suggest_category` |
| T26 | High priority near deadline gives HIGH risk with explanation | `test_intelligence.py::test_t26_high_priority_incident_close_to_deadline_is_high_risk_with_explanation` | `intelligence_service.sla_risk` |
| T27 | Dashboard totals match database | `test_search_reports.py::test_t27_dashboard_and_report_totals_match_database` | `report_service.py` |
| T28 | Data survives restart | `test_search_reports.py::test_t28_data_persists_after_application_restart` | SQLite file database |
| T29 | Employee rates own resolved incident, others blocked | `test_notes_feedback_config.py::test_t29_employee_rates_own_resolved_incident_and_others_are_blocked` | `incident_service.submit_feedback` |
| T30 | Admin changes strategy, recommendations follow | `test_assignment.py::test_t30_admin_changes_strategy_and_recommendations_follow` | `settings_service.py`, `strategies/factory.py` |

## 2. Functional requirements

| ID | Requirement | Where implemented | Tests | UI |
|---|---|---|---|---|
| FR-01 | Registration, login, three roles | `auth_service.py`, `routes/auth.py` | `test_auth.py` | Login, Register, profile menu |
| FR-02 | Admin manages users and technician profiles, deactivation | `user_service.py`, `routes/users.py` | `test_user_management`, `test_cannot_deactivate_technician_with_active_incidents` | Users, Technicians and teams |
| FR-03 | Employee creates incident | `incident_service.create_incident`, `incident_factory.py` | `test_priority.py`, `test_rbac.py` | Report incident |
| FR-04 | Classification and category admin | `intelligence_service.suggest_category`, `config_service.py` | `test_admin_keyword_changes_alter_suggestions_without_code_changes`, `test_category_service_policy_and_team_management` | Categories |
| FR-05 | Priority score and level | `strategies/priority.py` | `test_priority.py` | Priority preview on the form, badges |
| FR-06 | SLA selection and deadlines | `sla_service.py` | `test_sla.py` | SLA panel on incident detail |
| FR-07 | Two or more assignment strategies | `strategies/assignment.py` (three) | `test_assignment.py` | Assign panel, Settings |
| FR-08 | Lifecycle enforced | `domain/lifecycle.py` | `test_lifecycle.py` | Action buttons come from `allowed_transitions` |
| FR-09 | Technician workflow | `incident_service.py` | `test_lifecycle.py`, `test_information_request_and_reply_flow` | Technician dashboard, incident detail |
| FR-10 | Employee tracking, reply, verify, reopen, feedback | `incident_service.py` | `test_t11`, `test_t29`, `test_information_request_and_reply_flow` | Employee dashboard, incident detail |
| FR-11 | SLA monitor | `sla_service.run_check`, `sla_monitor.py` | `test_sla.py` | SLA monitor |
| FR-12 | In-app and simulated e-mail | `observers/channels.py` | `test_t20...` | Bell panel, Notifications, E-mail outbox |
| FR-13 | Append-only audit | `audit_observer.py`, `models/audit.py` | `test_t21`, `test_t22`, `test_audit_log_filters_and_pagination` | Audit log |
| FR-14 | Search filters | `incident_repository.IncidentFilters` (text, number, date range, status, priority, category, service, technician, SLA status, unassigned, awaiting info) | `test_search_reports.py` | Incident list filters |
| FR-15 | Dashboards and reports | `report_service.py` | `test_t27`, `test_role_specific_dashboards` | Three dashboards, Reports |
| FR-16 | Four intelligent features | `intelligence_service.py`, `assignment_service.py` | `test_intelligence.py` | Report form, incident detail insights |
| FR-17 | Admin configuration | `config_service.py`, `settings_service.py` | `test_category_service_policy_and_team_management`, `test_t30` | Services, Categories, SLA policies, Teams, Settings |
| FR-18 | Persistent storage | SQLAlchemy and SQLite | `test_t28` | n/a |

## 3. Business rules

| ID | Rule | Implementation | Test |
|---|---|---|---|
| BR-01 | score = impact x urgency x criticality, 1 to 5 each | `ScoreProductPriorityStrategy` | `test_priority.py` |
| BR-02 | P1 40 to 125, P2 20 to 39, P3 8 to 19, P4 1 to 7 | `level_for_score` | `test_documented_examples_and_boundaries` |
| BR-03 | Criticality defaults from service | `incident_factory.py` | `test_api_calculates_priority_and_takes_criticality_from_service` |
| BR-04 | SLA targets P1 5m/30m, P2 15m/2h, P3 1h/8h, P4 4h/24h | `utils/seed.py` standard policies | `test_all_priorities_use_the_specified_targets` |
| BR-05 | Deadlines from creation, calendar minutes | `sla_service.apply_policy` | `test_t16` |
| BR-06 | Response ends at acknowledgement, resolution at RESOLVED | `sla_service.on_acknowledged`, `on_resolved` | `test_resolved_incident_stops_the_clock` |
| BR-07 | Warn at 75 percent, configurable | `SlaPolicy.warning_percent` | `test_t17`, `test_resolution_warning_after_acknowledgement` |
| BR-08 | One violation per incident per type | unique constraint | `test_t18`, `test_t19` |
| BR-09 | Active workload = ASSIGNED, ACKNOWLEDGED, IN_PROGRESS, limit 5 | `domain/enums.ACTIVE_WORKLOAD` | `test_t13` |
| BR-10 | Technician active, available, under limit | `EligibilityPolicy` | `test_t13` |
| BR-11 | Never silently assign without skill | override flag, audited | `test_missing_skill_needs_explicit_override_and_is_audited` |
| BR-12 | Only allowed transitions, all audited | `LifecycleManager`, `AuditObserver` | `test_every_disallowed_transition_is_rejected`, `test_every_accepted_transition_is_audited_with_states` |
| BR-13 | Resolution needs summary and root cause | `required_fields` | `test_t10` |
| BR-14 | Duplicate detection warns only | `find_duplicates` | `test_t24` |
| BR-15 | Audit append-only | ORM listeners (`models/audit.py`); optional triggers in `database/schema.sql` | `test_t22`, `test_audit_rows_are_immutable_at_orm_level` |
| BR-16 | Large user counts can raise the counted impact, never lower it; admin can switch the rule off | `AffectedUsersPolicy`, `incident_service._effective_impact`, setting `affected_users_adjustment` | `test_affected_users.py` (26 tests) |

## 4. Known gaps

* No automated frontend test suite. The UI was checked by hand in the browser.
* E-mail is simulated by design, there is no real SMTP delivery.
* The system targets a single organisation and SQLite. Moving to a server database such as PostgreSQL would be the next step for larger use.
