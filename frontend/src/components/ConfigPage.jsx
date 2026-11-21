import { useState } from "react";
import { Pencil, Plus, Power } from "lucide-react";
import { useToast } from "../context/ToastContext";
import { errMsg, get, patch, post } from "../services/api";
import { useAsync } from "../utils";
import { Alert, Async, Card, ConfirmDialog, EmptyState, Field, Modal, PageHeader } from "./ui";

/**
 * Generic admin CRUD screen driven by a config object.
 * fields: [{key,label,type:'text'|'textarea'|'number'|'select', options, min, max, hint, required}]
 * columns: [{label, render(row)}]
 */
export default function ConfigPage({ title, subtitle, path, noun, fields, columns, defaults, toBody, extraLoad, nameOf = (r) => r.name }) {
  const toast = useToast();
  const state = useAsync(() => Promise.all([get(path), extraLoad ? extraLoad() : Promise.resolve(null)]), []);
  const [form, setForm] = useState(null);
  const [confirm, setConfirm] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const save = async () => {
    setBusy(true); setError("");
    try {
      const body = toBody ? toBody(form) : form;
      if (form.id) await patch(`${path}/${form.id}`, body); else await post(path, body);
      toast.success(`${noun} saved`); setForm(null); state.reload();
    } catch (e) { setError(errMsg(e)); } finally { setBusy(false); }
  };
  const toggle = async (row) => {
    setBusy(true);
    try { await patch(`${path}/${row.id}`, { is_active: !row.is_active }); toast.success(`${noun} ${row.is_active ? "deactivated" : "activated"}`); setConfirm(null); state.reload(); }
    catch (e) { toast.error(errMsg(e)); setConfirm(null); } finally { setBusy(false); }
  };

  return (
    <>
      <PageHeader title={title} subtitle={subtitle}>
        <button className="btn primary" onClick={() => { setError(""); setForm({ ...defaults }); }}><Plus size={16} />New {noun.toLowerCase()}</button>
      </PageHeader>
      <Card pad={false}>
        <Async state={state}>{([rows, extra]) => rows.length === 0 ? <EmptyState title={`No ${noun.toLowerCase()} records`} /> : (
          <div className="table-wrap"><table>
            <thead><tr>{columns.map((c) => <th key={c.label}>{c.label}</th>)}<th>Status</th><th></th></tr></thead>
            <tbody>{rows.map((r) => (
              <tr key={r.id}>{columns.map((c) => <td key={c.label}>{c.render(r, extra)}</td>)}
                <td><span className={`badge b-${r.is_active ? "green" : "gray"}`}>{r.is_active ? "Active" : "Inactive"}</span></td>
                <td><div className="row" style={{ flexWrap: "nowrap" }}>
                  <button className="btn sm" onClick={() => { setError(""); setForm({ ...defaults, ...Object.fromEntries(Object.entries(r).map(([k, v]) => [k, v ?? ""])) }); }}><Pencil size={13} />Edit</button>
                  <button className="btn sm" onClick={() => setConfirm(r)}><Power size={13} />{r.is_active ? "Deactivate" : "Activate"}</button>
                </div></td></tr>))}</tbody></table></div>)}</Async>
      </Card>
      {form && (
        <Modal title={`${form.id ? "Edit" : "New"} ${noun.toLowerCase()}`} onClose={() => setForm(null)} footer={<><button className="btn" onClick={() => setForm(null)}>Cancel</button>
          <button className="btn primary" disabled={busy || fields.some((f) => f.required && String(form[f.key] ?? "").trim() === "")} onClick={save}>{busy ? "Saving..." : "Save"}</button></>}>
          {error && <Alert kind="err">{error}</Alert>}
          {fields.map((f) => {
            const opts = typeof f.options === "function" ? f.options(state.data?.[1]) : f.options;
            return (
              <Field key={f.key} label={f.label} hint={f.hint}>
                {f.type === "textarea" ? <textarea value={form[f.key] ?? ""} onChange={(e) => setForm({ ...form, [f.key]: e.target.value })} />
                  : f.type === "select" ? <select value={form[f.key] ?? ""} onChange={(e) => setForm({ ...form, [f.key]: e.target.value })}>{opts.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select>
                  : <input type={f.type || "text"} min={f.min} max={f.max} value={form[f.key] ?? ""} onChange={(e) => setForm({ ...form, [f.key]: e.target.value })} />}
              </Field>);
          })}
        </Modal>
      )}
      {confirm && <ConfirmDialog title={`${confirm.is_active ? "Deactivate" : "Activate"} ${noun.toLowerCase()}`} danger={confirm.is_active} busy={busy} confirmLabel={confirm.is_active ? "Deactivate" : "Activate"} onCancel={() => setConfirm(null)} onConfirm={() => toggle(confirm)}
        message={confirm.is_active ? `"${nameOf(confirm)}" will no longer be offered for new incidents. Existing incidents are not changed.` : `"${nameOf(confirm)}" will be available again.`} />}
    </>
  );
}
