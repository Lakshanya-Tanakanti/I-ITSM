-- I-ITSM database schema (SQLite). Generated from the SQLAlchemy models by docs/tools/export_schema.py.
-- The application creates these tables automatically on first start. Use this file for review or manual setup:
--   sqlite3 itsm.db < database/schema.sql

PRAGMA foreign_keys = ON;

CREATE TABLE incident_categories (
	id INTEGER NOT NULL, 
	name VARCHAR(80) NOT NULL, 
	description TEXT, 
	keywords TEXT, 
	is_active BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
);


CREATE TABLE services (
	id INTEGER NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	description TEXT, 
	business_criticality INTEGER NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
);


CREATE TABLE system_settings (
	"key" VARCHAR(100) NOT NULL, 
	value TEXT NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY ("key")
);


CREATE TABLE users (
	id INTEGER NOT NULL, 
	employee_code VARCHAR(40), 
	full_name VARCHAR(120) NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	role VARCHAR(20) NOT NULL, 
	department VARCHAR(100), 
	is_active BOOLEAN NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (employee_code)
);

CREATE UNIQUE INDEX ix_users_email ON users (email);

CREATE TABLE sla_policies (
	id INTEGER NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	priority VARCHAR(2) NOT NULL, 
	service_id INTEGER, 
	response_minutes INTEGER NOT NULL, 
	resolution_minutes INTEGER NOT NULL, 
	warning_percent INTEGER NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(service_id) REFERENCES services (id)
);


CREATE TABLE support_teams (
	id INTEGER NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	description TEXT, 
	lead_id INTEGER, 
	is_active BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name), 
	FOREIGN KEY(lead_id) REFERENCES users (id)
);


CREATE TABLE incidents (
	id INTEGER NOT NULL, 
	number VARCHAR(30) NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	description TEXT NOT NULL, 
	reporter_id INTEGER NOT NULL, 
	category_id INTEGER, 
	category_source VARCHAR(20), 
	service_id INTEGER NOT NULL, 
	affected_system VARCHAR(200), 
	affected_users INTEGER, 
	impact INTEGER NOT NULL, 
	effective_impact INTEGER, 
	urgency INTEGER NOT NULL, 
	business_criticality INTEGER NOT NULL, 
	criticality_overridden BOOLEAN NOT NULL, 
	priority_score INTEGER NOT NULL, 
	priority VARCHAR(2) NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	assigned_technician_id INTEGER, 
	sla_policy_id INTEGER, 
	response_deadline DATETIME, 
	resolution_deadline DATETIME, 
	acknowledged_at DATETIME, 
	resolved_at DATETIME, 
	verified_at DATETIME, 
	closed_at DATETIME, 
	sla_status VARCHAR(20) NOT NULL, 
	response_warned_at DATETIME, 
	resolution_warned_at DATETIME, 
	escalation_level INTEGER NOT NULL, 
	escalated_at DATETIME, 
	awaiting_info BOOLEAN NOT NULL, 
	reopen_count INTEGER NOT NULL, 
	duplicate_of_id INTEGER, 
	closure_note TEXT, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_incident_impact CHECK (impact BETWEEN 1 AND 5), 
	CONSTRAINT ck_incident_urgency CHECK (urgency BETWEEN 1 AND 5), 
	CONSTRAINT ck_incident_criticality CHECK (business_criticality BETWEEN 1 AND 5), 
	FOREIGN KEY(reporter_id) REFERENCES users (id), 
	FOREIGN KEY(category_id) REFERENCES incident_categories (id), 
	FOREIGN KEY(service_id) REFERENCES services (id), 
	FOREIGN KEY(assigned_technician_id) REFERENCES users (id), 
	FOREIGN KEY(sla_policy_id) REFERENCES sla_policies (id), 
	FOREIGN KEY(duplicate_of_id) REFERENCES incidents (id)
);

CREATE INDEX ix_incidents_assigned_technician_id ON incidents (assigned_technician_id);
CREATE INDEX ix_incidents_category_id ON incidents (category_id);
CREATE INDEX ix_incidents_created_at ON incidents (created_at);
CREATE UNIQUE INDEX ix_incidents_number ON incidents (number);
CREATE INDEX ix_incidents_priority ON incidents (priority);
CREATE INDEX ix_incidents_reporter_id ON incidents (reporter_id);
CREATE INDEX ix_incidents_service_id ON incidents (service_id);
CREATE INDEX ix_incidents_sla_status ON incidents (sla_status);
CREATE INDEX ix_incidents_status ON incidents (status);

CREATE TABLE technician_profiles (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	team_id INTEGER, 
	experience_years INTEGER NOT NULL, 
	is_available BOOLEAN NOT NULL, 
	workload_limit INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (user_id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(team_id) REFERENCES support_teams (id)
);


CREATE TABLE audit_logs (
	id INTEGER NOT NULL, 
	actor_id INTEGER, 
	incident_id INTEGER, 
	action VARCHAR(80) NOT NULL, 
	previous_state VARCHAR(30), 
	new_state VARCHAR(30), 
	description TEXT NOT NULL, 
	metadata TEXT, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(actor_id) REFERENCES users (id), 
	FOREIGN KEY(incident_id) REFERENCES incidents (id)
);

CREATE INDEX ix_audit_incident_time ON audit_logs (incident_id, created_at);
CREATE INDEX ix_audit_logs_action ON audit_logs (action);
CREATE INDEX ix_audit_logs_created_at ON audit_logs (created_at);

CREATE TABLE employee_feedback (
	id INTEGER NOT NULL, 
	incident_id INTEGER NOT NULL, 
	employee_id INTEGER NOT NULL, 
	rating INTEGER NOT NULL, 
	comment TEXT, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_feedback_rating CHECK (rating BETWEEN 1 AND 5), 
	UNIQUE (incident_id), 
	FOREIGN KEY(incident_id) REFERENCES incidents (id), 
	FOREIGN KEY(employee_id) REFERENCES users (id)
);


CREATE TABLE investigation_notes (
	id INTEGER NOT NULL, 
	incident_id INTEGER NOT NULL, 
	author_id INTEGER, 
	note_type VARCHAR(30) NOT NULL, 
	body TEXT NOT NULL, 
	is_internal BOOLEAN NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(incident_id) REFERENCES incidents (id), 
	FOREIGN KEY(author_id) REFERENCES users (id)
);

CREATE INDEX ix_investigation_notes_incident_id ON investigation_notes (incident_id);

CREATE TABLE notifications (
	id INTEGER NOT NULL, 
	recipient_id INTEGER NOT NULL, 
	incident_id INTEGER, 
	channel VARCHAR(20) NOT NULL, 
	subject VARCHAR(200) NOT NULL, 
	body TEXT NOT NULL, 
	event_type VARCHAR(60), 
	is_read BOOLEAN NOT NULL, 
	delivery_status VARCHAR(20) NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(recipient_id) REFERENCES users (id), 
	FOREIGN KEY(incident_id) REFERENCES incidents (id)
);

CREATE INDEX ix_notifications_created_at ON notifications (created_at);
CREATE INDEX ix_notifications_recipient ON notifications (recipient_id, is_read);

CREATE TABLE resolutions (
	id INTEGER NOT NULL, 
	incident_id INTEGER NOT NULL, 
	technician_id INTEGER NOT NULL, 
	summary TEXT NOT NULL, 
	root_cause TEXT NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (incident_id), 
	FOREIGN KEY(incident_id) REFERENCES incidents (id), 
	FOREIGN KEY(technician_id) REFERENCES users (id)
);


CREATE TABLE sla_violations (
	id INTEGER NOT NULL, 
	incident_id INTEGER NOT NULL, 
	sla_type VARCHAR(20) NOT NULL, 
	deadline_at DATETIME NOT NULL, 
	detected_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_violation_once UNIQUE (incident_id, sla_type), 
	FOREIGN KEY(incident_id) REFERENCES incidents (id)
);

CREATE INDEX ix_sla_violations_incident_id ON sla_violations (incident_id);

CREATE TABLE technician_skills (
	technician_id INTEGER NOT NULL, 
	category_id INTEGER NOT NULL, 
	proficiency INTEGER NOT NULL, 
	PRIMARY KEY (technician_id, category_id), 
	FOREIGN KEY(technician_id) REFERENCES technician_profiles (id), 
	FOREIGN KEY(category_id) REFERENCES incident_categories (id)
);


-- OPTIONAL hardening, applied only when you load this file by hand (the running application does not
-- create these triggers). The application itself blocks UPDATE and DELETE of audit rows through ORM
-- event listeners in app/models/audit.py. The triggers enforce the same rule inside the database.
CREATE TRIGGER IF NOT EXISTS audit_logs_no_update BEFORE UPDATE ON audit_logs BEGIN SELECT RAISE(ABORT, 'audit_logs is append-only'); END;
CREATE TRIGGER IF NOT EXISTS audit_logs_no_delete BEFORE DELETE ON audit_logs BEGIN SELECT RAISE(ABORT, 'audit_logs is append-only'); END;
