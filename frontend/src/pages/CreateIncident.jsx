import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Lightbulb, Send, Copy, CheckCircle2 } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { errMsg, get, post } from "../services/api";
import { useAsync, useDebounced } from "../utils";
import { Alert, Async, Card, Field, Modal, PageHeader, PriorityBadge } from "../components/ui";

const SCALE = ["1 - Very low", "2 - Low", "3 - Medium", "4 - High", "5 - Very high"];

export default function CreateIncident() {
  const { user } = useAuth();
  const toast = useToast();
  const nav = useNavigate();
  const refs = useAsync(() => Promise.all([get("/services"), get("/categories")]), []);
  const [f, setF] = useState({ title: "", description: "", service_id: "", category_id: "", impact: 3, urgency: 3, affected_system: "", affected_users: "", business_criticality: "" });
  const [errors, setErrors] = useState({});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [suggestion, setSuggestion] = useState(null);
  const [dups, setDups] = useState([]);
  const [result, setResult] = useState(null);
  const [preview, setPreview] = useState(null);
  const set = (k) => (e) => setF((x) => ({ ...x, [k]: e.target.value }));

  const text = useDebounced(`${f.title}\n${f.description}`, 500);
  useEffect(() => {
    if (f.title.trim().length < 5 && f.description.trim().length < 10) { setSuggestion(null); setDups([]); return; }
    let live = true;
    post("/intelligence/suggest-category", { title: f.title, description: f.description }).then((r) => live && setSuggestion(r.suggestion)).catch(() => {});
    post("/intelligence/check-duplicates", { title: f.title, description: f.description, service_id: f.service_id ? Number(f.service_id) : null }).then((r) => live && setDups(r)).catch(() => {});
    return () => { live = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [text, f.service_id]);

  // The server does the calculation, so the preview always matches what will be stored.
  const pv = useDebounced(JSON.stringify([f.service_id, f.impact, f.urgency, f.affected_users, f.business_criticality]), 300);
  useEffect(() => {
    if (!f.service_id) { setPreview(null); return; }
    let live = true;
    post("/intelligence/preview-priority", {
      service_id: Number(f.service_id), impact: Number(f.impact), urgency: Number(f.urgency),
      affected_users: f.affected_users === "" ? null : Number(f.affected_users),
      business_criticality: user.role === "ADMIN" && f.business_criticality ? Number(f.business_criticality) : null,
    }).then((r) => live && setPreview(r)).catch(() => live && setPreview(null));
    return () => { live = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pv]);

  const validate = () => {
    const e = {};
    if (f.title.trim().length < 5) e.title = "Enter at least 5 characters.";
    if (f.description.trim().length < 10) e.description = "Describe the problem in at least 10 characters.";
    if (!f.service_id) e.service_id = "Choose the affected service.";
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const submit = async (ev) => {
    ev.preventDefault();
    setError("");
    if (!validate()) return;
    setBusy(true);
    try {
      const body = {
        title: f.title, description: f.description, service_id: Number(f.service_id), impact: Number(f.impact), urgency: Number(f.urgency),
        category_id: f.category_id ? Number(f.category_id) : null,
        affected_system: f.affected_system || null,
        affected_users: f.affected_users === "" ? null : Number(f.affected_users),
      };
      if (user.role === "ADMIN" && f.business_criticality) body.business_criticality = Number(f.business_criticality);
      const r = await post("/incidents", body);
      toast.success(`${r.incident.number} reported`);
      setResult(r);
    } catch (e) { setError(errMsg(e)); } finally { setBusy(false); }
  };

  return (
    <>
      <PageHeader title="Report an incident" subtitle="Tell us what is wrong. We classify, prioritise and route it automatically." />
      <Async state={refs}>{([services, categories]) => (
        <form onSubmit={submit} noValidate>
          <div className="grid g-main">
            <Card title="Incident details">
              {error && <Alert kind="err">{error}</Alert>}
              <Field label="Title" error={errors.title}><input value={f.title} onChange={set("title")} maxLength={200} placeholder="Short summary, for example: Cannot access the payment portal" /></Field>
              <Field label="Description" error={errors.description} hint="What happened, when it started, any error message and what you already tried."><textarea value={f.description} onChange={set("description")} maxLength={5000} rows={6} /></Field>
              <div className="form-row">
                <Field label="Affected service" error={errors.service_id}>
                  <select value={f.service_id} onChange={set("service_id")}><option value="">Select a service</option>{services.filter((s) => s.is_active).map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}</select>
                </Field>
                <Field label="Category" hint="Leave on automatic to let the system decide.">
                  <select value={f.category_id} onChange={set("category_id")}><option value="">Detect automatically</option>{categories.filter((c) => c.is_active).map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select>
                </Field>
              </div>
              <div className="form-row">
                <Field label="Impact" hint="How many people or processes are affected?"><select value={f.impact} onChange={set("impact")}>{SCALE.map((l, i) => <option key={i} value={i + 1}>{l}</option>)}</select></Field>
                <Field label="Urgency" hint="How quickly does it need to be fixed?"><select value={f.urgency} onChange={set("urgency")}>{SCALE.map((l, i) => <option key={i} value={i + 1}>{l}</option>)}</select></Field>
              </div>
              <div className="form-row">
                <Field label="Affected system (optional)"><input value={f.affected_system} onChange={set("affected_system")} maxLength={200} /></Field>
                <Field label="Users affected (optional)"><input type="number" min="0" max="1000000" value={f.affected_users} onChange={set("affected_users")} /></Field>
                {user.role === "ADMIN" && <Field label="Criticality override (admin)" hint="Defaults to the service rating."><select value={f.business_criticality} onChange={set("business_criticality")}><option value="">Use service rating</option>{SCALE.map((l, i) => <option key={i} value={i + 1}>{l}</option>)}</select></Field>}
              </div>
              <div className="row" style={{ justifyContent: "flex-end" }}>
                <button type="button" className="btn" onClick={() => nav(-1)}>Cancel</button>
                <button className="btn primary" disabled={busy}><Send size={16} />{busy ? "Submitting..." : "Submit incident"}</button>
              </div>
            </Card>
            <div className="grid" style={{ alignContent: "start" }}>
              <Card title="Priority preview">
                {preview ? <>
                  <div className="row"><PriorityBadge priority={preview.priority} /><b style={{ fontSize: 22 }}>{preview.score}</b></div>
                  <p className="small muted">{preview.explanation}</p>
                  {preview.impact_raised && <Alert kind="info">The number of affected users raised the impact rating to {preview.effective_impact}.</Alert>}
                </> : <p className="muted small">Select a service to preview the priority.</p>}
                <p className="small muted">P1 40 to 125, P2 20 to 39, P3 8 to 19, P4 1 to 7. Many affected users can raise the impact rating (10+ users: 2, 50+: 3, 250+: 4, 1000+: 5). Your own rating is never lowered.</p>
              </Card>
              {suggestion && (
                <Card title="Category suggestion">
                  <div className="row"><Lightbulb size={18} color="var(--warn)" /><b>{suggestion.category_name}</b><span className="badge b-indigo">{Math.round(suggestion.confidence * 100)}% match</span></div>
                  <p className="small muted">{suggestion.reason}</p>
                  {String(f.category_id) !== String(suggestion.category_id) && <button type="button" className="btn sm" onClick={() => setF((x) => ({ ...x, category_id: suggestion.category_id }))}>Use this category</button>}
                </Card>
              )}
              {dups.length > 0 && (
                <Card title="Possible duplicates">
                  <Alert kind="warn"><Copy size={16} /><span>Similar open incidents exist. Check them before submitting. You can still continue.</span></Alert>
                  {dups.map((d) => (
                    <div key={d.number} style={{ padding: "6px 0", borderBottom: "1px solid var(--line)" }}>
                      <Link to={`/incidents/${d.number}`} target="_blank"><b>{d.number}</b></Link> <span className="badge b-amber">{Math.round(d.similarity * 100)}% similar</span>
                      <div className="small">{d.title}</div><div className="small muted">{d.reasons.join(". ")}</div>
                    </div>
                  ))}
                </Card>
              )}
            </div>
          </div>
        </form>
      )}</Async>
      {result && (
        <Modal title="Incident reported" onClose={() => nav(`/incidents/${result.incident.number}`)} footer={<>
          <button className="btn" onClick={() => { setResult(null); setF({ title: "", description: "", service_id: "", category_id: "", impact: 3, urgency: 3, affected_system: "", affected_users: "", business_criticality: "" }); }}>Report another</button>
          <button className="btn primary" onClick={() => nav(`/incidents/${result.incident.number}`)}>Open incident</button></>}>
          <div className="row"><CheckCircle2 color="var(--ok)" /><h2>{result.incident.number} created</h2><PriorityBadge priority={result.incident.priority} score={result.incident.priority_score} /></div>
          <p>{result.assignment_message}</p>
          {result.duplicates?.length > 0 && <Alert kind="warn">Possible duplicates: {result.duplicates.map((d) => d.number).join(", ")}. The incident was still created.</Alert>}
        </Modal>
      )}
    </>
  );
}
