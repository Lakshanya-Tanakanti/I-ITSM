import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { CheckCheck, Mail, Bell } from "lucide-react";
import { useToast } from "../context/ToastContext";
import { errMsg, get, post } from "../services/api";
import { fmtDate, humanize, useAsync } from "../utils";
import { Async, Card, EmptyState, PageHeader } from "../components/ui";

export default function Notifications() {
  const nav = useNavigate();
  const toast = useToast();
  const [unreadOnly, setUnreadOnly] = useState(false);
  const state = useAsync(() => get("/notifications", { unread_only: unreadOnly, limit: 200 }), [unreadOnly]);
  const readAll = async () => { try { await post("/notifications/read-all"); toast.success("All notifications marked as read"); state.reload(); } catch (e) { toast.error(errMsg(e)); } };
  const open = async (n) => {
    try { if (!n.is_read) await post(`/notifications/${n.id}/read`); } catch { /* ignore */ }
    if (n.incident_number) nav(`/incidents/${n.incident_number}`); else state.reload();
  };
  return (
    <>
      <PageHeader title="Notifications" subtitle="In-app alerts for your incidents, assignments and SLA events.">
        <label className="row small" style={{ margin: 0 }}><input type="checkbox" checked={unreadOnly} onChange={(e) => setUnreadOnly(e.target.checked)} />Unread only</label>
        <button className="btn" onClick={readAll}><CheckCheck size={15} />Mark all as read</button>
      </PageHeader>
      <Card pad={false}>
        <Async state={state}>{(d) => d.items.length === 0 ? <EmptyState title="You are all caught up" text="New notifications will appear here." /> : d.items.map((n) => (
          <div key={n.id} className="row" onClick={() => open(n)} style={{ padding: "12px 18px", borderBottom: "1px solid var(--line)", cursor: "pointer", background: n.is_read ? undefined : "var(--brand-l)", alignItems: "flex-start" }}>
            <Bell size={18} style={{ marginTop: 3 }} />
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: n.is_read ? 500 : 700 }}>{n.subject}</div>
              <div className="small">{n.body}</div>
              <div className="small muted">{fmtDate(n.created_at)} | {humanize(n.event_type)}{n.incident_title ? ` | ${n.incident_title}` : ""}</div>
            </div>
            {!n.is_read && <span className="badge b-indigo">New</span>}
          </div>
        ))}</Async>
      </Card>
    </>
  );
}

export function EmailOutbox() {
  const state = useAsync(() => get("/admin/email-outbox", { limit: 200 }), []);
  const [view, setView] = useState(null);
  return (
    <>
      <PageHeader title="E-mail outbox" subtitle="Simulated e-mail. Nothing is sent over the network, messages are stored here and logged by the server.">
        <button className="btn" onClick={state.reload}>Refresh</button>
      </PageHeader>
      <Card pad={false}>
        <Async state={state}>{(list) => list.length === 0 ? <EmptyState title="Outbox is empty" /> : (
          <div className="table-wrap"><table><thead><tr><th>Sent</th><th>To</th><th>Subject</th><th>Incident</th><th>Status</th></tr></thead>
            <tbody>{list.map((m) => (
              <tr key={m.id} className="click" onClick={() => setView(m)}>
                <td className="small muted">{fmtDate(m.created_at)}</td><td>{m.to_name}<div className="small muted">{m.to_email}</div></td>
                <td><Mail size={13} /> {m.subject}</td><td className="mono">{m.incident_number || "-"}</td><td><span className="badge b-green">{m.delivery_status}</span></td>
              </tr>))}</tbody></table></div>)}</Async>
      </Card>
      {view && <div className="overlay" onClick={() => setView(null)}><div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-h"><h2>{view.subject}</h2></div><div className="modal-b"><p className="small muted">To: {view.to_name} &lt;{view.to_email}&gt;<br />{fmtDate(view.created_at)}</p><p>{view.body}</p></div>
        <div className="modal-f"><button className="btn" onClick={() => setView(null)}>Close</button></div></div></div>}
    </>
  );
}
