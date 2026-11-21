import { useEffect, useState } from "react";
import { AlertTriangle, Inbox, X, ChevronLeft, ChevronRight } from "lucide-react";
import { STATUS_COLOR, STATUS_LABEL, fmtDuration } from "../utils";

export const Spinner = ({ label = "Loading..." }) => (
  <div className="center"><div className="spinner" aria-hidden /><div style={{ marginTop: 10 }}>{label}</div></div>
);

export const EmptyState = ({ title = "Nothing here yet", text, action }) => (
  <div className="center"><Inbox size={36} /><h3 style={{ marginTop: 8, color: "var(--ink)" }}>{title}</h3>{text && <p style={{ margin: "4px 0 0" }}>{text}</p>}{action && <div style={{ marginTop: 12 }}>{action}</div>}</div>
);

export const ErrorState = ({ message, onRetry }) => (
  <div className="center"><AlertTriangle size={36} color="var(--bad)" /><h3 style={{ marginTop: 8, color: "var(--ink)" }}>Could not load data</h3><p style={{ margin: "4px 0 12px" }}>{message}</p>{onRetry && <button className="btn" onClick={onRetry}>Try again</button>}</div>
);

/** Renders loading / error / content for a useAsync result. */
export function Async({ state, children, empty }) {
  if (state.loading && !state.data) return <Spinner />;
  if (state.error) return <ErrorState message={state.error} onRetry={state.reload} />;
  if (!state.data) return null;
  if (empty && empty(state.data)) return <EmptyState {...empty.props} />;
  return children(state.data);
}

export const Alert = ({ kind = "info", children }) => <div className={`alert ${kind}`} role={kind === "err" ? "alert" : undefined}>{children}</div>;

export const PageHeader = ({ title, subtitle, children }) => (
  <div className="page-head"><div><h1>{title}</h1>{subtitle && <p>{subtitle}</p>}</div><div className="row">{children}</div></div>
);

export const Card = ({ title, actions, children, pad = true, style }) => (
  <div className="card" style={style}>
    {title && <div className="card-h"><h2>{title}</h2><div className="row">{actions}</div></div>}
    <div className={pad ? "card-b" : ""}>{children}</div>
  </div>
);

export const StatCard = ({ icon: Icon, label, value, color = "indigo", hint }) => {
  const colors = { indigo: ["var(--brand-l)", "var(--brand)"], red: ["var(--bad-l)", "var(--bad)"], green: ["var(--ok-l)", "var(--ok)"], amber: ["var(--warn-l)", "var(--warn)"], blue: ["var(--info-l)", "var(--info)"], gray: ["#f1f5f9", "#475569"] };
  const [bg, fg] = colors[color];
  return (
    <div className="card stat">
      <div className="ic" style={{ background: bg, color: fg }}><Icon size={22} /></div>
      <div><div className="v">{value}</div><div className="l">{label}</div>{hint && <div className="l">{hint}</div>}</div>
    </div>
  );
};

export const StatusBadge = ({ status }) => <span className={`badge b-${STATUS_COLOR[status] || "gray"}`}>{STATUS_LABEL[status] || status}</span>;
export const PriorityBadge = ({ priority, score }) => <span className={`badge ${String(priority).toLowerCase()}`} title={score != null ? `Score ${score}` : undefined}>{priority}</span>;
export const SlaBadge = ({ status }) => {
  const map = { ON_TRACK: ["green", "On track"], AT_RISK: ["amber", "At risk"], BREACHED: ["red", "Breached"], MET: ["blue", "Met"], MET_LATE: ["red", "Met late"] };
  const [c, l] = map[status] || ["gray", status || "-"];
  return <span className={`badge b-${c}`}>{l}</span>;
};
export const RiskBadge = ({ level }) => {
  const map = { LOW: "green", MEDIUM: "amber", HIGH: "red" };
  return <span className={`badge b-${map[level] || "gray"}`}>{level ? `${level.charAt(0)}${level.slice(1).toLowerCase()} risk` : "-"}</span>;
};

export function Modal({ title, onClose, children, footer, wide }) {
  useEffect(() => {
    const h = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [onClose]);
  return (
    <div className="overlay" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className={`modal ${wide ? "wide" : ""}`} role="dialog" aria-modal="true" aria-label={title}>
        <div className="modal-h"><h2>{title}</h2><button className="icon-btn" onClick={onClose} aria-label="Close"><X size={18} /></button></div>
        <div className="modal-b">{children}</div>
        {footer && <div className="modal-f">{footer}</div>}
      </div>
    </div>
  );
}

export function ConfirmDialog({ title, message, confirmLabel = "Confirm", danger, busy, onConfirm, onCancel, children }) {
  return (
    <Modal title={title} onClose={onCancel} footer={<>
      <button className="btn" onClick={onCancel} disabled={busy}>Cancel</button>
      <button className={`btn ${danger ? "danger" : "primary"}`} onClick={onConfirm} disabled={busy}>{busy ? "Working..." : confirmLabel}</button>
    </>}>
      <p style={{ marginTop: 0 }}>{message}</p>{children}
    </Modal>
  );
}

export const Field = ({ label, hint, error, children }) => (
  <div className="field"><label>{label}</label>{children}{hint && !error && <div className="hint">{hint}</div>}{error && <div className="err">{error}</div>}</div>
);

export function Pagination({ page, pages, total, pageSize, onPage }) {
  if (!total) return null;
  const from = (page - 1) * pageSize + 1, to = Math.min(total, page * pageSize);
  return (
    <div className="pager">
      <span className="muted small">Showing {from} to {to} of {total}</span>
      <div className="row">
        <button className="btn sm" disabled={page <= 1} onClick={() => onPage(page - 1)}><ChevronLeft size={14} />Prev</button>
        <span className="small">Page {page} of {pages}</span>
        <button className="btn sm" disabled={page >= pages} onClick={() => onPage(page + 1)}>Next<ChevronRight size={14} /></button>
      </div>
    </div>
  );
}

/** Live countdown. The server sends remaining_seconds, we convert it to a deadline and tick every second. */
export function SlaCountdown({ remainingSeconds, label }) {
  const [end, setEnd] = useState(() => Date.now() + (remainingSeconds || 0) * 1000);
  const [now, setNow] = useState(Date.now());
  useEffect(() => { setEnd(Date.now() + (remainingSeconds || 0) * 1000); }, [remainingSeconds]);
  useEffect(() => { const id = setInterval(() => setNow(Date.now()), 1000); return () => clearInterval(id); }, []);
  if (remainingSeconds == null) return <span className="muted">-</span>;
  const s = (end - now) / 1000;
  const color = s < 0 ? "red" : s < 600 ? "amber" : "green";
  return <span className={`badge b-${color}`}>{label ? `${label}: ` : ""}{s < 0 ? `overdue ${fmtDuration(-s)}` : fmtDuration(s)}</span>;
}

export const PercentBar = ({ value, color }) => (
  <div className="bar"><span style={{ width: `${Math.min(100, Math.max(0, value || 0))}%`, background: color || (value >= 100 ? "var(--bad)" : value >= 75 ? "var(--warn)" : "var(--brand)") }} /></div>
);
