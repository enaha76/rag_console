export const API_BASE_URL: string =
  (import.meta as any).env?.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

export type AuthUser = { 
  id: string; 
  email: string; 
  username: string;
  role?: string;
  llm_provider?: string;
  llm_model?: string;
};

const wait = (ms: number) => new Promise((r) => setTimeout(r, ms));

export function getToken(): string | null {
  try {
    return localStorage.getItem("access_token");
  } catch {
    return null;
  }
}

export function setToken(token: string | null) {
  try {
    if (token) localStorage.setItem("access_token", token);
    else localStorage.removeItem("access_token");
  } catch {}
}

// Internal helper to build headers
function authHeaders(extra: Record<string, string> = {}) {
  const headers: Record<string, string> = { ...extra };
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  return headers;
}

async function handleJsonResponse<T>(res: Response): Promise<T> {
  const text = await res.text();
  const data = text ? JSON.parse(text) : {};
  if (!res.ok) {
    const detail = (data && (data.detail || data.message)) || res.statusText;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data as T;
}

export async function login(params: {
  email: string;
  password: string;
}): Promise<{ access_token: string; user: AuthUser }> {
  const res = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  const data = await handleJsonResponse<{ access_token: string; user: AuthUser }>(res);
  setToken(data.access_token);
  return data;
}

export async function signup(params: {
  email: string;
  username: string;
  password: string;
  llm_provider?: string;
  llm_model?: string;
}): Promise<{ access_token: string; user: AuthUser }> {
  const res = await fetch(`${API_BASE_URL}/auth/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  const data = await handleJsonResponse<{ access_token: string; user: AuthUser }>(res);
  setToken(data.access_token);
  return data;
}

export async function listDocuments(skip = 0, limit = 20) {
  const url = `${API_BASE_URL}/documents?skip=${skip}&limit=${limit}`;
  const res = await fetch(url, { headers: authHeaders() });
  return handleJsonResponse<{ documents: any[] }>(res);
}

export async function deleteDocument(documentId: string) {
  const res = await fetch(`${API_BASE_URL}/documents/${documentId}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  return handleJsonResponse<{ success?: boolean; message?: string }>(res);
}

export async function uploadDocument(file: File, metadata: Record<string, any>) {
  const form = new FormData();
  form.append("file", file);
  // Backend expects a single 'metadata' field as JSON string
  try {
    form.append("metadata", JSON.stringify(metadata || {}));
  } catch {
    form.append("metadata", "{}");
  }
  const res = await fetch(`${API_BASE_URL}/documents/upload`, {
    method: "POST",
    headers: authHeaders(),
    body: form,
  });
  return handleJsonResponse<{ id: string; message?: string; status?: string }>(res);
}

export async function ragQuery(body: {
  query: string;
  max_chunks?: number;
  score_threshold?: number;
  temperature?: number;
  max_tokens?: number;
  include_sources?: boolean;
  session_id?: string;
}) {
  const res = await fetch(`${API_BASE_URL}/queries/rag`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(body),
  });
  return handleJsonResponse<any>(res);
}

export async function ragStream(
  body: {
    query: string;
    max_chunks?: number;
    score_threshold?: number;
    temperature?: number;
    max_tokens?: number;
    include_sources?: boolean;
    session_id?: string;
  },
  onChunk: (text: string, raw?: any) => void,
) {
  const res = await fetch(`${API_BASE_URL}/queries/rag/stream`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(body),
  });
  if (!res.ok || !res.body) {
    throw new Error(`Streaming failed: ${res.status} ${res.statusText}`);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let idx;
    while ((idx = buffer.indexOf("\n\n")) !== -1) {
      const raw = buffer.slice(0, idx).trim();
      buffer = buffer.slice(idx + 2);
      if (!raw) continue;
      if (raw.startsWith("data:")) {
        const payload = raw.slice(5).trim();
        if (payload === "[DONE]") return;
        onChunk(payload, raw);
      } else {
        onChunk(raw, raw);
      }
    }
  }
}

export async function vectorStatus() {
  const res = await fetch(`${API_BASE_URL}/queries/debug/vector-status`, {
    headers: authHeaders(),
  });
  return handleJsonResponse<any>(res);
}

export async function queryHistory(skip = 0, limit = 10, sessionId?: string) {
  const qp = new URLSearchParams({ skip: String(skip), limit: String(limit) });
  if (sessionId) qp.set("session_id", sessionId);
  const url = `${API_BASE_URL}/queries/history?${qp.toString()}`;
  const res = await fetch(url, { headers: authHeaders() });
  return handleJsonResponse<any>(res);
}
