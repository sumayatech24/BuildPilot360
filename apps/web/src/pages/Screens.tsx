import { CatalogView } from "../components/CatalogView";

export default function Screens() {
  return (
    <CatalogView
      category="screen"
      title="Screen inventory"
      subtitle="Every screen across web, desktop and mobile apps with its API dependencies."
      filters={["q", "priority"]}
      columns={[
        { label: "ID", col: "item_id", width: "100px" },
        { label: "App", col: "domain", width: "90px", badge: true },
        { label: "Screen", col: "title" },
        { label: "Main functions", dataKey: "Main Functions" },
        { label: "Priority", col: "priority", width: "100px", badge: true },
      ]}
    />
  );
}
