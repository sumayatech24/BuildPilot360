import { CatalogView } from "../components/CatalogView";

export default function Nfrs() {
  return (
    <CatalogView
      category="nfr"
      title="NFRs & guardrails"
      subtitle="Security, performance, reliability, scalability, AI governance and compliance controls."
      filters={["q"]}
      columns={[
        { label: "ID", col: "item_id", width: "100px" },
        { label: "Category", col: "domain", width: "160px", badge: true },
        { label: "Requirement", col: "title" },
        { label: "Acceptance measure", dataKey: "Acceptance Measure" },
      ]}
    />
  );
}
