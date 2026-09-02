export type AuthUser = {
  id: string;
  username: string;
  display_name: string;
};

export type AdminAccount = AuthUser & {
  active: boolean;
  created_at: string;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const authTokenStorageKey = "signaltutor.auth-token.v1";

function readMessage(body: unknown, fallback: string) {
  if (!body || typeof body !== "object") return fallback;
  const detail = "detail" in body ? body.detail : null;
  if (detail && typeof detail === "object" && "message" in detail) {
    return String(detail.message);
  }
  return fallback;
}

export function getAuthToken() {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(authTokenStorageKey);
}

export function setAuthToken(token: string) {
  window.localStorage.setItem(authTokenStorageKey, token);
}

export function clearAuthToken() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(authTokenStorageKey);
}

export async function authFetch(input: string, init: RequestInit = {}) {
  const headers = new Headers(init.headers);
  const token = getAuthToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(input, { ...init, headers });
  if (response.status === 401) {
    clearAuthToken();
    window.dispatchEvent(new Event("signaltutor:unauthorized"));
  }
  return response;
}

export async function login(username: string, password: string): Promise<AuthUser> {
  const response = await fetch(`${API_BASE}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new Error(readMessage(body, "登录失败，请稍后重试"));
  setAuthToken(body.access_token);
  return body.user as AuthUser;
}

export async function fetchCurrentUser(): Promise<AuthUser> {
  const response = await authFetch(`${API_BASE}/api/v1/auth/me`, { cache: "no-store" });
  if (!response.ok) throw new Error("登录已失效");
  return response.json() as Promise<AuthUser>;
}

async function adminRequest<T>(path: string, adminKey: string, init: RequestInit = {}) {
  const headers = new Headers(init.headers);
  headers.set("X-Admin-Key", adminKey);
  if (init.body) headers.set("Content-Type", "application/json");
  const response = await fetch(`${API_BASE}${path}`, { ...init, headers });
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new Error(readMessage(body, "管理操作失败"));
  return body as T;
}

export function listAccounts(adminKey: string) {
  return adminRequest<AdminAccount[]>("/api/v1/admin/accounts", adminKey);
}

export function createAccount(
  adminKey: string,
  payload: { username: string; display_name: string; password: string },
) {
  return adminRequest<AdminAccount>("/api/v1/admin/accounts", adminKey, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function setAccountActive(adminKey: string, accountId: string, active: boolean) {
  return adminRequest<AdminAccount>(`/api/v1/admin/accounts/${accountId}`, adminKey, {
    method: "PATCH",
    body: JSON.stringify({ active }),
  });
}

export function resetAccountPassword(adminKey: string, accountId: string, password: string) {
  return adminRequest<AdminAccount>(
    `/api/v1/admin/accounts/${accountId}/reset-password`,
    adminKey,
    { method: "POST", body: JSON.stringify({ password }) },
  );
}
