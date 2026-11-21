import { useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { ShieldCheck, LogIn, Gauge, Bell, Brain } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { errMsg } from "../services/api";
import { Alert, Field } from "../components/ui";

const DEMO = [
  ["Admin", "admin@iitsm.example.com", "Admin@123"],
  ["Technician", "arjun.kapoor@iitsm.example.com", "Tech@1234"],
  ["Technician (apps)", "meera.joshi@iitsm.example.com", "Tech@1234"],
  ["Employee", "rahul.verma@iitsm.example.com", "Employee@123"],
];

export function AuthHero() {
  return (
    <div className="auth-hero">
      <div className="row"><ShieldCheck size={34} /><h1 style={{ fontSize: 30 }}>I-ITSM</h1></div>
      <h2 style={{ fontSize: 22, fontWeight: 500 }}>Intelligent IT Service Management and Incident Resolution</h2>
      <ul style={{ listStyle: "none", padding: 0, opacity: .95 }}>
        <li className="row"><Gauge size={18} />Priority scoring and SLA tracking with live countdowns</li>
        <li className="row"><Brain size={18} />Smart category suggestions, duplicate detection and technician matching</li>
        <li className="row"><Bell size={18} />In-app and simulated e-mail notifications with a full audit trail</li>
      </ul>
    </div>
  );
}

export default function Login() {
  const { user, login } = useAuth();
  const nav = useNavigate();
  const loc = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  if (user) return <Navigate to="/" replace />;

  const submit = async (e) => {
    e.preventDefault();
    setError(""); setBusy(true);
    try { await login(email.trim(), password); nav(loc.state?.from || "/", { replace: true }); }
    catch (err) { setError(errMsg(err)); }
    finally { setBusy(false); }
  };

  return (
    <div className="auth">
      <AuthHero />
      <div className="auth-form">
        <form className="auth-box" onSubmit={submit} noValidate>
          <h1>Welcome back</h1>
          <p className="muted" style={{ margin: "4px 0 22px" }}>Sign in to your service desk account.</p>
          {error && <Alert kind="err">{error}</Alert>}
          <Field label="E-mail"><input type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="username" required autoFocus /></Field>
          <Field label="Password"><input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required /></Field>
          <button className="btn primary" style={{ width: "100%", justifyContent: "center" }} disabled={busy || !email || !password}><LogIn size={16} />{busy ? "Signing in..." : "Sign in"}</button>
          <p className="small" style={{ textAlign: "center" }}>New employee? <Link to="/register">Create an account</Link></p>
          <div className="demo">
            <div className="small muted"><b>Development demo accounts only.</b> Click to fill the form. Do not use these in production.</div>
            {DEMO.map(([r, em, pw]) => <button type="button" key={em} className="small" onClick={() => { setEmail(em); setPassword(pw); }}>{r}: {em}</button>)}
          </div>
        </form>
      </div>
    </div>
  );
}
