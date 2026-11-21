import { Fragment, useState } from "react";
import { Link } from "react-router-dom";
import { RotateCcw } from "lucide-react";
import { get } from "../services/api";
import { fmtDate, humanize, useAsync, useDebounced } from "../utils";
import { Async, Card, EmptyState, PageHeader, Pagination } from "../components/ui";

export default function AuditLog() {
  const [f, setF] = useState({ q: "", number: "", action: "", from_date: "", to_date: "" });
  const [page, setPage] = useState(1);
  const [open, setOpen] = useState(null);
  const q = useDebounced(f.q), number = useDebounced(f.number);
  const actions = useAsync(() => get("/audit-logs/actions"), []);
  const params = () => { const p = { page, page_size: 25 }; Object.entries({ ...f, q, number }).forEach(([k, v]) => v && (p[k] = v)); return p; };
  const state = useAsync(() => get("/audit-logs", params()), [q, number, f.action, f.from_date, f.to_date, page]);
  const set = (k) => (e) => { setPage(1); setF({ ...f, [k]: e.target.value }); };
  const bad = f.from_date && f.to_date && f.from_date > f.to_date;
  return (
    <>
      <PageHeader title="Audit log" subtitle="Append-only record of every important action. Entries cannot be edited or deleted." />
      <Card pad={false}>
        <div className="filters">
          <div><label>Search</label><input value={f.q} onChange={set("q")} placeholder="Text in description" /></div>
          <div><label>Incident</label><input value={f.number} onChange={set("number")} placeholder="INC-1001" /></div>
          <div><label>Action</label><select value={f.action} onChange={set("action")}><option value="">Any</option>{(actions.data || []).map((a) => <option key={a} value={a}>{humanize(a)}</option>)}</select></div>
          <div><label>From</label><input type="date" value={f.from_date} onChange={set("from_date")} /></div>
          <div><label>To</label><input type="date" value={f.to_date} onChange={set("to_date")} /></div>
          <div style={{ alignSelf: "end" }}><button className="btn" onClick={() => { setF({ q: "", number: "", action: "", from_date: "", to_date: "" }); setPage(1); }}><RotateCcw size={13} />Reset</button></div>
        </div>
        {bad ? <div className="alert err" style={{ margin: 14 }}>The start date must not be after the end date.</div> : (
          <Async state={state}>{(d) => d.items.length === 0 ? <EmptyState title="No audit entries match" /> : (<>
            <div className="table-wrap"><table><thead><tr><th>When</th><th>Action</th><th>Description</th><th>By</th><th>Incident</th><th>State change</th></tr></thead>
              <tbody>{d.items.map((e) => (<Fragment key={e.id}>
                <tr className="click" onClick={() => setOpen(open === e.id ? null : e.id)}>
                  <td className="small muted" style={{ whiteSpace: "nowrap" }}>{fmtDate(e.created_at)}</td><td><span className="badge b-indigo">{humanize(e.action)}</span></td><td>{e.description}</td><td>{e.actor_name || "System"}</td>
                  <td>{e.incident_number ? <Link to={`/incidents/${e.incident_number}`} onClick={(ev) => ev.stopPropagation()}>{e.incident_number}</Link> : "-"}</td>
                  <td className="small">{e.previous_state || e.new_state ? `${e.previous_state || "-"} to ${e.new_state || "-"}` : "-"}</td></tr>
                {open === e.id && <tr><td colSpan={6} style={{ background: "#f8fafc" }}><pre className="mono small" style={{ margin: 0, whiteSpace: "pre-wrap" }}>{e.metadata ? JSON.stringify(e.metadata, null, 2) : "No extra details."}</pre></td></tr>}</Fragment>))}</tbody></table></div>
            <Pagination page={d.page} pages={d.pages} total={d.total} pageSize={d.page_size} onPage={setPage} /></>)}</Async>)}
      </Card>
    </>
  );
}
