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
