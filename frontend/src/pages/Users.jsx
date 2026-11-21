import { useState } from "react";
import { Plus, Pencil, UserX, UserCheck, Search } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { errMsg, get, patch, post } from "../services/api";
import { fmtDate, useAsync, useDebounced } from "../utils";
import { Alert, Async, Card, ConfirmDialog, EmptyState, Field, Modal, PageHeader } from "../components/ui";

const ROLE_COLOR = { ADMIN: "red", TECHNICIAN: "blue", EMPLOYEE: "gray" };

export default function Users() {
  const { user: me } = useAuth();
  const toast = useToast();
  const [role, setRole] = useState("");
  const [q, setQ] = useState("");
  const dq = useDebounced(q);
  const state = useAsync(() => get("/users", { role: role || undefined, q: dq || undefined }), [role, dq]);
  const [form, setForm] = useState(null);
  const [confirm, setConfirm] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const save = async () => {
    setBusy(true); setError("");
    try {
      if (form.id) {
        const body = { full_name: form.full_name, department: form.department || null, email: form.email, role: form.role };
        if (form.password) body.password = form.password;
        await patch(`/users/${form.id}`, body); toast.success("User updated");
      } else {
        await post("/users", { full_name: form.full_name, email: form.email, password: form.password, role: form.role, department: form.department || null }); toast.success("User created");
      }
      setForm(null); state.reload();
    } catch (e) { setError(errMsg(e)); } finally { setBusy(false); }
  };
  const toggle = async (u) => {
    setBusy(true);
    try { await (u.is_active ? post(`/users/${u.id}/deactivate`) : patch(`/users/${u.id}`, { is_active: true })); toast.success(u.is_active ? "User deactivated" : "User reactivated"); setConfirm(null); state.reload(); }
    catch (e) { toast.error(errMsg(e)); setConfirm(null); } finally { setBusy(false); }
  };

  return (
    <>
      <PageHeader title="Users" subtitle="Create accounts, change roles and deactivate people who have left.">
        <button className="btn primary" onClick={() => { setError(""); setForm({ full_name: "", email: "", password: "", role: "EMPLOYEE", department: "" }); }}><Plus size={16} />New user</button>
      </PageHeader>
      <Card pad={false}>
        <div className="filters">
          <div><label>Search</label><div className="rel"><input placeholder="Name or e-mail" value={q} onChange={(e) => setQ(e.target.value)} /></div></div>
          <div><label>Role</label><select value={role} onChange={(e) => setRole(e.target.value)}><option value="">All roles</option><option value="EMPLOYEE">Employee</option><option value="TECHNICIAN">Technician</option><option value="ADMIN">Admin</option></select></div>
        </div>
        <Async state={state}>{(list) => list.length === 0 ? <EmptyState title="No users found" text="Try a different search." /> : (
          <div className="table-wrap"><table><thead><tr><th>Code</th><th>Name</th><th>E-mail</th><th>Role</th><th>Department</th><th>Status</th><th>Created</th><th></th></tr></thead>
            <tbody>{list.map((u) => (
              <tr key={u.id}><td className="mono">{u.employee_code}</td><td><b>{u.full_name}</b></td><td>{u.email}</td>
                <td><span className={`badge b-${ROLE_COLOR[u.role]}`}>{u.role}</span></td><td>{u.department || "-"}</td>
                <td><span className={`badge b-${u.is_active ? "green" : "gray"}`}>{u.is_active ? "Active" : "Inactive"}</span></td><td className="small muted">{fmtDate(u.created_at)}</td>
                <td><div className="row" style={{ flexWrap: "nowrap" }}>
                  <button className="btn sm" onClick={() => { setError(""); setForm({ ...u, password: "", department: u.department || "" }); }}><Pencil size={13} />Edit</button>
                  {u.id !== me.id && <button className={`btn sm ${u.is_active ? "" : "ok"}`} onClick={() => setConfirm(u)}>{u.is_active ? <><UserX size={13} />Deactivate</> : <><UserCheck size={13} />Reactivate</>}</button>}
                </div></td></tr>))}</tbody></table></div>)}</Async>
      </Card>
      {form && (
        <Modal title={form.id ? "Edit user" : "New user"} onClose={() => setForm(null)} footer={<><button className="btn" onClick={() => setForm(null)}>Cancel</button><button className="btn primary" disabled={busy || !form.full_name || !form.email || (!form.id && !form.password)} onClick={save}>{busy ? "Saving..." : "Save"}</button></>}>
          {error && <Alert kind="err">{error}</Alert>}
          <Field label="Full name"><input value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} /></Field>
          <Field label="E-mail"><input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></Field>
          <div className="form-row">
            <Field label="Role"><select value={form.role} disabled={form.id === me.id} onChange={(e) => setForm({ ...form, role: e.target.value })}><option value="EMPLOYEE">Employee</option><option value="TECHNICIAN">Technician</option><option value="ADMIN">Admin</option></select></Field>
            <Field label="Department"><input value={form.department} onChange={(e) => setForm({ ...form, department: e.target.value })} /></Field>
          </div>
          <Field label={form.id ? "New password (leave empty to keep)" : "Password"} hint="At least 8 characters with at least one letter and one number."><input type="password" autoComplete="new-password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} /></Field>
          {form.role === "TECHNICIAN" && <p className="small muted">After saving, set skills, team and workload limit under Technicians and teams.</p>}
        </Modal>
      )}
      {confirm && <ConfirmDialog title={confirm.is_active ? "Deactivate user" : "Reactivate user"} danger={confirm.is_active} busy={busy} confirmLabel={confirm.is_active ? "Deactivate" : "Reactivate"} onCancel={() => setConfirm(null)} onConfirm={() => toggle(confirm)}
        message={confirm.is_active ? `${confirm.full_name} will no longer be able to sign in. Their history is kept.` : `${confirm.full_name} will be able to sign in again.`} />}
    </>
  );
}
