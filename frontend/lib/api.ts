/**
 * API client for communicating with the FastAPI backend
 * via the JWT-authenticated proxy at /api/proxy/...
 *
 * ALL requests go through the Next.js Route Handler proxy which:
 * 1. Extracts the Auth0 Access Token server-side
 * 2. Injects the Authorization: Bearer header
 * 3. Forwards to the FastAPI backend
 *
 * The browser NEVER sees or handles the JWT directly.
 */

const PROXY_BASE = "/api/proxy";

export async function apiGet<T = unknown>(path: string): Promise<T> {
  const res = await fetch(`${PROXY_BASE}${path}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: `HTTP ${res.status}` }));
    throw new Error(err.error || err.detail || `API error: ${res.status}`);
  }
  return res.json();
}

export async function apiPost<T = unknown>(
  path: string,
  body?: unknown
): Promise<T> {
  const res = await fetch(`${PROXY_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: `HTTP ${res.status}` }));
    throw new Error(err.error || err.detail || `API error: ${res.status}`);
  }
  return res.json();
}

// ── Typed API calls ──

export const api = {
  health: () => apiGet("/health"),

  missions: {
    start: (scenario: string) =>
      apiPost("/api/v1/missions/start", { scenario }),
    status: (id: string) => apiGet(`/api/v1/missions/${id}/status`),
    approve: (id: string) => apiPost(`/api/v1/missions/${id}/approve`),
    reject: (id: string) => apiPost(`/api/v1/missions/${id}/reject`),
    kill: (id: string) => apiPost(`/api/v1/missions/${id}/kill`),
    active: () => apiGet("/api/v1/missions/active"),
  },

  infra: {
    status: () => apiGet("/api/v1/infra/status"),
    diff: (scenario: string) => apiGet(`/api/v1/infra/diff/${scenario}`),
    auditLog: () => apiGet("/api/v1/infra/audit-log"),
    reset: () => apiPost("/api/v1/infra/reset"),
  },

  ciba: {
    initiate: (missionId: string, interruptPayload: unknown) =>
      apiPost("/api/v1/auth/ciba/initiate", {
        mission_id: missionId,
        interrupt_payload: interruptPayload,
      }),
    approve: (authReqId: string) =>
      apiPost(`/api/v1/auth/ciba/${authReqId}/approve`, {
        decision: "approved",
      }),
    reject: (authReqId: string, reason?: string) =>
      apiPost(`/api/v1/auth/ciba/${authReqId}/approve`, {
        decision: "rejected",
        reason,
      }),
    status: (authReqId: string) =>
      apiGet(`/api/v1/auth/ciba/status/${authReqId}`),
    active: () => apiGet("/api/v1/auth/ciba/active"),
  },
};
