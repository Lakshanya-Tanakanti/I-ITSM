import { useState } from "react";
import { KeyRound, Save } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { errMsg, patch, post } from "../services/api";
import { Alert, Card, Field, PageHeader } from "../components/ui";

export default function Profile() {
  const { user, refresh } = useAuth();
  const toast = useToast();
  const [f, setF] = useState({ full_name: user.full_name, department: user.department || "" });
  const [pw, setPw] = useState({ current_password: "", new_password: "", confirm: "" });
  const [e1, setE1] = useState(""), [e2, setE2] = useState("");
  const [b1, setB1] = useState(false), [b2, setB2] = useState(false);
  const tp = user.technician_profile;

  const saveProfile = async () => { setB1(true); setE1(""); try { await patch("/auth/me", { full_name: f.full_name, department: f.department || null }); await refresh(); toast.success("Profile updated"); } catch (e) { setE1(errMsg(e)); } finally { setB1(false); } };
  const changePw = async () => {
    setE2("");
    if (pw.new_password !== pw.confirm) return setE2("The new passwords do not match.");
    setB2(true);
    try { await post("/auth/change-password", { current_password: pw.current_password, new_password: pw.new_password }); toast.success("Password changed"); setPw({ current_password: "", new_password: "", confirm: "" }); }
    catch (e) { setE2(errMsg(e)); } finally { setB2(false); }
  };
  const setAvail = async (v) => { try { await patch("/technicians/me/availability", { is_available: v }); await refresh(); toast.success(v ? "You are now available" : "You are now unavailable"); } catch (e) { toast.error(errMsg(e)); } };

  return (
    <>
      <PageHeader title="My profile" subtitle={`${user.email} | ${user.role.toLowerCase()} | ${user.employee_code || ""}`} />
      <div className="grid g2">
        <Card title="Personal details">
          {e1 && <Alert kind="err">{e1}</Alert>}
          <Field label="Full name"><input value={f.full_name} onChange={(e) => setF({ ...f, full_name: e.target.value })} /></Field>
          <Field label="Department"><input value={f.department} onChange={(e) => setF({ ...f, department: e.target.value })} /></Field>
          <button className="btn primary" disabled={b1 || f.full_name.trim().length < 2} onClick={saveProfile}><Save size={15} />Save changes</button>
        </Card>
        <Card title="Change password">
          {e2 && <Alert kind="err">{e2}</Alert>}
          <Field label="Current password"><input type="password" autoComplete="current-password" value={pw.current_password} onChange={(e) => setPw({ ...pw, current_password: e.target.value })} /></Field>
          <Field label="New password" hint="At least 8 characters with at least one letter and one number."><input type="password" autoComplete="new-password" value={pw.new_password} onChange={(e) => setPw({ ...pw, new_password: e.target.value })} /></Field>
          <Field label="Confirm new password"><input type="password" autoComplete="new-password" value={pw.confirm} onChange={(e) => setPw({ ...pw, confirm: e.target.value })} /></Field>
          <button className="btn primary" disabled={b2 || !pw.current_password || !pw.new_password} onClick={changePw}><KeyRound size={15} />Change password</button>
        </Card>
        {tp && (
          <Card title="Technician settings">
            <div className="row between"><div><b>Availability</b><div className="small muted">Unavailable technicians do not receive new automatic assignments.</div></div>
              <button className={`btn ${tp.is_available ? "ok" : ""}`} onClick={() => setAvail(!tp.is_available)}>{tp.is_available ? "Available" : "Unavailable"}</button></div>
            <hr style={{ border: 0, borderTop: "1px solid var(--line)" }} />
            <dl className="kv"><dt>Team</dt><dd>{tp.team_name || "-"}</dd><dt>Experience</dt><dd>{tp.experience_years} years</dd><dt>Workload limit</dt><dd>{tp.workload_limit}</dd>
              <dt>Skills</dt><dd>{tp.skills.map((s) => <span className="chip" key={s.category_id}>{s.category_name} {s.proficiency}/5</span>)}</dd></dl>
          </Card>
        )}
      </div>
    </>
  );
}
