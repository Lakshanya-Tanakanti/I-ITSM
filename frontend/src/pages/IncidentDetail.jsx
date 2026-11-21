import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { AlertTriangle, ArrowRight, Brain, CheckCircle2, Copy, Link2, Lightbulb, MessageSquarePlus, RotateCcw, Send, Star, UserCheck, Pencil } from "lucide-react";
import { useToast } from "../context/ToastContext";
import { useAuth } from "../context/AuthContext";
import { errMsg, get, patch, post } from "../services/api";
import { ACTION_LABEL, fmtDate, fmtMinutes, humanize, useAsync, usePolling } from "../utils";
import { Alert, Async, Card, ConfirmDialog, Field, Modal, PageHeader, PercentBar, PriorityBadge, RiskBadge, SlaBadge, SlaCountdown, StatusBadge } from "../components/ui";

const NOTE_LABEL = { INVESTIGATION: "Investigation", COMMENT: "Comment", INFO_REQUEST: "Information request", INFO_REPLY: "Reply", ADDITIONAL_INFO: "Additional information" };

function SlaPanel({ sla }) {
  const row = (p, title) => (
    <div style={{ marginBottom: 12 }}>
      <div className="row between"><b>{title}</b><SlaBadge status={p.state} /></div>
      <PercentBar value={p.elapsed_percent} />
      <div className="row between small muted" style={{ marginTop: 4 }}>
        <span>Target {fmtMinutes(p.target_minutes)} | Due {fmtDate(p.deadline)}</span>
        {p.pending ? <SlaCountdown remainingSeconds={p.remaining_seconds} /> : <span>Completed {fmtDate(p.completed_at)}</span>}
      </div>
    </div>
  );
  return <Card title="SLA">{row(sla.response, "Response")}{row(sla.resolution, "Resolution")}<div className="small muted">Policy: {sla.policy_name}. Warning at {sla.warning_percent}%.</div></Card>;
}

function AssignPanel({ inc, onDone }) {
  const toast = useToast();
  const rec = useAsync(() => get(`/incidents/${inc.number}/recommendations`), [inc.number, inc.status, inc.assigned_technician?.id]);
  const [strategy, setStrategy] = useState("");
  const [pick, setPick] = useState(null);
  const [override, setOverride] = useState(false);
  const [busy, setBusy] = useState(false);
  useEffect(() => { if (strategy) rec.setData && get(`/incidents/${inc.number}/recommendations`, { strategy }).then(rec.setData).catch((e) => toast.error(errMsg(e))); /* eslint-disable-next-line */ }, [strategy]);
  const assign = async (tech, ov) => {
    setBusy(true);
    try { await post(`/incidents/${inc.number}/assign`, { technician_id: tech, override: ov }); toast.success("Technician assigned"); setPick(null); setOverride(false); onDone(); }
    catch (e) { toast.error(errMsg(e)); } finally { setBusy(false); }
  };
  return (
    <Card title={inc.assigned_technician ? "Reassign technician" : "Assign technician"}>
      <Async state={rec}>{(r) => (
        <>
          <Field label="Recommendation strategy"><select value={strategy || r.strategy.name} onChange={(e) => setStrategy(e.target.value)}>{r.available_strategies.map((s) => <option key={s.name} value={s.name}>{s.label}</option>)}</select><div className="hint">{r.strategy.description}</div></Field>
          {r.eligible.length === 0 && <Alert kind="warn">No technician is eligible. Use an override below.</Alert>}
          {r.eligible.map((t) => (
            <div key={t.technician_id} className="note">
              <div className="row between"><div><b>#{t.rank} {t.name}</b> <span className="muted small">{t.team}</span></div><span className="badge b-indigo">Score {t.score}</span></div>
              <ul className="small muted" style={{ margin: "4px 0 8px 16px", padding: 0 }}>{t.reasons.map((x, i) => <li key={i}>{x}</li>)}<li>Workload {t.factors.workload}/{t.factors.workload_limit}</li></ul>
              {t.technician_id === inc.assigned_technician?.id ? <span className="badge b-green">Currently assigned</span> : <button className="btn sm primary" disabled={busy} onClick={() => setPick({ id: t.technician_id, name: t.name, ov: false })}><UserCheck size={14} />Assign</button>}
            </div>
          ))}
          {r.ineligible.length > 0 && (
            <details><summary className="small muted" style={{ cursor: "pointer" }}>{r.ineligible.length} not eligible (admin may override)</summary>
              {r.ineligible.map((t) => (
                <div key={t.technician_id} className="row between small" style={{ padding: "6px 0" }}>
                  <div><b>{t.name}</b><div className="muted">{t.reasons.join(". ")}</div></div>
                  <button className="btn sm" onClick={() => setPick({ id: t.technician_id, name: t.name, ov: true })}>Override</button>
                </div>
              ))}
            </details>
          )}
        </>
      )}</Async>
      {pick && (
        <ConfirmDialog title={pick.ov ? "Override assignment" : "Assign technician"} confirmLabel="Assign" busy={busy} onCancel={() => setPick(null)} onConfirm={() => assign(pick.id, pick.ov || override)}
          message={`Assign ${inc.number} to ${pick.name}?${inc.assigned_technician ? ` It is currently assigned to ${inc.assigned_technician.full_name}.` : ""}`}>
          {pick.ov && <Alert kind="warn">This technician does not meet the normal rules (skill, availability or workload). The override is recorded in the audit log.</Alert>}
        </ConfirmDialog>
      )}
    </Card>
  );
}

function Intelligence({ inc }) {
  const dups = useAsync(() => get(`/incidents/${inc.number}/duplicates`), [inc.number]);
  const rel = useAsync(() => get(`/incidents/${inc.number}/related`), [inc.number]);
  const sug = useAsync(() => get(`/incidents/${inc.number}/suggested-resolutions`), [inc.number]);
  return (
    <Card title={<span className="row"><Brain size={17} />Intelligent insights</span>}>
      <div style={{ marginBottom: 12 }}>
        <div className="row between"><b>SLA risk</b><RiskBadge level={inc.risk.level} /></div>
        <ul className="small muted" style={{ margin: "4px 0 0 16px", padding: 0 }}>{inc.risk.reasons.map((r, i) => <li key={i}>{r}</li>)}</ul>
      </div>
      <hr style={{ border: 0, borderTop: "1px solid var(--line)" }} />
      <b className="small">Duplicate candidates</b>
      <Async state={dups}>{(d) => d.length === 0 ? <div className="small muted">None found.</div> : d.map((x) => (
        <div key={x.number} className="small" style={{ padding: "4px 0" }}><Copy size={12} /> <Link to={`/incidents/${x.number}`}>{x.number}</Link> {Math.round(x.similarity * 100)}% similar. {x.title}</div>
      ))}</Async>
      <hr style={{ border: 0, borderTop: "1px solid var(--line)" }} />
      <b className="small">Related incidents on this service</b>
      <Async state={rel}>{(d) => (<>
        {d.summary && <Alert kind="warn"><Link2 size={14} />{d.summary}</Alert>}
        {d.related.length === 0 ? <div className="small muted">No correlated incidents.</div> : d.related.map((x) => (
          <div key={x.number} className="small" style={{ padding: "3px 0" }}><Link to={`/incidents/${x.number}`}>{x.number}</Link> <StatusBadge status={x.status} /> {x.title}</div>
        ))}</>)}</Async>
      <hr style={{ border: 0, borderTop: "1px solid var(--line)" }} />
      <b className="small">Suggested resolutions from past incidents</b>
      <Async state={sug}>{(d) => d.length === 0 ? <div className="small muted">No similar resolved incidents yet.</div> : d.map((x) => (
        <div key={x.incident_number} className="note small"><Lightbulb size={13} color="var(--warn)" /> <Link to={`/incidents/${x.incident_number}`}>{x.incident_number}</Link> ({Math.round(x.similarity * 100)}% similar)
          <div><b>Fix:</b> {x.summary}</div>{x.root_cause && <div className="muted">Cause: {x.root_cause}</div>}</div>
      ))}</Async>
    </Card>
  );
}

export default function IncidentDetail() {
  const { number } = useParams();
  const { user } = useAuth();
  const toast = useToast();
  const state = useAsync(() => get(`/incidents/${number}`), [number]);
  const notes = useAsync(() => get(`/incidents/${number}/notes`), [number]);
  const timeline = useAsync(() => get(`/incidents/${number}/timeline`), [number]);
  const [modal, setModal] = useState(null);
  const [form, setForm] = useState({});
  const [busy, setBusy] = useState(false);
  const [noteType, setNoteType] = useState("COMMENT");
  const [noteBody, setNoteBody] = useState("");
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState("");
  const [edit, setEdit] = useState(null);
  const [cats, setCats] = useState([]);

  const reloadAll = () => { state.reload(); notes.reload(); timeline.reload(); };
  usePolling(() => { state.reload(); }, 30000);
  useEffect(() => { get("/categories").then(setCats).catch(() => {}); }, []);

  const run = async (fn, okMsg) => {
    setBusy(true);
    try { await fn(); toast.success(okMsg); setModal(null); setForm({}); reloadAll(); }
    catch (e) { toast.error(errMsg(e)); } finally { setBusy(false); }
  };
  const transition = (to, extra = {}) => run(() => post(`/incidents/${number}/transition`, { to_status: to, ...extra }), `Moved to ${to.toLowerCase().replace("_", " ")}`);

  const addNote = (inc) => run(() => post(`/incidents/${number}/notes`, { note_type: noteType, body: noteBody }).then(() => setNoteBody("")), "Note added");

  return (
    <Async state={state}>{(inc) => {
      const p = inc.permissions, isStaff = user.role !== "EMPLOYEE";
      const noteTypes = [];
      if (p.can_add_investigation_note) noteTypes.push("INVESTIGATION");
      noteTypes.push("COMMENT");
      if (p.can_request_info) noteTypes.push("INFO_REQUEST");
      if (p.can_reply && inc.reporter.id === user.id) noteTypes.push(inc.awaiting_info ? "INFO_REPLY" : "ADDITIONAL_INFO");
      const canNote = inc.status !== "CLOSED";
      const type = noteTypes.includes(noteType) ? noteType : noteTypes[0];

      return (
        <>
          <PageHeader title={<span className="row"><span className="mono">{inc.number}</span><PriorityBadge priority={inc.priority} score={inc.priority_score} /><StatusBadge status={inc.status} /><SlaBadge status={inc.sla.overall} /></span>} subtitle={inc.title}>
            {p.can_edit_text && <button className="btn" onClick={() => setEdit({ title: inc.title, description: inc.description, affected_system: inc.affected_system || "", affected_users: inc.affected_users ?? "" })}><Pencil size={15} />Edit</button>}
            {inc.allowed_transitions.map((t) => (
              <button key={t} className={`btn ${t === "RESOLVED" || t === "VERIFIED" ? "ok" : "primary"}`} disabled={busy}
                onClick={() => (t === "RESOLVED" || (t === "IN_PROGRESS" && inc.status === "RESOLVED") || t === "CLOSED" || t === "VERIFIED" ? setModal(t === "IN_PROGRESS" ? "REOPEN" : t) : transition(t))}>
                {t === "IN_PROGRESS" && inc.status === "RESOLVED" ? <><RotateCcw size={15} />Reopen</> : <><ArrowRight size={15} />{ACTION_LABEL[t] || humanize(t)}</>}
              </button>
            ))}
          </PageHeader>

          {inc.awaiting_info && <Alert kind="warn"><AlertTriangle size={16} /><span>Waiting for the reporter to provide more information.</span></Alert>}
          {inc.escalation_level > 0 && <Alert kind="err"><AlertTriangle size={16} /><span>Escalated to level {inc.escalation_level} because the response SLA was breached.</span></Alert>}
          {inc.duplicate_of && <Alert kind="info"><Copy size={16} /><span>Linked as related to <Link to={`/incidents/${inc.duplicate_of.number}`}>{inc.duplicate_of.number}</Link>.</span></Alert>}

          <div className="grid g-main">
            <div className="grid" style={{ alignContent: "start" }}>
              <Card title="Description"><p style={{ whiteSpace: "pre-wrap", marginTop: 0 }}>{inc.description}</p>
                <dl className="kv">
                  <dt>Service</dt><dd>{inc.service.name} (criticality {inc.business_criticality}{inc.criticality_overridden && ", overridden"})</dd>
                  <dt>Category</dt><dd>{inc.category?.name} <span className="muted small">({humanize(inc.category_source)})</span></dd>
                  <dt>Impact / urgency</dt><dd>{inc.impact} / {inc.urgency} <span className="muted small">score {inc.priority_score}</span>{inc.effective_impact !== inc.impact && <div className="small muted">Impact counted as {inc.effective_impact} because {inc.affected_users} users are affected.</div>}</dd>
                  <dt>Reporter</dt><dd>{inc.reporter.full_name} <span className="muted small">{inc.reporter.department}</span></dd>
                  <dt>Technician</dt><dd>{inc.assigned_technician?.full_name || <span className="muted">Unassigned</span>}</dd>
                  {inc.affected_system && <><dt>Affected system</dt><dd>{inc.affected_system}</dd></>}
                  {inc.affected_users != null && <><dt>Users affected</dt><dd>{inc.affected_users}</dd></>}
                  <dt>Created</dt><dd>{fmtDate(inc.created_at)}</dd>
                  {inc.acknowledged_at && <><dt>Acknowledged</dt><dd>{fmtDate(inc.acknowledged_at)}</dd></>}
                  {inc.resolved_at && <><dt>Resolved</dt><dd>{fmtDate(inc.resolved_at)}</dd></>}
                  {inc.closed_at && <><dt>Closed</dt><dd>{fmtDate(inc.closed_at)}</dd></>}
                  {inc.reopen_count > 0 && <><dt>Reopened</dt><dd>{inc.reopen_count} time(s)</dd></>}
                </dl>
                {(p.can_change_category || p.can_edit_priority) && <div className="row" style={{ marginTop: 12 }}>
                  {p.can_change_category && <select style={{ width: "auto" }} value={inc.category?.id || ""} onChange={(e) => run(() => patch(`/incidents/${number}`, { category_id: Number(e.target.value) }), "Category updated")}>{cats.filter((c) => c.is_active || c.id === inc.category?.id).map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select>}
                  {p.can_edit_priority && <button className="btn sm" onClick={() => setModal("PRIORITY")}>Adjust priority</button>}
                </div>}
              </Card>

              {inc.resolution && <Card title="Resolution"><dl className="kv"><dt>Summary</dt><dd>{inc.resolution.summary}</dd><dt>Root cause</dt><dd>{inc.resolution.root_cause}</dd><dt>Resolved by</dt><dd>{inc.resolution.technician?.full_name}</dd></dl></Card>}
              {inc.feedback && <Card title="Employee feedback"><div className="rating">{[1, 2, 3, 4, 5].map((n) => <Star key={n} size={20} fill={n <= inc.feedback.rating ? "#f59e0b" : "none"} color="#f59e0b" />)}</div>{inc.feedback.comment && <p>{inc.feedback.comment}</p>}</Card>}
              {p.can_give_feedback && (
                <Card title="How did we do?">
                  <div className="rating">{[1, 2, 3, 4, 5].map((n) => <button key={n} type="button" className={n <= rating ? "on" : ""} onClick={() => setRating(n)} aria-label={`${n} stars`}>★</button>)}</div>
                  <Field label="Comment (optional)"><textarea value={comment} onChange={(e) => setComment(e.target.value)} maxLength={2000} /></Field>
                  <button className="btn primary" disabled={!rating || busy} onClick={() => run(() => post(`/incidents/${number}/feedback`, { rating, comment: comment || null }), "Thank you for your feedback")}><Send size={14} />Submit feedback</button>
                </Card>
              )}

              <Card title="Notes and conversation">
                <Async state={notes}>{(list) => list.length === 0 ? <div className="muted">No notes yet.</div> : list.map((n) => (
                  <div key={n.id} className={`note ${n.is_internal ? "internal" : ""}`}>
                    <div className="row between small"><span><b>{n.author?.full_name || n.author_name}</b> <span className="badge b-gray">{NOTE_LABEL[n.note_type] || n.note_type}</span>{n.is_internal && <span className="badge b-amber" style={{ marginLeft: 4 }}>Internal</span>}</span><span className="muted">{fmtDate(n.created_at)}</span></div>
                    <div style={{ whiteSpace: "pre-wrap", marginTop: 4 }}>{n.body}</div>
                  </div>
                ))}</Async>
                {canNote && (
                  <div style={{ marginTop: 12 }}>
                    <div className="row">
                      <select style={{ width: "auto" }} value={type} onChange={(e) => setNoteType(e.target.value)}>{noteTypes.map((t) => <option key={t} value={t}>{NOTE_LABEL[t]}</option>)}</select>
                      {type === "INVESTIGATION" && <span className="small muted">Internal, hidden from the reporter.</span>}
                      {type === "INFO_REQUEST" && <span className="small muted">Notifies the reporter and pauses nothing in the SLA.</span>}
                    </div>
                    <textarea style={{ marginTop: 8 }} value={noteBody} onChange={(e) => setNoteBody(e.target.value)} placeholder="Write a note..." maxLength={5000} />
                    <div style={{ marginTop: 8 }}><button className="btn primary" disabled={!noteBody.trim() || busy} onClick={() => addNote(inc)}><MessageSquarePlus size={15} />Add note</button></div>
                  </div>
                )}
              </Card>
            </div>

            <div className="grid" style={{ alignContent: "start" }}>
              <SlaPanel sla={inc.sla} />
              {p.can_assign && <AssignPanel inc={inc} onDone={reloadAll} />}
              {p.can_view_intelligence && <Intelligence inc={inc} />}
              <Card title="Timeline">
                <Async state={timeline}>{(list) => <ul className="timeline">{list.map((e) => (
                  <li key={e.id}><div className="small"><b>{humanize(e.action)}</b></div><div className="small">{e.description}</div><div className="small muted">{e.actor_name} | {fmtDate(e.created_at)}</div></li>
                ))}</ul>}</Async>
              </Card>
            </div>
          </div>

          {modal === "RESOLVED" && (
            <Modal title="Resolve incident" onClose={() => setModal(null)} footer={<><button className="btn" onClick={() => setModal(null)}>Cancel</button>
              <button className="btn ok" disabled={busy || !form.summary?.trim() || !form.cause?.trim()} onClick={() => transition("RESOLVED", { resolution_summary: form.summary, root_cause: form.cause })}><CheckCircle2 size={15} />Mark resolved</button></>}>
              <Field label="Resolution summary" hint="What did you do to fix it?"><textarea value={form.summary || ""} onChange={(e) => setForm({ ...form, summary: e.target.value })} maxLength={5000} /></Field>
              <Field label="Root cause"><textarea value={form.cause || ""} onChange={(e) => setForm({ ...form, cause: e.target.value })} maxLength={2000} /></Field>
            </Modal>
          )}
          {modal === "REOPEN" && (
            <Modal title="Reopen incident" onClose={() => setModal(null)} footer={<><button className="btn" onClick={() => setModal(null)}>Cancel</button>
              <button className="btn danger" disabled={busy || !form.reason?.trim()} onClick={() => transition("IN_PROGRESS", { reason: form.reason })}>Reopen</button></>}>
              <Field label="Why is the problem not fixed?"><textarea value={form.reason || ""} onChange={(e) => setForm({ ...form, reason: e.target.value })} maxLength={2000} /></Field>
            </Modal>
          )}
          {modal === "VERIFIED" && <ConfirmDialog title="Verify resolution" message="Confirm that the problem is fixed and you can work normally again?" confirmLabel="Yes, it is fixed" busy={busy} onCancel={() => setModal(null)} onConfirm={() => transition("VERIFIED")} />}
          {modal === "CLOSED" && (
            <ConfirmDialog title="Close incident" message="Closing is final. A closed incident is read-only." confirmLabel="Close incident" danger busy={busy} onCancel={() => setModal(null)} onConfirm={() => transition("CLOSED", { closure_note: form.note || null })}>
              <Field label="Closure note (optional)"><textarea value={form.note || ""} onChange={(e) => setForm({ ...form, note: e.target.value })} maxLength={2000} /></Field>
            </ConfirmDialog>
          )}
          {modal === "PRIORITY" && (
            <Modal title="Adjust priority inputs" onClose={() => setModal(null)} footer={<><button className="btn" onClick={() => setModal(null)}>Cancel</button>
              <button className="btn primary" disabled={busy} onClick={() => run(() => patch(`/incidents/${number}`, { impact: Number(form.impact ?? inc.impact), urgency: Number(form.urgency ?? inc.urgency), business_criticality: Number(form.crit ?? inc.business_criticality) }), "Priority recalculated")}>Save</button></>}>
              <div className="form-row">
                {[["impact", "Impact", inc.impact], ["urgency", "Urgency", inc.urgency], ["crit", "Criticality", inc.business_criticality]].map(([k, l, v]) => (
                  <Field key={k} label={l}><select value={form[k] ?? v} onChange={(e) => setForm({ ...form, [k]: e.target.value })}>{[1, 2, 3, 4, 5].map((n) => <option key={n}>{n}</option>)}</select></Field>
                ))}
              </div>
              <p className="small muted">The score is impact x urgency x criticality. SLA deadlines are recalculated from the new priority.</p>
            </Modal>
          )}
          {edit && (
            <Modal title="Edit incident" onClose={() => setEdit(null)} footer={<><button className="btn" onClick={() => setEdit(null)}>Cancel</button>
              <button className="btn primary" disabled={busy} onClick={() => run(() => patch(`/incidents/${number}`, { title: edit.title, description: edit.description, affected_system: edit.affected_system || null, affected_users: edit.affected_users === "" ? null : Number(edit.affected_users) }).then(() => setEdit(null)), "Incident updated")}>Save changes</button></>}>
              <Field label="Title"><input value={edit.title} onChange={(e) => setEdit({ ...edit, title: e.target.value })} maxLength={200} /></Field>
              <Field label="Description"><textarea value={edit.description} onChange={(e) => setEdit({ ...edit, description: e.target.value })} rows={5} maxLength={5000} /></Field>
              <div className="form-row"><Field label="Affected system"><input value={edit.affected_system} onChange={(e) => setEdit({ ...edit, affected_system: e.target.value })} /></Field>
                <Field label="Users affected"><input type="number" min="0" value={edit.affected_users} onChange={(e) => setEdit({ ...edit, affected_users: e.target.value })} /></Field></div>
            </Modal>
          )}
        </>
      );
    }}</Async>
  );
}
