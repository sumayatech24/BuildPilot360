import { CatalogView } from "../components/CatalogView";

export default function Stories() {
  return (
    <CatalogView
      category="user_story"
      title="User stories"
      subtitle="The full user-story backlog with personas, acceptance criteria and DoD."
      filters={["q", "priority"]}
      columns={[
        { label: "ID", col: "item_id", width: "120px" },
        { label: "Persona", dataKey: "Persona", width: "150px" },
        { label: "Story", col: "title" },
        { label: "Priority", col: "priority", width: "90px", badge: true },
      ]}
    />
  );
}
