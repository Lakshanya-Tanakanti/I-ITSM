import { Link } from "react-router-dom";
import { Activity, Play, ShieldAlert, AlertTriangle } from "lucide-react";
import { useToast } from "../context/ToastContext";
import { errMsg, get, post } from "../services/api";
import { fmtDate, useAsync, usePolling } from "../utils";
import { Async, Card, EmptyState, PageHeader, PriorityBadge, StatCard } from "../components/ui";
import IncidentTable from "../components/IncidentTable";

export default function SlaMonitor() {
  const toast = useToast();
  const state = useAsync(() => Promise.all([get("/sla/monitor"), get("/sla/at-risk"), get("/sla/violations")]), []);
  usePolling(() => state.reload(), 15000);
  const run = async () => {
    try { const r = await post("/sla/run-check"); toast.success(`Checked ${r.checked} incident(s): ${r.warnings} warning(s), ${r.breaches} breach(es), ${r.escalations} escalation(s)`); state.reload(); }
    catch (e) { toast.error(errMsg(e)); }
  };
  return (
    <>
      <PageHeader title="SLA monitor" subtitle="A background job checks every active incident and raises warnings, breaches and escalations.">
        <button className="btn primary" onClick={run}><Play size={15} />Run check now</button>
      </PageHeader>
      <Async state={state}>{([mon, risk, viol]) => (<>
        <div className="grid g4" style={{ marginBottom: 16 }}>
          <StatCard icon={Activity} label={mon.running ? "Monitor running" : "Monitor stopped"} value={`every ${mon.interval_seconds}s`} color={mon.running ? "green" : "red"} hint={`${mon.runs} run(s) since start`} />
          <StatCard icon={AlertTriangle} label="Last check" value={mon.last_run ? mon.last_run.checked : "-"} color="blue" hint={mon.last_run ? fmtDate(mon.last_run.checked_at) : "Not run yet"} />
          <StatCard icon={AlertTriangle} label="At risk or breached" value={risk.length} color="amber" />
          <StatCard icon={ShieldAlert} label="Recorded violations" value={viol.length} color="red" />
        </div>
        <Card title="Incidents needing attention" pad={false} style={{ marginBottom: 16 }}>{risk.length === 0 ? <EmptyState title="Everything is within SLA" /> : <IncidentTable items={risk} />}</Card>
        <Card title="SLA violation history" pad={false}>{viol.length === 0 ? <EmptyState title="No violations recorded" /> : (
          <div className="table-wrap"><table><thead><tr><th>Incident</th><th>Type</th><th>Priority</th><th>Service</th><th>Technician</th><th>Deadline</th><th>Detected</th><th>Late by</th></tr></thead>
            <tbody>{viol.map((v) => <tr key={v.id}><td><Link to={`/incidents/${v.incident_number}`}><b>{v.incident_number}</b></Link><div className="small muted">{v.incident_title}</div></td><td>{v.sla_type}</td><td><PriorityBadge priority={v.priority} /></td><td>{v.service}</td><td>{v.technician || "-"}</td><td className="small">{fmtDate(v.deadline_at)}</td><td className="small">{fmtDate(v.detected_at)}</td><td>{v.late_minutes} min</td></tr>)}</tbody></table></div>)}</Card>
      </>)}</Async>
    </>
  );
}
