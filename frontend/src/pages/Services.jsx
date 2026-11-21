import ConfigPage from "../components/ConfigPage";
const CRIT = [1, 2, 3, 4, 5].map((n) => [n, `${n} - ${["Minimal", "Low", "Moderate", "High", "Mission critical"][n - 1]}`]);
export default function Services() {
  return <ConfigPage title="Services" subtitle="Business services that incidents are reported against. Criticality feeds the priority score." path="/services" noun="Service"
    defaults={{ name: "", description: "", business_criticality: 3 }}
    toBody={(f) => ({ name: f.name, description: f.description || null, business_criticality: Number(f.business_criticality) })}
    fields={[{ key: "name", label: "Name", required: true }, { key: "description", label: "Description", type: "textarea" }, { key: "business_criticality", label: "Business criticality", type: "select", options: CRIT }]}
    columns={[{ label: "Service", render: (r) => <b>{r.name}</b> }, { label: "Description", render: (r) => r.description || "-" }, { label: "Criticality", render: (r) => <span className="badge b-indigo">{r.business_criticality} / 5</span> }]} />;
}
