import { CatalogView } from "../components/CatalogView";

export default function Features() {
  return (
    <CatalogView
      category="feature"
      title="Feature backlog"
      subtitle="Every planned capability across all 27 modules, straight from the blueprint."
      filters={["q", "module_id", "priority", "phase"]}
      columns={[
        { label: "ID", col: "item_id", width: "120px" },
        { label: "Module", col: "module_id", width: "80px" },
        { label: "Feature", col: "title" },
        { label: "Domain", col: "domain", width: "150px" },
        { label: "Phase", col: "phase", width: "100px" },
        { label: "Priority", col: "priority", width: "90px", badge: true },
      ]}
    />
  );
}
