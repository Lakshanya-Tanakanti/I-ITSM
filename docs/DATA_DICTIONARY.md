# Data dictionary

Generated from the SQLAlchemy models by `docs/tools/generate_diagrams.py`. Do not edit by hand.

## incident_categories

Entity class: `IncidentCategory`

| Column | Type | Null | Key | Notes |
|---|---|---|---|---|
| id | integer | no | PK |  |
| name | varchar(80) | no | unique |  |
| description | text | yes |  |  |
| keywords | text | yes |  |  |
| is_active | boolean | no |  | default True |

Constraints:
* unique (name)

## services

Entity class: `Service`

| Column | Type | Null | Key | Notes |
|---|---|---|---|---|
| id | integer | no | PK |  |
| name | varchar(120) | no | unique |  |
| description | text | yes |  |  |
| business_criticality | integer | no |  |  |
| is_active | boolean | no |  | default True |

Constraints:
* unique (name)

## system_settings

Entity class: `SystemSetting`

| Column | Type | Null | Key | Notes |
|---|---|---|---|---|
| key | varchar(100) | no | PK |  |
| value | text | no |  |  |
| updated_at | datetime | no |  |  |

## users

Entity class: `User`

| Column | Type | Null | Key | Notes |
|---|---|---|---|---|
| id | integer | no | PK |  |
| employee_code | varchar(40) | yes | unique |  |
| full_name | varchar(120) | no |  |  |
| email | varchar(255) | no | unique |  |
| password_hash | varchar(255) | no |  |  |
| role | varchar(20) | no |  |  |
| department | varchar(100) | yes |  |  |
| is_active | boolean | no |  | default True |
| created_at | datetime | no |  |  |
| updated_at | datetime | no |  |  |

Constraints:
* unique (employee_code)

## sla_policies

Entity class: `SlaPolicy`

| Column | Type | Null | Key | Notes |
|---|---|---|---|---|
| id | integer | no | PK |  |
| name | varchar(120) | no |  |  |
| priority | varchar(2) | no |  |  |
| service_id | integer | yes | FK to services.id |  |
| response_minutes | integer | no |  |  |
| resolution_minutes | integer | no |  |  |
| warning_percent | integer | no |  | default 75 |
| is_active | boolean | no |  | default True |

## support_teams

Entity class: `SupportTeam`

| Column | Type | Null | Key | Notes |
|---|---|---|---|---|
| id | integer | no | PK |  |
| name | varchar(100) | no | unique |  |
| description | text | yes |  |  |
| lead_id | integer | yes | FK to users.id |  |
| is_active | boolean | no |  | default True |

Constraints:
* unique (name)

## incidents

Entity class: `Incident`

| Column | Type | Null | Key | Notes |
|---|---|---|---|---|
| id | integer | no | PK |  |
| number | varchar(30) | no | unique |  |
| title | varchar(200) | no |  |  |
| description | text | no |  |  |
| reporter_id | integer | no | FK to users.id |  |
| category_id | integer | yes | FK to incident_categories.id |  |
| category_source | varchar(20) | yes |  |  |
| service_id | integer | no | FK to services.id |  |
| affected_system | varchar(200) | yes |  |  |
| affected_users | integer | yes |  |  |
| impact | integer | no |  |  |
| effective_impact | integer | yes |  |  |
| urgency | integer | no |  |  |
| business_criticality | integer | no |  |  |
| criticality_overridden | boolean | no |  | default False |
| priority_score | integer | no |  |  |
| priority | varchar(2) | no |  |  |
| status | varchar(30) | no |  |  |
| assigned_technician_id | integer | yes | FK to users.id |  |
| sla_policy_id | integer | yes | FK to sla_policies.id |  |
| response_deadline | datetime | yes |  |  |
| resolution_deadline | datetime | yes |  |  |
| acknowledged_at | datetime | yes |  |  |
| resolved_at | datetime | yes |  |  |
| verified_at | datetime | yes |  |  |
| closed_at | datetime | yes |  |  |
| sla_status | varchar(20) | no |  | default SlaStatus.ON_TRACK |
| response_warned_at | datetime | yes |  |  |
| resolution_warned_at | datetime | yes |  |  |
| escalation_level | integer | no |  | default 0 |
| escalated_at | datetime | yes |  |  |
| awaiting_info | boolean | no |  | default False |
| reopen_count | integer | no |  | default 0 |
| duplicate_of_id | integer | yes | FK to incidents.id |  |
| closure_note | text | yes |  |  |
| created_at | datetime | no |  |  |
| updated_at | datetime | no |  |  |

Constraints:
* check `impact BETWEEN 1 AND 5`
* check `urgency BETWEEN 1 AND 5`
* check `business_criticality BETWEEN 1 AND 5`

## technician_profiles

Entity class: `TechnicianProfile`

| Column | Type | Null | Key | Notes |
|---|---|---|---|---|
| id | integer | no | PK |  |
| user_id | integer | no | FK to users.id, unique |  |
| team_id | integer | yes | FK to support_teams.id |  |
| experience_years | integer | no |  | default 0 |
| is_available | boolean | no |  | default True |
| workload_limit | integer | no |  | default 5 |
| created_at | datetime | no |  |  |

Constraints:
* unique (user_id)

## audit_logs

Entity class: `AuditLog`

| Column | Type | Null | Key | Notes |
|---|---|---|---|---|
| id | integer | no | PK |  |
| actor_id | integer | yes | FK to users.id |  |
| incident_id | integer | yes | FK to incidents.id |  |
| action | varchar(80) | no |  |  |
| previous_state | varchar(30) | yes |  |  |
| new_state | varchar(30) | yes |  |  |
| description | text | no |  |  |
| metadata | text | yes |  |  |
| created_at | datetime | no |  |  |

## employee_feedback

Entity class: `EmployeeFeedback`

| Column | Type | Null | Key | Notes |
|---|---|---|---|---|
| id | integer | no | PK |  |
| incident_id | integer | no | FK to incidents.id, unique |  |
| employee_id | integer | no | FK to users.id |  |
| rating | integer | no |  |  |
| comment | text | yes |  |  |
| created_at | datetime | no |  |  |

Constraints:
* unique (incident_id)
* check `rating BETWEEN 1 AND 5`

## investigation_notes

Entity class: `InvestigationNote`

| Column | Type | Null | Key | Notes |
|---|---|---|---|---|
| id | integer | no | PK |  |
| incident_id | integer | no | FK to incidents.id |  |
| author_id | integer | yes | FK to users.id |  |
| note_type | varchar(30) | no |  |  |
| body | text | no |  |  |
| is_internal | boolean | no |  | default False |
| created_at | datetime | no |  |  |

## notifications

Entity class: `Notification`

| Column | Type | Null | Key | Notes |
|---|---|---|---|---|
| id | integer | no | PK |  |
| recipient_id | integer | no | FK to users.id |  |
| incident_id | integer | yes | FK to incidents.id |  |
| channel | varchar(20) | no |  |  |
| subject | varchar(200) | no |  |  |
| body | text | no |  |  |
| event_type | varchar(60) | yes |  |  |
| is_read | boolean | no |  | default False |
| delivery_status | varchar(20) | no |  | default QUEUED |
| created_at | datetime | no |  |  |

## resolutions

Entity class: `Resolution`

| Column | Type | Null | Key | Notes |
|---|---|---|---|---|
| id | integer | no | PK |  |
| incident_id | integer | no | FK to incidents.id, unique |  |
| technician_id | integer | no | FK to users.id |  |
| summary | text | no |  |  |
| root_cause | text | no |  |  |
| created_at | datetime | no |  |  |

Constraints:
* unique (incident_id)

## sla_violations

Entity class: `SlaViolation`

| Column | Type | Null | Key | Notes |
|---|---|---|---|---|
| id | integer | no | PK |  |
| incident_id | integer | no | FK to incidents.id |  |
| sla_type | varchar(20) | no |  |  |
| deadline_at | datetime | no |  |  |
| detected_at | datetime | no |  |  |

Constraints:
* unique (incident_id, sla_type)

## technician_skills

Entity class: `TechnicianSkill`

| Column | Type | Null | Key | Notes |
|---|---|---|---|---|
| technician_id | integer | no | PK, FK to technician_profiles.id |  |
| category_id | integer | no | PK, FK to incident_categories.id |  |
| proficiency | integer | no |  | default 3 |
