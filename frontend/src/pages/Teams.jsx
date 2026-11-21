import { useState } from "react";
import { Plus, Pencil, Settings2 } from "lucide-react";
import { useToast } from "../context/ToastContext";
import { errMsg, get, patch, post, put } from "../services/api";
import { useAsync } from "../utils";
import { Alert, Async, Card, EmptyState, Field, Modal, PageHeader, PercentBar } from "../components/ui";

function ProfileModal({ tech, teams, cats, onClose, onSaved }) {
  const toast = useToast();
  const p = tech.technician_profile || {};
  const [f, setF] = useState({ team_id: p.team_id || "", experience_years: p.experience_years ?? 0, workload_limit: p.workload_limit ?? 5, is_available: p.is_available ?? true });
  const [skills, setSkills] = useState(Object.fromEntries((p.skills || []).map((s) => [s.category_id, s.proficiency])));
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const save = async () => {
    setBusy(true); setError("");
    try {
      await put(`/users/${tech.id}/technician-profile`, {
        team_id: f.team_id ? Number(f.team_id) : 0, experience_years: Number(f.experience_years), workload_limit: Number(f.workload_limit), is_available: f.is_available,
        skills: Object.entries(skills).filter(([, v]) => v > 0).map(([k, v]) => ({ category_id: Number(k), proficiency: Number(v) })),
      });
      toast.success("Technician profile saved"); onSaved();
    } catch (e) { setError(errMsg(e)); } finally { setBusy(false); }
  };
  return (
    <Modal title={`Technician profile: ${tech.full_name}`} wide onClose={onClose} footer={<><button className="btn" onClick={onClose}>Cancel</button><button className="btn primary" disabled={busy} onClick={save}>{busy ? "Saving..." : "Save profile"}</button></>}>
      {error && <Alert kind="err">{error}</Alert>}
      <div className="form-row">
        <Field label="Team"><select value={f.team_id} onChange={(e) => setF({ ...f, team_id: e.target.value })}><option value="">No team</option>{teams.filter((t) => t.is_active).map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}</select></Field>
        <Field label="Experience (years)"><input type="number" min="0" max="60" value={f.experience_years} onChange={(e) => setF({ ...f, experience_years: e.target.value })} /></Field>
        <Field label="Workload limit"><input type="number" min="1" max="50" value={f.workload_limit} onChange={(e) => setF({ ...f, workload_limit: e.target.value })} /></Field>
      </div>
      <label className="row" style={{ marginBottom: 12 }}><input type="checkbox" checked={f.is_available} onChange={(e) => setF({ ...f, is_available: e.target.checked })} />Available for new assignments</label>
      <b>Skills (0 means none, 5 means expert)</b>
      <div className="form-row" style={{ marginTop: 8 }}>
        {cats.map((c) => (
          <div key={c.id} className="row between"><span>{c.name}</span>
            <select style={{ width: 70 }} value={skills[c.id] || 0} onChange={(e) => setSkills({ ...skills, [c.id]: Number(e.target.value) })}>{[0, 1, 2, 3, 4, 5].map((n) => <option key={n}>{n}</option>)}</select></div>
        ))}
      </div>
    </Modal>
  );
}

export default function Teams() {
  const toast = useToast();
  const [tab, setTab] = useState("tech");
  const data = useAsync(() => Promise.all([get("/users", { role: "TECHNICIAN" }), get("/teams"), get("/categories"), get("/technicians/workload")]), []);
  const [editTech, setEditTech] = useState(null);
  const [team, setTeam] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const saveTeam = async () => {
    setBusy(true); setError("");
    try {
      const body = { name: team.name, description: team.description || null, lead_id: team.lead_id ? Number(team.lead_id) : null };
      if (team.id) await patch(`/teams/${team.id}`, { ...body, is_active: team.is_active }); else await post("/teams", body);
      toast.success("Team saved"); setTeam(null); data.reload();
    } catch (e) { setError(errMsg(e)); } finally { setBusy(false); }
  };

  return (
    <>
      <PageHeader title="Technicians and teams" subtitle="Skills, workload limits and availability drive automatic assignment.">
        {tab === "teams" && <button className="btn primary" onClick={() => { setError(""); setTeam({ name: "", description: "", lead_id: "", is_active: true }); }}><Plus size={16} />New team</button>}
      </PageHeader>
      <div className="tabs"><button className={tab === "tech" ? "on" : ""} onClick={() => setTab("tech")}>Technicians</button><button className={tab === "teams" ? "on" : ""} onClick={() => setTab("teams")}>Teams</button></div>
      <Async state={data}>{([techs, teams, cats, load]) => tab === "tech" ? (
        <Card pad={false}>{techs.length === 0 ? <EmptyState title="No technicians" text="Create a user with the Technician role first." /> : (
          <div className="table-wrap"><table><thead><tr><th>Name</th><th>Team</th><th>Skills</th><th>Experience</th><th style={{ width: 170 }}>Workload</th><th>Status</th><th></th></tr></thead>
            <tbody>{techs.map((t) => { const w = load.find((x) => x.technician_id === t.id); const p = t.technician_profile; return (
              <tr key={t.id}><td><b>{t.full_name}</b><div className="small muted">{t.email}</div></td><td>{p?.team_name || "-"}</td>
                <td>{(p?.skills || []).map((s) => <span key={s.category_id} className="chip">{s.category_name} {s.proficiency}/5</span>)}{!p?.skills?.length && <span className="muted">None</span>}</td>
                <td>{p?.experience_years ?? 0} yrs</td>
                <td><div className="small">{w?.active_incidents ?? 0} / {p?.workload_limit}</div><PercentBar value={w?.utilization_percent} /></td>
                <td><span className={`badge b-${!t.is_active ? "gray" : p?.is_available ? "green" : "amber"}`}>{!t.is_active ? "Inactive" : p?.is_available ? "Available" : "Unavailable"}</span></td>
                <td><button className="btn sm" onClick={() => setEditTech(t)}><Settings2 size={13} />Edit profile</button></td></tr>); })}</tbody></table></div>)}</Card>
      ) : (
        <Card pad={false}><div className="table-wrap"><table><thead><tr><th>Team</th><th>Description</th><th>Lead</th><th>Members</th><th>Status</th><th></th></tr></thead>
          <tbody>{teams.map((t) => (<tr key={t.id}><td><b>{t.name}</b></td><td>{t.description || "-"}</td><td>{t.lead_name || "-"}</td><td>{t.member_count}</td>
            <td><span className={`badge b-${t.is_active ? "green" : "gray"}`}>{t.is_active ? "Active" : "Inactive"}</span></td>
            <td><button className="btn sm" onClick={() => { setError(""); setTeam({ ...t, description: t.description || "", lead_id: t.lead_id || "" }); }}><Pencil size={13} />Edit</button></td></tr>))}</tbody></table></div></Card>
      )}</Async>
      {editTech && data.data && <ProfileModal tech={editTech} teams={data.data[1]} cats={data.data[2]} onClose={() => setEditTech(null)} onSaved={() => { setEditTech(null); data.reload(); }} />}
      {team && data.data && (
        <Modal title={team.id ? "Edit team" : "New team"} onClose={() => setTeam(null)} footer={<><button className="btn" onClick={() => setTeam(null)}>Cancel</button><button className="btn primary" disabled={busy || team.name.trim().length < 2} onClick={saveTeam}>Save</button></>}>
          {error && <Alert kind="err">{error}</Alert>}
          <Field label="Name"><input value={team.name} onChange={(e) => setTeam({ ...team, name: e.target.value })} /></Field>
          <Field label="Description"><textarea value={team.description} onChange={(e) => setTeam({ ...team, description: e.target.value })} /></Field>
          <Field label="Team lead" hint="Receives escalations when the response SLA is breached."><select value={team.lead_id} onChange={(e) => setTeam({ ...team, lead_id: e.target.value })}><option value="">No lead</option>{data.data[0].map((t) => <option key={t.id} value={t.id}>{t.full_name}</option>)}</select></Field>
          {team.id && <label className="row"><input type="checkbox" checked={team.is_active} onChange={(e) => setTeam({ ...team, is_active: e.target.checked })} />Team is active</label>}
        </Modal>
      )}
    </>
  );
}
