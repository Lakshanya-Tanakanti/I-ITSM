import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { UserPlus } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { errMsg, post } from "../services/api";
import { Alert, Field } from "./../components/ui";
import { AuthHero } from "./Login";

export default function Register() {
  const { user, login } = useAuth();
  const toast = useToast();
  const nav = useNavigate();
  const [f, setF] = useState({ full_name: "", email: "", department: "", password: "", confirm: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  if (user) return <Navigate to="/" replace />;
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const mismatch = f.confirm && f.confirm !== f.password;

  const submit = async (e) => {
    e.preventDefault();
    if (f.password !== f.confirm) return setError("The passwords do not match.");
    setError(""); setBusy(true);
    try {
      await post("/auth/register", { full_name: f.full_name, email: f.email.trim(), department: f.department || null, password: f.password });
      await login(f.email.trim(), f.password);
      toast.success("Account created. Welcome to I-ITSM!");
      nav("/", { replace: true });
    } catch (err) { setError(errMsg(err)); } finally { setBusy(false); }
  };

  return (
    <div className="auth">
      <AuthHero />
      <div className="auth-form">
        <form className="auth-box" onSubmit={submit}>
          <h1>Create your account</h1>
          <p className="muted" style={{ margin: "4px 0 20px" }}>Registration creates an employee account. Technician and admin roles are assigned by an administrator.</p>
          {error && <Alert kind="err">{error}</Alert>}
          <Field label="Full name"><input value={f.full_name} onChange={set("full_name")} required minLength={2} autoFocus /></Field>
          <Field label="E-mail"><input type="email" value={f.email} onChange={set("email")} required /></Field>
          <Field label="Department (optional)"><input value={f.department} onChange={set("department")} /></Field>
          <Field label="Password" hint="At least 8 characters with at least one letter and one number."><input type="password" value={f.password} onChange={set("password")} required autoComplete="new-password" /></Field>
          <Field label="Confirm password" error={mismatch ? "Passwords do not match." : null}><input type="password" value={f.confirm} onChange={set("confirm")} required autoComplete="new-password" /></Field>
          <button className="btn primary" style={{ width: "100%", justifyContent: "center" }} disabled={busy || mismatch}><UserPlus size={16} />{busy ? "Creating..." : "Create account"}</button>
          <p className="small" style={{ textAlign: "center" }}>Already registered? <Link to="/login">Sign in</Link></p>
        </form>
      </div>
    </div>
  );
}
