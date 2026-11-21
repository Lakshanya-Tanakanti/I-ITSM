import ConfigPage from "../components/ConfigPage";
import { fmtMinutes } from "../utils";
import { get } from "../services/api";
export default function SlaPolicies() {
  return <ConfigPage title="SLA policies" subtitle="Response and resolution targets per priority. A service specific policy overrides the standard one." path="/sla-policies" noun="Policy"
    extraLoad={() => get("/services")}
    defaults={{ name: "", priority: "P3", service_id: "", response_minutes: 60, resolution_minutes: 480, warning_percent: 75 }}
    toBody={(f) => ({ name: f.name, priority: f.priority, service_id: f.service_id ? Number(f.service_id) : null, response_minutes: Number(f.response_minutes), resolution_minutes: Number(f.resolution_minutes), warning_percent: Number(f.warning_percent) })}
    fields={[
      { key: "name", label: "Policy name", required: true },
      { key: "priority", label: "Priority", type: "select", options: ["P1", "P2", "P3", "P4"].map((p) => [p, p]) },
      { key: "service_id", label: "Service (optional)", type: "select", hint: "Leave empty for a standard policy.", options: (svcs) => [["", "All services (standard)"], ...(svcs || []).map((s) => [s.id, s.name])] },
      { key: "response_minutes", label: "Response target (minutes)", type: "number", min: 1, required: true },
      { key: "resolution_minutes", label: "Resolution target (minutes)", type: "number", min: 1, required: true, hint: "Must not be shorter than the response target." },
      { key: "warning_percent", label: "Warning threshold (%)", type: "number", min: 1, max: 99 },
    ]}
    columns={[{ label: "Policy", render: (r) => <b>{r.name}</b> }, { label: "Priority", render: (r) => <span className={`badge ${r.priority.toLowerCase()}`}>{r.priority}</span> },
      { label: "Scope", render: (r) => r.service_name || <span className="muted">Standard</span> }, { label: "Response", render: (r) => fmtMinutes(r.response_minutes) },
      { label: "Resolution", render: (r) => fmtMinutes(r.resolution_minutes) }, { label: "Warning", render: (r) => `${r.warning_percent}%` }]} />;
}
