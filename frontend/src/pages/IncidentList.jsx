import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Filter, PlusCircle, RotateCcw } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { get } from "../services/api";
import { STATUS_LABEL, useAsync, useDebounced } from "../utils";
import { Async, Card, EmptyState, PageHeader, Pagination } from "../components/ui";
import IncidentTable from "../components/IncidentTable";

const EMPTY = { q: "", number: "", status: "", priority: "", category_id: "", service_id: "", technician_id: "", sla_status: "", from_date: "", to_date: "", unassigned: "", awaiting_info: "" };

export default function IncidentList() {
  const { user } = useAuth();
  const [params, setParams] = useSearchParams();
  const initial = { ...EMPTY, ...Object.fromEntries(params.entries()) };
  const [f, setF] = useState(initial);
  const [sort, setSort] = useState("-created_at");
  const [page, setPage] = useState(1);
  const refs = useAsync(() => Promise.all([get("/categories"), get("/services"), user.role === "ADMIN" ? get("/users", { role: "TECHNICIAN" }) : Promise.resolve([])]), []);
  const q = useDebounced(f.q), number = useDebounced(f.number);

  const query = () => {
    const p = { sort, page, page_size: 15 };
    const src = { ...f, q, number };
    Object.entries(src).forEach(([k, v]) => { if (v !== "" && v != null) p[k] = v; });
    if (p.unassigned === "true") p.unassigned = true; else delete p.unassigned;
    if (p.awaiting_info === "") delete p.awaiting_info;
    return p;
  };
  const state = useAsync(() => get("/incidents", query()), [q, number, f.status, f.priority, f.category_id, f.service_id, f.technician_id, f.sla_status, f.from_date, f.to_date, f.unassigned, f.awaiting_info, sort, page]);

  useEffect(() => { setPage(1); }, [q, number, f.status, f.priority, f.category_id, f.service_id, f.technician_id, f.sla_status, f.from_date, f.to_date, f.unassigned, f.awaiting_info]);
  const set = (k) => (e) => setF((x) => ({ ...x, [k]: e.target.value }));
  const reset = () => { setF(EMPTY); setParams({}); };
  const dateBad = f.from_date && f.to_date && f.from_date > f.to_date;
  const active = Object.values(f).some((v) => v !== "");

  return (
    <>
      <PageHeader title={user.role === "EMPLOYEE" ? "My incidents" : user.role === "TECHNICIAN" ? "Incident queue" : "All incidents"} subtitle="Search, filter and sort. Click a row to open it.">
        <Link to="/incidents/new" className="btn primary"><PlusCircle size={16} />Report incident</Link>
      </PageHeader>
      <Card pad={false} title={<span className="row"><Filter size={16} />Filters</span>} actions={active && <button className="btn sm" onClick={reset}><RotateCcw size={13} />Reset</button>}>
        <Async state={refs}>{([cats, svcs, techs]) => (
          <div className="filters">
            <div><label>Search text</label><input placeholder="Title or description" value={f.q} onChange={set("q")} /></div>
            <div><label>Incident ID</label><input placeholder="INC-1001" value={f.number} onChange={set("number")} /></div>
            <div><label>Status</label><select value={f.status} onChange={set("status")}><option value="">Any</option><option value="OPEN">All open</option><option value="DONE">Resolved or closed</option>{Object.entries(STATUS_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></div>
            <div><label>Priority</label><select value={f.priority} onChange={set("priority")}><option value="">Any</option>{["P1", "P2", "P3", "P4"].map((p) => <option key={p}>{p}</option>)}</select></div>
            <div><label>Category</label><select value={f.category_id} onChange={set("category_id")}><option value="">Any</option>{cats.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select></div>
            <div><label>Service</label><select value={f.service_id} onChange={set("service_id")}><option value="">Any</option>{svcs.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select></div>
            {user.role === "ADMIN" && <div><label>Technician</label><select value={f.technician_id} onChange={set("technician_id")}><option value="">Any</option>{techs.map((t) => <option key={t.id} value={t.id}>{t.full_name}</option>)}</select></div>}
            <div><label>SLA status</label><select value={f.sla_status} onChange={set("sla_status")}><option value="">Any</option><option value="ON_TRACK">On track</option><option value="AT_RISK">At risk</option><option value="BREACHED">Breached</option><option value="MET">Met</option></select></div>
            <div><label>From date</label><input type="date" value={f.from_date} onChange={set("from_date")} /></div>
            <div><label>To date</label><input type="date" value={f.to_date} onChange={set("to_date")} /></div>
            {user.role !== "EMPLOYEE" && <div><label>Assignment</label><select value={f.unassigned} onChange={set("unassigned")}><option value="">Any</option><option value="true">Unassigned only</option></select></div>}
            <div><label>Waiting for info</label><select value={f.awaiting_info} onChange={set("awaiting_info")}><option value="">Any</option><option value="true">Yes</option><option value="false">No</option></select></div>
          </div>
        )}</Async>
        {dateBad && <div className="alert err" style={{ margin: 14 }}>The start date must not be after the end date.</div>}
        {!dateBad && (
          <Async state={state}>{(d) => d.items.length === 0
            ? <EmptyState title="No incidents match" text={active ? "Try removing some filters." : "No incidents have been reported yet."} action={active && <button className="btn" onClick={reset}>Clear filters</button>} />
            : <><IncidentTable items={d.items} sort={sort} onSort={setSort} /><Pagination page={d.page} pages={d.pages} total={d.total} pageSize={d.page_size} onPage={setPage} /></>}
          </Async>
        )}
      </Card>
    </>
  );
}
