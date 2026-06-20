// Thin API client. Base URL is config-driven (Vercel env / Electron injected global).
// When no backend is configured, the app falls back to a fully client-side data layer
// (localApi) so the static build is a working app with no server required.
import { localApi } from "./localApi";

const w = window as unknown as { __BP360_API_BASE__?: string };
const CONFIGURED_BASE =
  w.__BP360_API_BASE__ || (import.meta.env.VITE_API_BASE_URL as string) || "";
export const USE_LOCAL = !CONFIGURED_BASE;
export const API_BASE = CONFIGURED_BASE || "http://localhost:8000";

const TOKEN_KEY = "bp360_token";

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t: string) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = tokenStore.get();
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail || detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export interface CurrentUser {
  id: string;
  tenant_id: string;
  email: string;
  full_name: string;
  roles: string[];
  permissions: string[];
}
export interface Project { id: string; name: string; code: string; description?: string; status: string; repo_url?: string | null; tech_stack?: string | null; default_branch?: string; }
export interface Requirement { id: string; project_id: string; title: string; raw_text: string; source: string; status: string; priority: string; }
export interface Analysis {
  id: string; requirement_id: string; summary: string; classification: string; confidence: number;
  gaps: string[]; questions: string[]; nfrs: string[]; acceptance_criteria: string[];
  suggested_stories: { capability: string; persona: string; title: string }[];
  provider: string; model: string | null; tokens_used: number;
}
export interface Story {
  id: string; project_id: string; requirement_id: string | null; title: string;
  persona: string | null; story_text: string | null; acceptance_criteria: string[];
  priority: string; status_code: string;
  rank?: number; mvp?: boolean; priority_score?: number; priority_rationale?: string | null;
}
export interface LifecycleStage {
  stage_no: number; stage_name: string; status_code: string;
  primary_owner: string; verifier: string; exit_criteria: string;
}
export interface CatalogItem {
  id: string; category: string; item_id: string | null; module_id: string | null;
  title: string | null; domain: string | null; phase: string | null;
  priority: string | null; status: string | null; data: Record<string, string>;
}
export interface CatalogPage { category: string; total: number; limit: number; offset: number; items: CatalogItem[]; }
export interface CatalogSummary { counts: Record<string, number>; totals: Record<string, number>; }
export interface ModuleInfo { module_id: string; name: string; domain: string; mvp_priority: string; data: Record<string, string>; }
export interface ModuleRecord {
  id: string; module_id: string; project_id: string | null; title: string;
  status: string; priority: string; data: Record<string, unknown>; version: number;
}
export interface Provider {
  id: string; provider: string; label: string; masked_secret: string;
  config: Record<string, unknown>; is_active: boolean;
}
export interface Usage { period: string; input_tokens: number; output_tokens: number; calls: number; monthly_budget: number; }
export interface GenFile { path: string; language: string; content: string; kind?: string; }
export interface Run {
  id: string; project_id: string; story_id: string | null; kind: string;
  provider: string; model: string | null; status: string;
  input_tokens: number; output_tokens: number; branch: string | null;
  pr_url: string | null; files: GenFile[]; rationale: string | null; log: string | null;
}
export interface RankedStory { id: string; rank: number; mvp: boolean; score: number; rationale: string | null; title: string; }

const remoteApi = {
  login: (email: string, password: string) =>
    request<{ access_token: string }>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  me: () => request<CurrentUser>("/api/v1/auth/me"),
  projects: () => request<Project[]>("/api/v1/projects"),
  createProject: (body: { name: string; code: string; description?: string; repo_url?: string; tech_stack?: string; default_branch?: string }) =>
    request<Project>("/api/v1/projects", { method: "POST", body: JSON.stringify(body) }),
  requirements: (projectId?: string) =>
    request<Requirement[]>(`/api/v1/requirements${projectId ? `?project_id=${projectId}` : ""}`),
  createRequirement: (body: { project_id: string; title: string; raw_text: string }) =>
    request<Requirement>("/api/v1/requirements", { method: "POST", body: JSON.stringify(body) }),
  uploadRequirement: async (projectId: string, title: string, file: File) => {
    const fd = new FormData();
    fd.append("project_id", projectId);
    fd.append("title", title);
    fd.append("file", file);
    const res = await fetch(`${API_BASE}/api/v1/requirements/upload`, {
      method: "POST",
      headers: tokenStore.get() ? { Authorization: `Bearer ${tokenStore.get()}` } : {},
      body: fd,
    });
    if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || res.statusText);
    return res.json() as Promise<Requirement>;
  },
  analyze: (id: string) =>
    request<Analysis>(`/api/v1/requirements/${id}/analyze`, { method: "POST" }),
  generateBacklog: (id: string) =>
    request<{ requirement_id: string; created_story_ids: string[] }>(
      `/api/v1/requirements/${id}/generate-backlog`, { method: "POST" }),
  stories: (projectId?: string) =>
    request<Story[]>(`/api/v1/stories${projectId ? `?project_id=${projectId}` : ""}`),
  lifecycle: () => request<LifecycleStage[]>("/api/v1/stories/lifecycle"),
  updateStoryStatus: (id: string, status_code: string) =>
    request<Story>(`/api/v1/stories/${id}/status`, {
      method: "PATCH", body: JSON.stringify({ status_code }),
    }),

  // Blueprint catalog (full workbook as data)
  catalogSummary: () => request<CatalogSummary>("/api/v1/catalog/summary"),
  catalog: (category: string, params: Record<string, string | number> = {}) => {
    const qs = new URLSearchParams(
      Object.entries(params).map(([k, v]) => [k, String(v)])
    ).toString();
    return request<CatalogPage>(`/api/v1/catalog/${category}${qs ? `?${qs}` : ""}`);
  },

  // Generic module engine (all 27 modules)
  modules: () => request<ModuleInfo[]>("/api/v1/modules"),
  moduleRecords: (moduleId: string, params: Record<string, string | number> = {}) => {
    const qs = new URLSearchParams(
      Object.entries(params).map(([k, v]) => [k, String(v)])
    ).toString();
    return request<{ module_id: string; total: number; items: ModuleRecord[] }>(
      `/api/v1/modules/${moduleId}/records${qs ? `?${qs}` : ""}`);
  },
  createModuleRecord: (moduleId: string, body: { title: string; priority?: string; status?: string; data?: Record<string, unknown> }) =>
    request<ModuleRecord>(`/api/v1/modules/${moduleId}/records`, {
      method: "POST", body: JSON.stringify(body),
    }),
  deleteModuleRecord: (moduleId: string, recordId: string) =>
    request<void>(`/api/v1/modules/${moduleId}/records/${recordId}`, { method: "DELETE" }),

  // Integrations / Settings
  providers: () => request<Provider[]>("/api/v1/integrations/providers"),
  addProvider: (body: { provider: string; label: string; secret: string; config?: Record<string, unknown> }) =>
    request<Provider>("/api/v1/integrations/providers", { method: "POST", body: JSON.stringify(body) }),
  deleteProvider: (id: string) =>
    request<void>(`/api/v1/integrations/providers/${id}`, { method: "DELETE" }),
  testProvider: (id: string) =>
    request<{ ok: boolean; detail: string }>(`/api/v1/integrations/providers/${id}/test`, { method: "POST" }),
  usage: () => request<Usage>("/api/v1/integrations/usage"),

  // Real AI pipeline
  generateStories: (reqId: string) =>
    request<Story[]>(`/api/v1/requirements/${reqId}/generate-stories`, { method: "POST" }),
  prioritize: (projectId: string) =>
    request<{ ranked: RankedStory[] }>(`/api/v1/projects/${projectId}/prioritize?mode=ai`, { method: "POST" }),
  generateCode: (projectId: string, storyIds: string[]) =>
    request<Run[]>(`/api/v1/projects/${projectId}/generate`, {
      method: "POST", body: JSON.stringify({ story_ids: storyIds }),
    }),
  run: (id: string) => request<Run>(`/api/v1/runs/${id}`),
  runs: (projectId?: string) =>
    request<Run[]>(`/api/v1/runs${projectId ? `?project_id=${projectId}` : ""}`),
};

// localApi only imports *types* from this module (erased at build), so there is no runtime
// cycle. Bind to it when no backend is configured — that's what makes the static build work.
export const api: typeof remoteApi = USE_LOCAL
  ? (localApi as unknown as typeof remoteApi)
  : remoteApi;
