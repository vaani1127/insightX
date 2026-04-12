import axios from "axios";
import Cookies from "js-cookie";

const client = axios.create({ baseURL: "/api" });

// Attach JWT from cookie on every request
client.interceptors.request.use((config) => {
  const token = Cookies.get("insightx_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Auto-redirect to login on 401
client.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      Cookies.remove("insightx_token");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

export default client;

// ── Auth ──────────────────────────────────────────────────────────────────
export const signup = (email: string, username: string, password: string) =>
  client.post("/auth/signup", { email, username, password });

export const login = (email: string, password: string) =>
  client.post("/auth/login", { email, password });

export const getMe = () => client.get("/auth/me");

// ── Workspaces ────────────────────────────────────────────────────────────
export const listWorkspaces = () => client.get("/workspaces");
export const createWorkspace = (name: string, description?: string) =>
  client.post("/workspaces", { name, description: description ?? "" });
export const getWorkspace = (id: string) => client.get(`/workspaces/${id}`);
export const deleteWorkspace = (id: string) => client.delete(`/workspaces/${id}`);

// ── Upload ────────────────────────────────────────────────────────────────
export const uploadFile = (workspaceId: string, file: File) => {
  const form = new FormData();
  form.append("file", file);
  return client.post(`/upload/${workspaceId}`, form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
};

// ── Query ─────────────────────────────────────────────────────────────────
export const runQuery = (query: string, workspaceId: string) =>
  client.post("/query", { query, workspace_id: workspaceId });

// ── Schema ────────────────────────────────────────────────────────────────
export const getSchema = (workspaceId: string) =>
  client.get(`/schema/${workspaceId}`);

// ── History ───────────────────────────────────────────────────────────────
export const getHistory = (workspaceId: string) =>
  client.get(`/history/${workspaceId}`);
export const clearHistory = (workspaceId: string) =>
  client.delete(`/history/${workspaceId}`);

// ── Feedback ──────────────────────────────────────────────────────────────
export const submitFeedback = (
  queryHistoryId: string,
  wasHelpful: boolean,
  correction?: string
) =>
  client.post("/feedback", {
    query_history_id: queryHistoryId,
    was_helpful: wasHelpful,
    correction: correction ?? null,
  });
