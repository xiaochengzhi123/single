export type AuthUser = {
  id: string;
  username: string;
  display_name: string;
};

export type AdminAccount = AuthUser & {
  active: boolean;
  created_at: string;
  expires_at: string;
  expired: boolean;
  remaining_days: number;
};

export type KnowledgeKind =
  | "past_exam"
  | "textbook"
  | "formula"
  | "syllabus"
  | "solution"
  | "other";

export type KnowledgeEntry = {
  id: string;
  title: string;
  content: string;
  kind: KnowledgeKind;
  school?: string | null;
  year?: number | null;
  chapter: string;
  topics: string[];
  difficulty?: number | null;
  source_page?: number | null;
  source_url?: string | null;
  published: boolean;
  created_at: string;
};

export type KnowledgeEntryInput = Omit<KnowledgeEntry, "id" | "created_at">;

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
  payload: {
    username: string;
    display_name: string;
    password: string;
    subscription_months: number;
  },
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

export function renewAccount(adminKey: string, accountId: string, months: number) {
  return adminRequest<AdminAccount>(`/api/v1/admin/accounts/${accountId}/renew`, adminKey, {
    method: "POST",
    body: JSON.stringify({ months }),
  });
}

export function listKnowledgeEntries(adminKey: string) {
  return adminRequest<KnowledgeEntry[]>("/api/v1/admin/knowledge", adminKey);
}

export function createKnowledgeEntry(adminKey: string, payload: KnowledgeEntryInput) {
  return adminRequest<KnowledgeEntry>("/api/v1/admin/knowledge", adminKey, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function setKnowledgePublished(
  adminKey: string,
  entryId: string,
  published: boolean,
) {
  return adminRequest<KnowledgeEntry>(`/api/v1/admin/knowledge/${entryId}`, adminKey, {
    method: "PATCH",
    body: JSON.stringify({ published }),
  });
}

export async function deleteKnowledgeEntry(adminKey: string, entryId: string) {
  const response = await fetch(`${API_BASE}/api/v1/admin/knowledge/${entryId}`, {
    method: "DELETE",
    headers: { "X-Admin-Key": adminKey },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(readMessage(body, "删除知识条目失败"));
  }
}

export async function importKnowledgeFile(
  adminKey: string,
  file: File,
  metadata: {
    title: string;
    kind: KnowledgeKind;
    school: string;
    year: string;
    chapter: string;
    topics: string;
    difficulty: string;
    sourceUrl: string;
  },
) {
  const form = new FormData();
  form.append("file", file);
  form.append("title", metadata.title);
  form.append("kind", metadata.kind);
  form.append("chapter", metadata.chapter);
  form.append("topics", metadata.topics);
  if (metadata.school) form.append("school", metadata.school);
  if (metadata.year) form.append("year", metadata.year);
  if (metadata.difficulty) form.append("difficulty", metadata.difficulty);
  if (metadata.sourceUrl) form.append("source_url", metadata.sourceUrl);
  const response = await fetch(`${API_BASE}/api/v1/admin/knowledge/import`, {
    method: "POST",
    headers: { "X-Admin-Key": adminKey },
    body: form,
  });
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new Error(readMessage(body, "资料导入失败"));
  return body as { imported: number; entries: KnowledgeEntry[] };
}
