/**
 * Tiny API client for the IterLab control plane.
 *
 * Token handling for this skeleton:
 *  - the access token is kept in memory only
 *  - the refresh token is persisted in localStorage
 *  - a 401 on an authed request triggers one refresh + retry
 *
 * Hardening later: move refresh tokens to httpOnly cookies (needs a backend
 * change) so JS can't read them.
 */

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

const REFRESH_KEY = "iterlab.refresh_token";

let accessToken: string | null = null;

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
}

interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

interface AuthResult {
  user: User;
  tokens: TokenPair;
}

export class ApiError extends Error {
  status: number;
  code?: string;
  constructor(status: number, message: string, code?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(REFRESH_KEY);
}

function setSession(tokens: TokenPair | null): void {
  accessToken = tokens?.access_token ?? null;
  if (typeof window === "undefined") return;
  if (tokens) {
    window.localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
  } else {
    window.localStorage.removeItem(REFRESH_KEY);
  }
}

export function hasStoredSession(): boolean {
  return getRefreshToken() !== null;
}

async function request(
  path: string,
  init: RequestInit = {},
  withAuth = true,
): Promise<Response> {
  const headers = new Headers(init.headers);
  headers.set("content-type", "application/json");
  if (withAuth && accessToken) {
    headers.set("authorization", `Bearer ${accessToken}`);
  }
  return fetch(`${API_BASE}${path}`, { ...init, headers, cache: "no-store" });
}

async function toJsonOrThrow(res: Response): Promise<any> {
  const text = await res.text();
  const body = text ? JSON.parse(text) : null;
  if (!res.ok) {
    const err = body?.error;
    throw new ApiError(
      res.status,
      err?.message ?? res.statusText ?? "request failed",
      err?.code,
    );
  }
  return body;
}

let refreshInFlight: Promise<boolean> | null = null;

function refreshSession(): Promise<boolean> {
  if (!refreshInFlight) {
    refreshInFlight = (async () => {
      const refresh_token = getRefreshToken();
      if (!refresh_token) return false;
      const res = await request(
        "/auth/refresh",
        { method: "POST", body: JSON.stringify({ refresh_token }) },
        false,
      );
      if (!res.ok) {
        setSession(null);
        return false;
      }
      const body = (await res.json()) as AuthResult;
      setSession(body.tokens);
      return true;
    })().finally(() => {
      refreshInFlight = null;
    });
  }
  return refreshInFlight;
}

export async function apiFetch<T = any>(
  path: string,
  init: RequestInit = {},
  withAuth = true,
): Promise<T> {
  let res = await request(path, init, withAuth);
  if (res.status === 401 && withAuth && getRefreshToken()) {
    if (await refreshSession()) {
      res = await request(path, init, withAuth);
    }
  }
  return toJsonOrThrow(res) as Promise<T>;
}

// --- auth ----------------------------------------------------------------

export async function register(
  email: string,
  password: string,
  fullName?: string,
): Promise<User> {
  const body = await apiFetch<AuthResult>(
    "/auth/register",
    {
      method: "POST",
      body: JSON.stringify({
        email,
        password,
        full_name: fullName?.trim() ? fullName.trim() : null,
      }),
    },
    false,
  );
  setSession(body.tokens);
  return body.user;
}

export async function login(email: string, password: string): Promise<User> {
  const body = await apiFetch<AuthResult>(
    "/auth/login",
    { method: "POST", body: JSON.stringify({ email, password }) },
    false,
  );
  setSession(body.tokens);
  return body.user;
}

export async function logout(): Promise<void> {
  const refresh_token = getRefreshToken();
  try {
    if (refresh_token) {
      await request(
        "/auth/logout",
        { method: "POST", body: JSON.stringify({ refresh_token }) },
        false,
      );
    }
  } finally {
    setSession(null);
  }
}

export async function fetchMe(): Promise<User> {
  return apiFetch<User>("/auth/me");
}

// --- labs & benchmarks -------------------------------------------------

export interface Lab {
  id: string;
  project_id: string;
  slug: string;
  name: string;
  description: string | null;
  repo_url: string | null;
  repo_default_branch: string;
  settings: Record<string, unknown>;
  source: "manual" | "instance";
  created_at: string;
}

export interface Benchmark {
  id: string;
  lab_id: string;
  slug: string;
  name: string;
  description: string | null;
  adapter: string;
  primary_metric: string | null;
  higher_is_better: boolean;
  managed: boolean;
  created_at: string;
}

export interface LabDetail extends Lab {
  benchmarks: Benchmark[];
}

export interface LeaderboardColumn {
  key: string;
  label: string;
  kind: "number" | "string" | "percent" | "integer";
  primary: boolean;
}

export interface LeaderboardRow {
  rank: number;
  entrant: string;
  score: number | null;
  is_baseline: boolean;
  is_candidate: boolean;
  values: Record<string, unknown>;
}

export interface Leaderboard {
  benchmark_slug: string;
  title: string;
  columns: LeaderboardColumn[];
  rows: LeaderboardRow[];
  updated_at: string | null;
  note: string | null;
}

export const listLabs = () => apiFetch<Lab[]>("/labs");
export const getLab = (id: string) => apiFetch<LabDetail>(`/labs/${id}`);
export const getLeaderboard = (benchmarkId: string) =>
  apiFetch<Leaderboard>(`/benchmarks/${benchmarkId}/leaderboard`);
export const getBenchmarkHealth = (benchmarkId: string) =>
  apiFetch<{ ok: boolean; detail: string; adapter: string }>(
    `/benchmarks/${benchmarkId}/health`,
  );

// --- agents ----------------------------------------------------------

export type AgentKind = "cli" | "api";

export interface CliConfig {
  command: string;
  args: string[];
  working_dir: string | null;
  env: Record<string, string>;
}

export interface ApiConfig {
  provider: string;
  model: string | null;
  credential_env: string | null;
  params: Record<string, unknown>;
}

export interface Agent {
  id: string;
  owner_id: string;
  name: string;
  description: string | null;
  kind: AgentKind;
  managed: boolean;
  cli: CliConfig | null;
  api: ApiConfig | null;
  created_at: string;
}

export interface AgentCreate {
  name: string;
  description?: string | null;
  kind: AgentKind;
  cli?: Partial<CliConfig>;
  api?: Partial<ApiConfig>;
}

export const listAgents = () => apiFetch<Agent[]>("/agents");
export const createAgent = (body: AgentCreate) =>
  apiFetch<Agent>("/agents", { method: "POST", body: JSON.stringify(body) });
export const updateAgent = (id: string, body: Partial<AgentCreate>) =>
  apiFetch<Agent>(`/agents/${id}`, { method: "PATCH", body: JSON.stringify(body) });
export const deleteAgent = (id: string) =>
  apiFetch<void>(`/agents/${id}`, { method: "DELETE" });

// --- experiments & runs ---------------------------------------------

export interface WorkflowStep {
  handler: string;
  name: string | null;
  config: Record<string, unknown>;
}

export interface Experiment {
  id: string;
  lab_id: string;
  slug: string;
  name: string;
  description: string | null;
  workflow: { name?: string; steps?: WorkflowStep[] };
  managed: boolean;
  created_at: string;
}

export interface Run {
  id: string;
  experiment_id: string;
  status: string;
  iteration: number;
  summary: string | null;
  agent_session_id: string | null;
  error: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
}

export interface RunStep {
  id: string;
  iteration: number;
  position: number;
  handler: string;
  name: string | null;
  status: string;
  output: Record<string, unknown> | null;
  error: string | null;
  started_at: string | null;
  finished_at: string | null;
}

export interface Candidate {
  id: string;
  iteration: number;
  status: string;
  summary: string | null;
  commit_sha: string | null;
  branch: string | null;
  score: number | null;
  cost_usd: number | null;
  tokens: number | null;
  extra: Record<string, unknown> & { name?: string };
}

export interface RunListItem extends Run {
  candidates: Candidate[];
  steps: RunStep[];
  context: Record<string, unknown>;
}

export interface RunDetail extends Run {
  steps: RunStep[];
  candidates: Candidate[];
  benchmark_results: Array<{
    id: string;
    benchmark_id: string;
    score: number | null;
    passed: boolean | null;
    details: Record<string, unknown>;
    created_at: string;
  }>;
  context: Record<string, unknown>;
}

export const listExperiments = (labId: string) =>
  apiFetch<Experiment[]>(`/labs/${labId}/experiments`);
export const listRuns = (experimentId: string) =>
  apiFetch<RunListItem[]>(`/experiments/${experimentId}/runs`);
export const createRun = (experimentId: string) =>
  apiFetch<Run>(`/experiments/${experimentId}/runs`, { method: "POST" });
export const retryRun = (runId: string) =>
  apiFetch<Run>(`/runs/${runId}/retry`, { method: "POST" });
export const getRun = (runId: string) => apiFetch<RunDetail>(`/runs/${runId}`);
