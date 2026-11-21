import { useState } from "react";
import { Download } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { get } from "../services/api";
import { fmtMinutes, STATUS_LABEL, useAsync } from "../utils";
import { Async, Card, PageHeader, PercentBar, StatCard } from "../components/ui";
import { ClipboardList, Clock, ShieldCheck, Star } from "lucide-react";

const PCOL = { P1: "#dc2626", P2: "#ea580c", P3: "#ca8a04", P4: "#16a34a" };

function csv(name, rows) {
  if (!rows.length) return;
  const keys = Object.keys(rows[0]);
  const esc = (v) => `"${String(v ?? "").replace(/"/g, '""')}"`;
  const blob = new Blob([[keys.join(","), ...rows.map((r) => keys.map((k) => esc(r[k])).join(","))].join("\n")], { type: "text/csv" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob); a.download = `${name}.csv`; a.click(); URL.revokeObjectURL(a.href);
}

export default function Reports() {
  const [days, setDays] = useState(30);
  const state = useAsync(() => Promise.all([get("/reports/overview"), get("/reports/trends", { days }), get("/reports/by-service"), get("/reports/by-category"), get("/reports/technician-workload"), get("/reports/category-service-matrix")]), [days]);
  return (
    <>
      <PageHeader title="Reports" subtitle="All figures are calculated live from the database.">
        <select style={{ width: "auto" }} value={days} onChange={(e) => setDays(Number(e.target.value))}>{[7, 14, 30, 60, 90].map((d) => <option key={d} value={d}>Last {d} days</option>)}</select>
      </PageHeader>
      <Async state={state}>{([o, trends, svc, cat, load, matrix]) => {
        const pri = Object.entries(o.by_priority).map(([name, value]) => ({ name, value }));
        const stat = Object.entries(o.by_status).map(([k, value]) => ({ name: STATUS_LABEL[k], value }));
        const cats = [...new Set(matrix.map((m) => m.category))], svcs = [...new Set(matrix.map((m) => m.service))];
        const max = Math.max(1, ...matrix.map((m) => m.count));
        return (
          <>
            <div className="grid g4" style={{ marginBottom: 16 }}>
              <StatCard icon={ClipboardList} label="Total incidents" value={o.total} />
              <StatCard icon={ShieldCheck} label="SLA compliance" value={o.sla_compliance_percent != null ? `${o.sla_compliance_percent}%` : "-"} color="green" hint={`${o.sla_violations} violation(s)`} />
              <StatCard icon={Clock} label="Average resolution" value={fmtMinutes(o.avg_resolution_minutes)} color="blue" />
              <StatCard icon={Star} label="Average feedback" value={o.avg_feedback_rating ? `${o.avg_feedback_rating} / 5` : "-"} color="amber" />
            </div>
            <div className="grid g2" style={{ marginBottom: 16 }}>
              <Card title="Created vs resolved per day" actions={<button className="btn sm" onClick={() => csv("trends", trends)}><Download size={13} />CSV</button>}>
                <ResponsiveContainer width="100%" height={260}><LineChart data={trends}><CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" /><XAxis dataKey="date" tickFormatter={(v) => v.slice(5)} /><YAxis allowDecimals={false} width={28} /><Tooltip /><Legend /><Line dataKey="created" name="Created" stroke="#4f46e5" strokeWidth={2} dot={false} /><Line dataKey="resolved" name="Resolved" stroke="#059669" strokeWidth={2} dot={false} /></LineChart></ResponsiveContainer>
              </Card>
              <Card title="Priority and status mix">
                <div className="grid g2"><ResponsiveContainer width="100%" height={260}><PieChart><Pie data={pri} dataKey="value" nameKey="name" outerRadius={85} label>{pri.map((p) => <Cell key={p.name} fill={PCOL[p.name]} />)}</Pie><Tooltip /><Legend /></PieChart></ResponsiveContainer>
                  <ResponsiveContainer width="100%" height={260}><BarChart data={stat} layout="vertical"><XAxis type="number" allowDecimals={false} /><YAxis type="category" dataKey="name" width={90} /><Tooltip /><Bar dataKey="value" fill="#6366f1" radius={[0, 5, 5, 0]} /></BarChart></ResponsiveContainer></div>
              </Card>
            </div>
            <div className="grid g2" style={{ marginBottom: 16 }}>
              <Card title="Incidents by service" actions={<button className="btn sm" onClick={() => csv("by-service", svc)}><Download size={13} />CSV</button>}>
                <ResponsiveContainer width="100%" height={260}><BarChart data={svc}><CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" /><XAxis dataKey="name" tick={{ fontSize: 10 }} interval={0} angle={-20} textAnchor="end" height={60} /><YAxis allowDecimals={false} width={28} /><Tooltip /><Legend /><Bar dataKey="total" name="Total" fill="#a5b4fc" /><Bar dataKey="open" name="Open" fill="#4f46e5" /><Bar dataKey="sla_breached" name="SLA breached" fill="#dc2626" /></BarChart></ResponsiveContainer>
              </Card>
              <Card title="Incidents by category" actions={<button className="btn sm" onClick={() => csv("by-category", cat)}><Download size={13} />CSV</button>}>
                <ResponsiveContainer width="100%" height={260}><BarChart data={cat}><CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" /><XAxis dataKey="name" tick={{ fontSize: 10 }} interval={0} angle={-20} textAnchor="end" height={60} /><YAxis allowDecimals={false} width={28} /><Tooltip /><Legend /><Bar dataKey="total" name="Total" fill="#a5b4fc" /><Bar dataKey="open" name="Open" fill="#4f46e5" /><Bar dataKey="critical" name="Critical" fill="#dc2626" /></BarChart></ResponsiveContainer>
              </Card>
            </div>
            <div className="grid g2">
              <Card title="Technician workload" actions={<button className="btn sm" onClick={() => csv("workload", load.map(({ skills, ...r }) => ({ ...r, skills: skills.join("; ") })))}><Download size={13} />CSV</button>}>
                {load.map((t) => <div key={t.technician_id} style={{ marginBottom: 10 }}><div className="row between small"><span><b>{t.name}</b> <span className="muted">{t.team}</span></span><span>{t.active_incidents}/{t.workload_limit}</span></div><PercentBar value={t.utilization_percent} /></div>)}
              </Card>
              <Card title="Category by service (heat map)">
                {matrix.length === 0 ? <div className="muted">No data.</div> : <div className="table-wrap"><table><thead><tr><th></th>{svcs.map((s) => <th key={s} style={{ fontSize: 10 }}>{s}</th>)}</tr></thead>
                  <tbody>{cats.map((c) => <tr key={c}><td><b>{c}</b></td>{svcs.map((s) => { const n = matrix.find((m) => m.category === c && m.service === s)?.count || 0; return <td key={s} style={{ textAlign: "center", background: n ? `rgba(79,70,229,${0.12 + 0.7 * (n / max)})` : undefined, color: n / max > 0.6 ? "#fff" : undefined }}>{n || ""}</td>; })}</tr>)}</tbody></table></div>}
              </Card>
            </div>
          </>
        );
      }}</Async>
    </>
  );
}
