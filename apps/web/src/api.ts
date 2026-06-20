// Thin API client. Base URL is config-driven (Vercel env / Electron injected global).
const w = window as unknown as { __BP360_API_BASE__?: string };
export const API_BASE =
  w.__BP360_API_BASE__ ||
  (import.meta.env.VITE_API_BASE_URL as string) ||
  "http://localhost:8000";

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
export interface Project { id: string; name: string; code: string; description?: string; status: string; }
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

export const api = {
  login: (email: string, password: string) =>
    request<{ access_token: string }>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  me: () => request<CurrentUser>("/api/v1/auth/me"),
  projects: () => request<Project[]>("/api/v1/projects"),
  createProject: (body: { name: string; code: string; description?: string }) =>
    request<Project>("/api/v1/projects", { method: "POST", body: JSON.stringify(body) }),
  requirements: (projectId?: string) =>
    request<Requirement[]>(`/api/v1/requirements${projectId ? `?project_id=${projectId}` : ""}`),
  createRequirement: (body: { project_id: string; title: string; raw_text: string }) =>
    request<Requirement>("/api/v1/requirements", { method: "POST", body: JSON.stringify(body) }),
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
};
