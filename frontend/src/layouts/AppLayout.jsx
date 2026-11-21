import { useEffect, useRef, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  LayoutDashboard, PlusCircle, ListChecks, Bell, Users, Wrench, Server, Tags, Timer, Settings, BarChart3, ScrollText, Mail,
  Activity, UserCircle, LogOut, Menu, ShieldCheck, ChevronDown, CheckCheck, UsersRound, Inbox,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { get, post } from "../services/api";
import { fmtShort, usePolling } from "../utils";
import { ConfirmDialog } from "../components/ui";

const NAV = {
  EMPLOYEE: [
    ["Overview", [["/", "Dashboard", LayoutDashboard], ["/incidents/new", "Report incident", PlusCircle], ["/incidents", "My incidents", ListChecks]]],
    ["Account", [["/notifications", "Notifications", Bell], ["/profile", "Profile", UserCircle]]],
  ],
  TECHNICIAN: [
    ["Work", [["/", "My dashboard", LayoutDashboard], ["/incidents", "Incident queue", ListChecks], ["/incidents/new", "Report incident", PlusCircle]]],
    ["Account", [["/notifications", "Notifications", Bell], ["/profile", "Profile and availability", UserCircle]]],
  ],
  ADMIN: [
    ["Overview", [["/", "Dashboard", LayoutDashboard], ["/incidents", "All incidents", ListChecks], ["/incidents/new", "Report incident", PlusCircle], ["/sla-monitor", "SLA monitor", Activity], ["/reports", "Reports", BarChart3]]],
    ["Administration", [["/users", "Users", Users], ["/teams", "Technicians and teams", Wrench], ["/services", "Services", Server], ["/categories", "Categories", Tags], ["/sla-policies", "SLA policies", Timer], ["/settings", "Settings", Settings]]],
    ["Governance", [["/audit-log", "Audit log", ScrollText], ["/email-outbox", "E-mail outbox", Mail]]],
    ["Account", [["/notifications", "Notifications", Bell], ["/profile", "Profile", UserCircle]]],
  ],
};

function useOutside(ref, fn) {
  useEffect(() => {
    const h = (e) => ref.current && !ref.current.contains(e.target) && fn();
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, [ref, fn]);
}

export default function AppLayout() {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const loc = useLocation();
  const [open, setOpen] = useState(false);
  const [bell, setBell] = useState(false);
  const [menu, setMenu] = useState(false);
  const [confirmOut, setConfirmOut] = useState(false);
  const [notes, setNotes] = useState({ items: [], unread_count: 0 });
  const bellRef = useRef(null), menuRef = useRef(null);
  useOutside(bellRef, () => setBell(false));
  useOutside(menuRef, () => setMenu(false));

  const load = () => get("/notifications", { limit: 8 }).then(setNotes).catch(() => {});
  useEffect(() => { load(); }, [loc.pathname]);
  usePolling(load, 30000);
  useEffect(() => { setOpen(false); }, [loc.pathname]);

  const readAll = async () => { await post("/notifications/read-all"); load(); };
  const openNote = async (n) => {
    if (!n.is_read) await post(`/notifications/${n.id}/read`).catch(() => {});
    setBell(false); load();
    if (n.incident_number) nav(`/incidents/${n.incident_number}`);
  };

  return (
    <div className="app">
      <aside className={`sidebar ${open ? "open" : ""}`}>
        <div className="brand"><div className="logo"><ShieldCheck size={19} /></div>I-ITSM</div>
        <nav className="nav" aria-label="Main">
          {(NAV[user.role] || []).map(([group, links]) => (
            <div key={group}>
              <div className="nav-group">{group}</div>
              {links.map(([to, label, Icon]) => (
                <NavLink key={to} to={to} end={to === "/" || to === "/incidents"} className={({ isActive }) => (isActive ? "active" : "")}>
                  <Icon size={18} />{label}
                  {to === "/notifications" && notes.unread_count > 0 && <span className="count">{notes.unread_count}</span>}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>
        <div style={{ padding: 14, fontSize: 12, color: "#64748b" }}>Signed in as {user.role.toLowerCase()}</div>
      </aside>

      <div className="main">
        <header className="topbar">
          <button className="icon-btn menu-btn" onClick={() => setOpen(!open)} aria-label="Toggle menu"><Menu size={18} /></button>
          <div className="grow" />
          <div className="rel" ref={bellRef}>
            <button className="icon-btn" aria-label="Notifications" onClick={() => { setBell(!bell); setMenu(false); }}>
              <Bell size={18} />{notes.unread_count > 0 && <span className="dot">{notes.unread_count > 99 ? "99+" : notes.unread_count}</span>}
            </button>
            {bell && (
              <div className="dropdown" style={{ width: 370 }}>
                <div className="card-h"><h3>Notifications</h3><button className="btn sm ghost" onClick={readAll} disabled={!notes.unread_count}><CheckCheck size={14} />Mark all read</button></div>
                <div style={{ maxHeight: 360, overflow: "auto" }}>
                  {notes.items.length === 0 && <div className="center" style={{ padding: 28 }}><Inbox size={28} />No notifications yet</div>}
                  {notes.items.map((n) => (
                    <button key={n.id} className="item" style={{ alignItems: "flex-start", background: n.is_read ? undefined : "var(--brand-l)" }} onClick={() => openNote(n)}>
                      <div><div style={{ fontWeight: n.is_read ? 500 : 700 }}>{n.subject}</div><div className="small muted">{n.body}</div><div className="small muted">{fmtShort(n.created_at)}</div></div>
                    </button>
                  ))}
                </div>
                <div style={{ padding: 10, textAlign: "center", borderTop: "1px solid var(--line)" }}><button className="btn sm ghost" onClick={() => { setBell(false); nav("/notifications"); }}>View all notifications</button></div>
              </div>
            )}
          </div>
          <div className="rel" ref={menuRef}>
            <button className="profile-btn" onClick={() => { setMenu(!menu); setBell(false); }} aria-haspopup="menu" aria-expanded={menu}>
              <div className="avatar">{user.full_name.charAt(0)}</div>
              <div style={{ textAlign: "left" }}><div style={{ fontWeight: 600, lineHeight: 1.2 }}>{user.full_name}</div><div className="small muted">{user.role.toLowerCase()}</div></div>
              <ChevronDown size={16} />
            </button>
            {menu && (
              <div className="dropdown" role="menu">
                <button className="item" onClick={() => { setMenu(false); nav("/profile"); }}><UserCircle size={16} />My profile</button>
                <button className="item" onClick={() => { setMenu(false); nav("/notifications"); }}><Bell size={16} />Notifications</button>
                <button className="item" style={{ color: "var(--bad)" }} onClick={() => { setMenu(false); setConfirmOut(true); }}><LogOut size={16} />Sign out</button>
              </div>
            )}
          </div>
        </header>
        <main className="content"><Outlet /></main>
      </div>
      {confirmOut && <ConfirmDialog title="Sign out" message="Do you want to sign out of I-ITSM?" confirmLabel="Sign out" onCancel={() => setConfirmOut(false)} onConfirm={() => { logout(); nav("/login"); }} />}
    </div>
  );
}
