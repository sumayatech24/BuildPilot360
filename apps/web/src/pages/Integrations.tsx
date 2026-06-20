import { CatalogView } from "../components/CatalogView";

export default function Integrations() {
  return (
    <CatalogView
      category="api_integration"
      title="API integrations"
      subtitle="Provider-neutral connectors: PM tools, Git, cloud, CI/CD, AI providers and data platforms."
      filters={["q", "priority"]}
      columns={[
        { label: "ID", col: "item_id", width: "100px" },
        { label: "Category", col: "domain", width: "170px" },
        { label: "Provider", col: "title", width: "160px" },
        { label: "Purpose", dataKey: "Purpose" },
        { label: "Auth", dataKey: "Auth Type", width: "130px" },
        { label: "Priority", col: "priority", width: "100px", badge: true },
      ]}
    />
  );
}
