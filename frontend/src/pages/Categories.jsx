import ConfigPage from "../components/ConfigPage";
export default function Categories() {
  return <ConfigPage title="Categories" subtitle="Keywords drive the automatic category suggestion. Edit them here, no code change needed." path="/categories" noun="Category"
    defaults={{ name: "", description: "", keywords: "" }}
    toBody={(f) => ({ name: f.name, description: f.description || null, keywords: f.keywords || null })}
    fields={[{ key: "name", label: "Name", required: true }, { key: "description", label: "Description", type: "textarea" }, { key: "keywords", label: "Keywords", type: "textarea", hint: "Comma separated, for example: vpn, wifi, router" }]}
    columns={[{ label: "Category", render: (r) => <b>{r.name}</b> }, { label: "Description", render: (r) => r.description || "-" },
      { label: "Keywords", render: (r) => (r.keywords || "").split(",").filter(Boolean).slice(0, 8).map((k) => <span key={k} className="chip">{k.trim()}</span>) }]} />;
}
