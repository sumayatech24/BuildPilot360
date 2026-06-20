import { useEffect, useState } from "react";
import { api, LifecycleStage, Story } from "../api";

export default function Board() {
  const [stories, setStories] = useState<Story[]>([]);
  const [stages, setStages] = useState<LifecycleStage[]>([]);
  const [error, setError] = useState("");

  const load = () => {
    api.stories().then(setStories).catch((e) => setError((e as Error).message));
    api.lifecycle().then(setStages).catch(() => {});
  };
  useEffect(load, []);

  const advance = async (story: Story) => {
    const idx = stages.findIndex((s) => s.status_code === story.status_code);
    const next = stages[idx + 1];
    if (!next) return;
    try {
      await api.updateStoryStatus(story.id, next.status_code);
      load();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  // Show the first 6 lifecycle columns to keep the board readable.
  const columns = stages.slice(0, 6);
  const byStatus = (code: string) => stories.filter((s) => s.status_code === code);
  const overflow = stories.filter(
    (s) => !columns.some((c) => c.status_code === s.status_code)
  );

  return (
    <>
      <div className="topbar">
        <div>
          <h1>Backlog board</h1>
          <p>Stories flow through the 16-stage lifecycle. Click → to advance a story.</p>
        </div>
      </div>
      {error && <div className="error">{error}</div>}
      {stories.length === 0 && (
        <div className="card"><p className="muted">No stories yet. Generate a backlog from Requirement intake.</p></div>
      )}
      <div className="board">
        {columns.map((col) => (
          <div className="column" key={col.status_code}>
            <h4>{col.stage_name} <span className="count">({byStatus(col.status_code).length})</span></h4>
            {byStatus(col.status_code).map((s) => (
              <div className="story-card" key={s.id}>
                <div className="title">{s.title}</div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span className={"badge" + (s.priority === "P0" ? " p0" : "")}>{s.priority}</span>
                  <button className="btn secondary" style={{ padding: "4px 10px" }}
                    onClick={() => advance(s)}>Advance →</button>
                </div>
              </div>
            ))}
          </div>
        ))}
        {overflow.length > 0 && (
          <div className="column">
            <h4>Later stages <span className="count">({overflow.length})</span></h4>
            {overflow.map((s) => (
              <div className="story-card" key={s.id}>
                <div className="title">{s.title}</div>
                <span className="muted">{s.status_code}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  );
}
