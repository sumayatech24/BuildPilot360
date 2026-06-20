// Client-side data layer used when no backend is configured (e.g. the static Vercel build).
// Serves the full blueprint from the bundled JSON and persists operational data in localStorage,
// so the deployed site is fully functional with no server or database.
import type {
  Analysis, CatalogItem, CatalogPage, CatalogSummary, CurrentUser,
  LifecycleStage, ModuleInfo, ModuleRecord, Project, Requirement, Story,
} from "./api";

const uuid = () => (crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2));

const DEMO_USER: CurrentUser = {
  id: "local-owner", tenant_id: "local", email: "owner@buildpilot360.dev",
  full_name: "Platform Owner (demo)", roles: ["Owner"], permissions: ["*"],
};

// ---- localStorage helpers ----
const read = <T>(key: string, fallback: T): T => {
  try { const v = localStorage.getItem(`bp360:${key}`); return v ? (JSON.parse(v) as T) : fallback; }
  catch { return fallback; }
};
const write = <T>(key: string, value: T) => localStorage.setItem(`bp360:${key}`, JSON.stringify(value));

// ---- blueprint loading ----
let _bp: Record<string, Record<string, string>[]> | null = null;
async function blueprint() {
  if (_bp) return _bp;
  const res = await fetch(`${import.meta.env.BASE_URL}blueprint.json`);
  if (!res.ok) throw new Error("Could not load blueprint data");
  _bp = await res.json();
  return _bp!;
}

const first = (row: Record<string, string>, ...keys: string[]) => {
  for (const k of keys) if (row[k]) return row[k];
  return undefined;
};

const SHEET: Record<string, string> = {
  module: "modules", feature: "features", user_story: "user_stories", nfr: "nfrs",
  api_integration: "api_integrations", screen: "screens", roadmap: "roadmap",
  database_table: "database_schema", ai_prompt: "ai_prompts", build_prompt: "build_prompts",
  token_safe: "token_safe", verification_gate: "verification_matrix",
  milestone_type: "milestone_planner", gcp_matrix: "gcp_data_matrix",
  workflow_config: "workflow_config", story_lifecycle: "story_lifecycle",
};

function mapItem(category: string, row: Record<string, string>): CatalogItem {
  const m: Partial<CatalogItem> = { id: uuid(), category, data: row };
  switch (category) {
    case "module":
      return { ...m, item_id: first(row, "Module ID") ?? null, module_id: first(row, "Module ID") ?? null,
        title: first(row, "Module") ?? null, domain: first(row, "Domain") ?? null,
        phase: first(row, "MVP Priority") ?? null, priority: first(row, "MVP Priority") ?? null, status: null } as CatalogItem;
    case "feature":
      return { ...m, item_id: first(row, "Feature ID") ?? null, module_id: first(row, "Module ID") ?? null,
        title: first(row, "Feature Title") ?? null, domain: first(row, "Domain") ?? null,
        phase: first(row, "Phase") ?? null, priority: first(row, "Priority") ?? null, status: first(row, "Status") ?? null } as CatalogItem;
    case "user_story":
      return { ...m, item_id: first(row, "Story ID") ?? null, module_id: first(row, "Linked Feature ID") ?? null,
        title: first(row, "User Story") ?? null, domain: null, phase: null, priority: first(row, "Priority") ?? null, status: null } as CatalogItem;
    case "nfr":
      return { ...m, item_id: first(row, "NFR ID") ?? null, module_id: null, title: first(row, "Requirement") ?? null,
        domain: first(row, "Category") ?? null, phase: null, priority: null, status: null } as CatalogItem;
    case "api_integration":
      return { ...m, item_id: first(row, "Integration ID") ?? null, module_id: null, title: first(row, "Provider") ?? null,
        domain: first(row, "Category") ?? null, phase: null, priority: first(row, "Implementation Priority") ?? null, status: null } as CatalogItem;
    case "screen":
      return { ...m, item_id: first(row, "Screen ID") ?? null, module_id: null, title: first(row, "Screen Name") ?? null,
        domain: first(row, "App") ?? null, phase: null, priority: first(row, "Priority") ?? null, status: null } as CatalogItem;
    case "roadmap":
      return { ...m, item_id: null, module_id: null, title: first(row, "Milestone") ?? null, domain: null,
        phase: first(row, "Phase") ?? null, priority: null, status: null } as CatalogItem;
    default:
      return { ...m, item_id: null, module_id: null,
        title: first(row, "Provider/Tool", "Verification Gate", "Milestone Type", "Prompt Name", "Table Name", "Capability", "Feature", "Lifecycle Stage", "Config Area") ?? null,
        domain: first(row, "Area", "Domain", "Config Area") ?? null, phase: null,
        priority: first(row, "Priority") ?? null, status: null } as CatalogItem;
  }
}

async function items(category: string): Promise<CatalogItem[]> {
  const bp = await blueprint();
  const rows = bp[SHEET[category]] || [];
  return rows.map((r) => mapItem(category, r));
}

// ---- lifecycle ----
async function lifecycleStages(): Promise<LifecycleStage[]> {
  const bp = await blueprint();
  return (bp.story_lifecycle || []).map((r) => ({
    stage_no: Number(r["Stage No"]) || 0,
    stage_name: r["Lifecycle Stage"] || "",
    status_code: r["Status Code"] || "",
    primary_owner: r["Primary Owner"] || "",
    verifier: r["Verifier/Approver"] || "",
    exit_criteria: r["Exit Criteria"] || "",
  })).sort((a, b) => a.stage_no - b.stage_no);
}

// ---- deterministic analyzer (TS port of the backend StubProvider) ----
function analyzeLocal(title: string, raw: string): Analysis {
  const text = raw.trim();
  const low = text.toLowerCase();
  const words = (text.match(/[A-Za-z']+/g) || []).length;
  let classification = "feature";
  if (/(fix|bug|error|broken)/.test(low)) classification = "bug";
  else if (/(must|shall|compliance|regulat)/.test(low)) classification = "compliance";
  else if (/(spike|investigate|research)/.test(low)) classification = "spike";
  const confidence = Math.min(0.95, 0.45 + words / 120);
  const gaps: string[] = [];
  if (words < 12) gaps.push("Requirement is very short; scope and intent may be ambiguous.");
  if (!/\b(user|admin|customer|role|persona|actor)\b/.test(low)) gaps.push("No clear actor/persona identified.");
  if (!/\b(so that|because|in order to|goal)\b/.test(low)) gaps.push("Business value / outcome not explicitly stated.");
  const nfrMap: [RegExp, string][] = [
    [/secure/, "Security: authn/authz, encryption, secret handling"],
    [/performance|real-time/, "Performance: define p95 latency / throughput targets"],
    [/scal/, "Scalability: horizontal scaling + partitioning strategy"],
    [/audit/, "Compliance: audit trail + traceability"],
    [/integrat/, "Reliability: retry, idempotency, dead-letter handling"],
  ];
  let nfrs = nfrMap.filter(([re]) => re.test(low)).map(([, v]) => v);
  if (nfrs.length === 0) nfrs = ["Security: tenant isolation + RBAC", "Compliance: audit logging"];
  const acceptance_criteria = [
    "User has the required permission in the active tenant/project.",
    "Inputs are validated through the API before persistence.",
    "Changes are stored and an audit log captures before/after values.",
    "UI reflects success and error states.",
    "No hardcoded demo data; all options are config/API driven.",
  ];
  const suggested_stories = [
    { capability: "Create", persona: "Admin", title: `Create for ${title}` },
    { capability: "Read/Search", persona: "Product Owner", title: `Read/Search for ${title}` },
    { capability: "Update", persona: "Business Analyst", title: `Update for ${title}` },
    { capability: "Delete/Archive", persona: "Delivery Manager", title: `Delete/Archive for ${title}` },
  ];
  return {
    id: uuid(), requirement_id: "", summary:
      `'${title}' is classified as a ${classification}. Captured ${words} words. ${gaps.length} gap(s); confidence ${(confidence * 100).toFixed(0)}%.`,
    classification, confidence, gaps,
    questions: [`Who is the primary persona for '${title}'?`, "What is the measurable success outcome?", "Are there compliance, data-residency or audit constraints?"],
    nfrs, acceptance_criteria, suggested_stories, provider: "local-stub", model: "deterministic-v1", tokens_used: 0,
  };
}

// ---- the api surface ----
export const localApi = {
  login: async (_e: string, _p: string) => ({ access_token: "local-demo-token" }),
  me: async () => DEMO_USER,

  projects: async () => read<Project[]>("projects", []),
  createProject: async (body: { name: string; code: string; description?: string }) => {
    const list = read<Project[]>("projects", []);
    const p: Project = { id: uuid(), status: "active", description: body.description, ...body };
    write("projects", [...list, p]);
    return p;
  },

  requirements: async (projectId?: string) =>
    read<Requirement[]>("requirements", []).filter((r) => !projectId || r.project_id === projectId),
  createRequirement: async (body: { project_id: string; title: string; raw_text: string }) => {
    const list = read<Requirement[]>("requirements", []);
    const r: Requirement = { id: uuid(), source: "text", status: "captured", priority: "P2", ...body };
    write("requirements", [...list, r]);
    return r;
  },
  analyze: async (id: string) => {
    const req = read<Requirement[]>("requirements", []).find((r) => r.id === id)!;
    const a = analyzeLocal(req.title, req.raw_text); a.requirement_id = id;
    write(`analysis:${id}`, a);
    const reqs = read<Requirement[]>("requirements", []).map((r) => r.id === id ? { ...r, status: "analyzed" } : r);
    write("requirements", reqs);
    return a;
  },
  generateBacklog: async (id: string) => {
    const a = read<Analysis | null>(`analysis:${id}`, null);
    const req = read<Requirement[]>("requirements", []).find((r) => r.id === id)!;
    const stories = read<Story[]>("stories", []);
    const created: string[] = [];
    (a?.suggested_stories || []).forEach((s) => {
      const story: Story = {
        id: uuid(), project_id: req.project_id, requirement_id: id, title: s.title,
        persona: s.persona, story_text: `As a ${s.persona}, I want to ${s.capability} in ${req.title}.`,
        acceptance_criteria: a?.acceptance_criteria || [], priority: req.priority, status_code: "STORY_DRAFT",
      };
      stories.push(story); created.push(story.id);
    });
    write("stories", stories);
    return { requirement_id: id, created_story_ids: created };
  },

  stories: async (projectId?: string) =>
    read<Story[]>("stories", []).filter((s) => !projectId || s.project_id === projectId),
  lifecycle: lifecycleStages,
  updateStoryStatus: async (id: string, status_code: string) => {
    const list = read<Story[]>("stories", []);
    const updated = list.map((s) => s.id === id ? { ...s, status_code } : s);
    write("stories", updated);
    return updated.find((s) => s.id === id)!;
  },

  catalogSummary: async (): Promise<CatalogSummary> => {
    const bp = await blueprint();
    const counts: Record<string, number> = {};
    for (const [cat, sheet] of Object.entries(SHEET)) counts[cat] = (bp[sheet] || []).length;
    return {
      counts,
      totals: {
        modules: counts.module, features: counts.feature, user_stories: counts.user_story,
        nfrs: counts.nfr, api_integrations: counts.api_integration, screens: counts.screen,
      },
    };
  },
  catalog: async (category: string, params: Record<string, string | number> = {}): Promise<CatalogPage> => {
    let list = await items(category);
    const p = params as Record<string, string>;
    if (p.module_id) list = list.filter((i) => i.module_id === p.module_id);
    if (p.phase) list = list.filter((i) => i.phase === p.phase);
    if (p.priority) list = list.filter((i) => i.priority === p.priority);
    if (p.domain) list = list.filter((i) => i.domain === p.domain);
    if (p.q) list = list.filter((i) => (i.title || "").toLowerCase().includes(String(p.q).toLowerCase()));
    const limit = Number(params.limit ?? 200), offset = Number(params.offset ?? 0);
    return { category, total: list.length, limit, offset, items: list.slice(offset, offset + limit) };
  },

  modules: async (): Promise<ModuleInfo[]> => {
    const list = await items("module");
    return list.map((m) => ({
      module_id: m.item_id || "", name: m.title || "", domain: m.domain || "",
      mvp_priority: m.priority || "", data: m.data,
    }));
  },
  moduleRecords: async (moduleId: string) => {
    const recs = read<ModuleRecord[]>(`records:${moduleId}`, []);
    return { module_id: moduleId, total: recs.length, items: recs };
  },
  createModuleRecord: async (moduleId: string, body: { title: string; priority?: string; status?: string; data?: Record<string, unknown> }) => {
    const recs = read<ModuleRecord[]>(`records:${moduleId}`, []);
    const rec: ModuleRecord = {
      id: uuid(), module_id: moduleId, project_id: null, title: body.title,
      status: body.status || "active", priority: body.priority || "P2", data: body.data || {}, version: 1,
    };
    write(`records:${moduleId}`, [...recs, rec]);
    return rec;
  },
  deleteModuleRecord: async (moduleId: string, recordId: string) => {
    const recs = read<ModuleRecord[]>(`records:${moduleId}`, []).filter((r) => r.id !== recordId);
    write(`records:${moduleId}`, recs);
  },
};
