import { Navigate, Route, Routes } from "react-router-dom";
import ProtectedRoute from "./components/ProtectedRoute";
import AppLayout from "./layouts/AppLayout";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import CreateIncident from "./pages/CreateIncident";
import IncidentList from "./pages/IncidentList";
import IncidentDetail from "./pages/IncidentDetail";
import Notifications, { EmailOutbox } from "./pages/Notifications";
import Users from "./pages/Users";
import Teams from "./pages/Teams";
import Services from "./pages/Services";
import Categories from "./pages/Categories";
import SlaPolicies from "./pages/SlaPolicies";
import Settings from "./pages/Settings";
import Reports from "./pages/Reports";
import AuditLog from "./pages/AuditLog";
import SlaMonitor from "./pages/SlaMonitor";
import Profile from "./pages/Profile";
import NotFound from "./pages/NotFound";

const A = ["ADMIN"];
const guard = (el, roles) => <ProtectedRoute roles={roles}>{el}</ProtectedRoute>;

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route element={<ProtectedRoute><AppLayout /></ProtectedRoute>}>
        <Route index element={<Dashboard />} />
        <Route path="incidents" element={<IncidentList />} />
        <Route path="incidents/new" element={<CreateIncident />} />
        <Route path="incidents/:number" element={<IncidentDetail />} />
        <Route path="notifications" element={<Notifications />} />
        <Route path="profile" element={<Profile />} />
        <Route path="users" element={guard(<Users />, A)} />
        <Route path="teams" element={guard(<Teams />, A)} />
        <Route path="services" element={guard(<Services />, A)} />
        <Route path="categories" element={guard(<Categories />, A)} />
        <Route path="sla-policies" element={guard(<SlaPolicies />, A)} />
        <Route path="settings" element={guard(<Settings />, A)} />
        <Route path="reports" element={guard(<Reports />, A)} />
        <Route path="audit-log" element={guard(<AuditLog />, A)} />
        <Route path="email-outbox" element={guard(<EmailOutbox />, A)} />
        <Route path="sla-monitor" element={guard(<SlaMonitor />, A)} />
        <Route path="*" element={<NotFound />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
