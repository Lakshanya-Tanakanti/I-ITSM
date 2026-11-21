import { useEffect, useState } from "react";
import { Save } from "lucide-react";
import { useToast } from "../context/ToastContext";
import { errMsg, get, patch } from "../services/api";
import { useAsync } from "../utils";
import { Alert, Async, Card, Field, PageHeader } from "../components/ui";

export default function Settings() {
  const toast = useToast();
  const state = useAsync(() => get("/settings"), []);
  const [f, setF] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => { if (state.data) setF({ ...state.data.settings }); }, [state.data]);

  const save = async () => {
    setBusy(true); setError("");
    try {
      await patch("/settings", { ...f, duplicate_threshold: Number(f.duplicate_threshold), default_workload_limit: Number(f.default_workload_limit) });
      toast.success("Settings saved"); state.reload();
    } catch (e) { setError(errMsg(e)); } finally { setBusy(false); }
  };
  const desc = (list, name) => list.find((x) => x.name === name)?.description;

  return (
    <>
      <PageHeader title="Settings" subtitle="Switch strategies and thresholds without changing code." />
      <Async state={state}>{(d) => f && (
        <div className="grid g2">
          <Card title="Strategies">
            {error && <Alert kind="err">{error}</Alert>}
            <Field label="Assignment strategy" hint={desc(d.assignment_strategies, f.assignment_strategy)}>
              <select value={f.assignment_strategy} onChange={(e) => setF({ ...f, assignment_strategy: e.target.value })}>{d.assignment_strategies.map((s) => <option key={s.name} value={s.name}>{s.label}</option>)}</select></Field>
            <Field label="Priority strategy" hint={desc(d.priority_strategies, f.priority_strategy)}>
              <select value={f.priority_strategy} onChange={(e) => setF({ ...f, priority_strategy: e.target.value })}>{d.priority_strategies.map((s) => <option key={s.name} value={s.name}>{s.label}</option>)}</select></Field>
          </Card>
          <Card title="Behaviour">
            <label className="row" style={{ marginBottom: 12 }}><input type="checkbox" checked={f.auto_assign} onChange={(e) => setF({ ...f, auto_assign: e.target.checked })} />Assign technicians automatically when an incident is created</label>
            <label className="row" style={{ marginBottom: 12 }}><input type="checkbox" checked={f.affected_users_adjustment} onChange={(e) => setF({ ...f, affected_users_adjustment: e.target.checked })} />Raise the impact rating when many users are affected (10+ users: 2, 50+: 3, 250+: 4, 1000+: 5)</label>
            <label className="row" style={{ marginBottom: 12 }}><input type="checkbox" checked={f.escalation_enabled} onChange={(e) => setF({ ...f, escalation_enabled: e.target.checked })} />Escalate when the response SLA is breached</label>
            <Field label="Duplicate similarity threshold" hint="0.1 to 1.0. Higher means fewer warnings."><input type="number" step="0.05" min="0.1" max="1" value={f.duplicate_threshold} onChange={(e) => setF({ ...f, duplicate_threshold: e.target.value })} /></Field>
            <Field label="Default technician workload limit" hint="Used for new technicians."><input type="number" min="1" max="50" value={f.default_workload_limit} onChange={(e) => setF({ ...f, default_workload_limit: e.target.value })} /></Field>
            <button className="btn primary" disabled={busy} onClick={save}><Save size={15} />{busy ? "Saving..." : "Save settings"}</button>
          </Card>
        </div>
      )}</Async>
    </>
  );
}
