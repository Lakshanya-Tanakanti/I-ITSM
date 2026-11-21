import { Link } from "react-router-dom";
import { Compass } from "lucide-react";
export default function NotFound() {
  return <div className="center"><Compass size={44} /><h1 style={{ color: "var(--ink)", marginTop: 10 }}>Page not found</h1><p>The page you are looking for does not exist or you do not have access to it.</p><Link className="btn primary" to="/">Back to dashboard</Link></div>;
}
