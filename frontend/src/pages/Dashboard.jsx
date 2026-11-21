import { Link } from "react-router-dom";
import {
  AlertOctagon, CheckCircle2, ClipboardList, Clock, Flame, Gauge, Hourglass, MessageCircleQuestion, PlusCircle, ShieldAlert, Star, UserX, Users, Wrench, Zap,
} from "lucide-react";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useAuth } from "../context/AuthContext";
import { get } from "../services/api";
import { fmtMinutes, fmtShort, STATUS_LABEL, useAsync, usePolling } from "../utils";
import { Async, Card, EmptyState, PageHeader, PercentBar, PriorityBadge, SlaCountdown, StatCard, StatusBadge } from "../components/ui";
import IncidentTable from "../components/IncidentTable";

const PCOL = { P1: "#dc2626", P2: "#ea580c", P3: "#ca8a04", P4: "#16a34a" };
const SCOL = ["#94a3b8", "#38bdf8", "#818cf8", "#a78bfa", "#fbbf24", "#34d399", "#10b981", "#64748b"];

function Notifs({ block }) {
  return (
    <Card title="Recent notifications" actions={<Link to="/notifications" className="small">View all</Link>}>
      {block.recent.length === 0 ? <div className="muted">No notifications yet.</div> : block.recent.map((n) => (
        <div key={n.id} style={{ padding: "8px 0", borderBottom: "1px solid var(--line)" }}>
          <div style={{ fontWeight: n.is_read ? 500 : 700 }}>{n.incident_number ? <Link to={`/incidents/${n.incident_number}`}>{n.subject}</Link> : n.subject}</div>
          <div className="small muted">{n.body}</div><div className="small muted">{fmtShort(n.created_at)}</div>
        </div>
      ))}
    </Card>
  );
}

function EmployeeDashboard({ d }) {
  return (
    <>
      <div className="grid g4" style={{ marginBottom: 16 }}>
        <StatCard icon={ClipboardList} label="My incidents" value={d.counts.total} />
        <StatCard icon={Hourglass} label="Open" value={d.counts.open} color="amber" />
        <StatCard icon={CheckCircle2} label="Resolved or closed" value={d.counts.resolved} color="green" />
        <StatCard icon={Flame} label="Open critical (P1)" value={d.counts.critical} color="red" />
      </div>
      {d.pending_info_requests.length > 0 && (
        <div className="alert warn"><MessageCircleQuestion size={18} /><div><b>The service desk needs more information</b> on: {d.pending_info_requests.map((i) => <Link key={i.id} to={`/incidents/${i.number}`} style={{ marginRight: 8 }}>{i.number}</Link>)}</div></div>
      )}
      {d.pending_verification.length > 0 && (
        <div className="alert info"><CheckCircle2 size={18} /><div><b>Please verify the fix</b> for: {d.pending_verification.map((i) => <Link key={i.id} to={`/incidents/${i.number}`} style={{ marginRight: 8 }}>{i.number}</Link>)}</div></div>
      )}
      <div className="grid g-main">
        <Card title="Recent incidents" actions={<Link className="btn sm primary" to="/incidents/new"><PlusCircle size={14} />Report incident</Link>} pad={false}>
          {d.recent_incidents.length === 0 ? <EmptyState title="No incidents yet" text="Report a problem and the service desk will pick it up." action={<Link className="btn primary" to="/incidents/new">Report an incident</Link>} /> : <IncidentTable items={d.recent_incidents} compact />}
        </Card>
        <Notifs block={d.notifications} />
      </div>
    </>
  );
}

function TechnicianDashboard({ d }) {
  const pri = Object.entries(d.by_priority).map(([name, value]) => ({ name, value }));
  return (
    <>
      <div className="grid g4" style={{ marginBottom: 16 }}>
        <StatCard icon={Wrench} label="Assigned and open" value={d.counts.assigned_open} />
        <StatCard icon={Zap} label="Waiting acknowledgement" value={d.counts.pending_acknowledgement} color="amber" />
        <StatCard icon={Gauge} label="In progress" value={d.counts.in_progress} color="blue" />
        <StatCard icon={CheckCircle2} label="Resolved by me" value={d.counts.resolved_by_me} color="green" />
      </div>
      <div className="grid g3" style={{ marginBottom: 16 }}>
        <Card title="My workload">
          <div className="row between"><span>{d.workload.active} of {d.workload.limit} active</span><b>{d.workload.utilization_percent}%</b></div>
          <PercentBar value={d.workload.utilization_percent} />
          <p className="small muted">Status: {d.workload.is_available ? "Available for new assignments" : "Unavailable (set on your profile)"}</p>
        </Card>
        <Card title="SLA">
          <div className="row between"><span>Breached</span><span className="badge b-red">{d.counts.sla_breached}</span></div>
          <div className="row between" style={{ marginTop: 8 }}><span>At risk</span><span className="badge b-amber">{d.counts.sla_at_risk}</span></div>
        </Card>
        <Card title="Queue by priority">
          <ResponsiveContainer width="100%" height={110}><BarChart data={pri}><XAxis dataKey="name" /><YAxis allowDecimals={false} width={24} /><Tooltip /><Bar dataKey="value" radius={[5, 5, 0, 0]}>{pri.map((p) => <Cell key={p.name} fill={PCOL[p.name]} />)}</Bar></BarChart></ResponsiveContainer>
        </Card>
      </div>
      <div className="grid g-main">
        <Card title="My queue (highest priority first)" pad={false}>{d.queue.length === 0 ? <EmptyState title="Queue is empty" text="Nothing is assigned to you right now." /> : <IncidentTable items={d.queue} compact />}</Card>
        <div className="grid">
          <Card title="SLA countdowns">
            {d.sla_countdown.length === 0 ? <div className="muted">No active deadlines.</div> : d.sla_countdown.map((c) => (
              <div key={c.number} className="row between" style={{ padding: "7px 0", borderBottom: "1px solid var(--line)" }}>
                <div><Link to={`/incidents/${c.number}`}><b>{c.number}</b></Link> <PriorityBadge priority={c.priority} /><div className="small muted">{c.phase === "RESPONSE" ? "Respond within" : "Resolve within"}</div></div>
                <SlaCountdown remainingSeconds={c.remaining_seconds} />
              </div>
            ))}
          </Card>
          <Notifs block={d.notifications} />
        </div>
      </div>
    </>
  );
}

function AdminDashboard({ d }) {
  const o = d.overview;
  const pri = Object.entries(o.by_priority).map(([name, value]) => ({ name, value }));
  const stat = Object.entries(o.by_status).map(([name, value]) => ({ name: STATUS_LABEL[name] || name, value }));
  return (
    <>
      <div className="grid g4" style={{ marginBottom: 16 }}>
        <StatCard icon={ClipboardList} label="Total incidents" value={o.total} />
        <StatCard icon={Hourglass} label="Open" value={o.open} color="amber" />
        <StatCard icon={Flame} label="Critical open (P1)" value={o.critical} color="red" />
        <StatCard icon={UserX} label="Unassigned" value={o.unassigned} color="gray" />
        <StatCard icon={ShieldAlert} label="SLA violations" value={o.sla_violations} color="red" />
        <StatCard icon={AlertOctagon} label="SLA at risk" value={o.sla_at_risk} color="amber" />
        <StatCard icon={Clock} label="Avg resolution" value={fmtMinutes(o.avg_resolution_minutes)} color="blue" />
        <StatCard icon={Star} label="Avg feedback" value={o.avg_feedback_rating ? `${o.avg_feedback_rating} / 5` : "-"} color="green" hint={`SLA compliance ${o.sla_compliance_percent ?? "-"}%`} />
      </div>
      <div className="grid g-main" style={{ marginBottom: 16 }}>
        <Card title="Incidents created vs resolved (14 days)">
          <ResponsiveContainer width="100%" height={250}>
            <AreaChart data={d.trends}><CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" /><XAxis dataKey="date" tickFormatter={(v) => v.slice(5)} /><YAxis allowDecimals={false} width={30} /><Tooltip /><Legend />
              <Area type="monotone" dataKey="created" name="Created" stroke="#4f46e5" fill="#c7d2fe" /><Area type="monotone" dataKey="resolved" name="Resolved" stroke="#059669" fill="#a7f3d0" /></AreaChart>
          </ResponsiveContainer>
        </Card>
        <Card title="By priority">
          <ResponsiveContainer width="100%" height={250}><PieChart><Pie data={pri} dataKey="value" nameKey="name" innerRadius={55} outerRadius={90} paddingAngle={2}>{pri.map((p) => <Cell key={p.name} fill={PCOL[p.name]} />)}</Pie><Tooltip /><Legend /></PieChart></ResponsiveContainer>
        </Card>
      </div>
      <div className="grid g3" style={{ marginBottom: 16 }}>
        <Card title="By status"><ResponsiveContainer width="100%" height={230}><BarChart data={stat} layout="vertical"><XAxis type="number" allowDecimals={false} /><YAxis type="category" dataKey="name" width={90} /><Tooltip /><Bar dataKey="value" radius={[0, 5, 5, 0]}>{stat.map((s, i) => <Cell key={s.name} fill={SCOL[i]} />)}</Bar></BarChart></ResponsiveContainer></Card>
        <Card title="By service (open vs total)"><ResponsiveContainer width="100%" height={230}><BarChart data={d.by_service}><XAxis dataKey="name" tick={{ fontSize: 10 }} interval={0} angle={-25} textAnchor="end" height={60} /><YAxis allowDecimals={false} width={24} /><Tooltip /><Bar dataKey="total" name="Total" fill="#a5b4fc" /><Bar dataKey="open" name="Open" fill="#4f46e5" /></BarChart></ResponsiveContainer></Card>
        <Card title="Technician workload">
          {d.technician_workload.map((t) => (
            <div key={t.technician_id} style={{ marginBottom: 9 }}>
              <div className="row between small"><span>{t.name}{!t.is_available && <span className="badge b-gray" style={{ marginLeft: 6 }}>Unavailable</span>}</span><span>{t.active_incidents}/{t.workload_limit}</span></div>
              <PercentBar value={t.utilization_percent} />
            </div>
          ))}
        </Card>
      </div>
      <div className="grid g-main">
        <Card title="SLA attention list" actions={<Link className="small" to="/sla-monitor">Open SLA monitor</Link>} pad={false}>
          {d.at_risk.length === 0 ? <EmptyState title="All clear" text="No incident is at risk or breached." /> : <IncidentTable items={d.at_risk} compact />}
        </Card>
        <Card title="Recent activity">
          {d.recent_activity.map((a) => (
            <div key={a.id} style={{ padding: "7px 0", borderBottom: "1px solid var(--line)" }}>
              <div className="small">{a.description}</div><div className="small muted">{fmtShort(a.created_at)}</div>
            </div>
          ))}
          <div style={{ marginTop: 10 }}><Link to="/audit-log" className="small">Open audit log</Link></div>
        </Card>
      </div>
    </>
  );
}

export default function Dashboard() {
  const { user } = useAuth();
  const state = useAsync(() => get("/dashboard"), []);
  usePolling(() => state.reload(), 30000);
  const titles = { ADMIN: "Operations dashboard", TECHNICIAN: "My work", EMPLOYEE: "My service desk" };
  return (
    <>
      <PageHeader title={titles[user.role]} subtitle={`Hello ${user.full_name.split(" ")[0]}, here is what is happening right now.`}>
        <Link to="/incidents/new" className="btn primary"><PlusCircle size={16} />Report incident</Link>
      </PageHeader>
      <Async state={state}>{(d) => d.role === "ADMIN" ? <AdminDashboard d={d} /> : d.role === "TECHNICIAN" ? <TechnicianDashboard d={d} /> : <EmployeeDashboard d={d} />}</Async>
    </>
  );
}
