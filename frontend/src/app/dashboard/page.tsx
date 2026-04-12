"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { createWorkspace, deleteWorkspace, listWorkspaces, uploadFile } from "@/lib/api";
import { clearSession, getUser, isLoggedIn } from "@/lib/auth";

interface Workspace {
  id: string;
  name: string;
  description: string;
  table_name: string | null;
  columns: string[] | null;
  row_count: number;
  created_at: string;
}

export default function DashboardPage() {
  const router = useRouter();
  const user = getUser();
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [uploadingId, setUploadingId] = useState<string | null>(null);

  useEffect(() => {
    if (!isLoggedIn()) { router.push("/login"); return; }
    loadWorkspaces();
  }, []);

  async function loadWorkspaces() {
    setLoading(true);
    try {
      const res = await listWorkspaces();
      setWorkspaces(res.data);
    } catch {/* handled by interceptor */}
    finally { setLoading(false); }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!newName.trim()) return;
    setCreating(true);
    try {
      await createWorkspace(newName.trim());
      setNewName("");
      setShowCreate(false);
      await loadWorkspaces();
    } finally { setCreating(false); }
  }

  async function handleUpload(workspaceId: string, file: File) {
    setUploadingId(workspaceId);
    try {
      await uploadFile(workspaceId, file);
      await loadWorkspaces();
    } catch (err: unknown) {
      alert((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Upload failed.");
    } finally { setUploadingId(null); }
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this workspace and all its data?")) return;
    await deleteWorkspace(id);
    setWorkspaces((ws) => ws.filter((w) => w.id !== id));
  }

  return (
    <div className="min-h-screen bg-bg">
      {/* Header */}
      <header className="border-b border-border px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-purple/20 flex items-center justify-center text-purple font-bold">X</div>
          <span className="font-bold tracking-tight">InsightX AI</span>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-text3 text-sm">{user?.username}</span>
          <button
            onClick={() => { clearSession(); router.push("/login"); }}
            className="text-text3 hover:text-text2 text-sm transition-colors"
          >
            Sign out
          </button>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-10">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold">Workspaces</h1>
            <p className="text-text3 text-sm mt-1">Each workspace holds one dataset and its full conversation history.</p>
          </div>
          <button
            onClick={() => setShowCreate(true)}
            className="bg-purple hover:bg-purple/90 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
          >
            + New workspace
          </button>
        </div>

        {/* Create form */}
        {showCreate && (
          <form onSubmit={handleCreate} className="bg-surface border border-border rounded-xl p-4 mb-6 flex gap-3 animate-fade-up">
            <input
              autoFocus
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="Workspace name (e.g. Q2 Sales Data)"
              className="flex-1 bg-surface2 border border-border rounded-lg px-3 py-2 text-sm text-text placeholder:text-text3 focus:outline-none focus:border-purple/50"
            />
            <button type="submit" disabled={creating} className="bg-purple hover:bg-purple/90 disabled:opacity-50 text-white text-sm font-medium px-4 py-2 rounded-lg">
              {creating ? "Creating…" : "Create"}
            </button>
            <button type="button" onClick={() => setShowCreate(false)} className="text-text3 hover:text-text2 text-sm px-3">
              Cancel
            </button>
          </form>
        )}

        {/* Workspace grid */}
        {loading ? (
          <div className="text-text3 text-sm">Loading…</div>
        ) : workspaces.length === 0 ? (
          <div className="text-center py-20 text-text3">
            <p className="text-lg mb-2">No workspaces yet.</p>
            <p className="text-sm">Create one and upload a CSV or Excel file to get started.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {workspaces.map((ws) => (
              <div key={ws.id} className="bg-surface border border-border rounded-xl p-5 hover:border-purple/30 transition-colors group">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h2 className="font-semibold text-sm">{ws.name}</h2>
                    {ws.description && <p className="text-text3 text-xs mt-0.5">{ws.description}</p>}
                  </div>
                  <button
                    onClick={() => handleDelete(ws.id)}
                    className="opacity-0 group-hover:opacity-100 text-text3 hover:text-red text-xs transition-all"
                  >
                    Delete
                  </button>
                </div>

                {ws.table_name ? (
                  <div className="mb-4">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="w-2 h-2 rounded-full bg-green inline-block"></span>
                      <span className="text-green text-xs font-medium">Dataset loaded</span>
                    </div>
                    <p className="text-text3 text-xs">{ws.row_count.toLocaleString()} rows · {ws.columns?.length ?? 0} columns</p>
                  </div>
                ) : (
                  <div className="mb-4">
                    <label className="block w-full cursor-pointer">
                      <div className="border border-dashed border-border rounded-lg p-3 text-center hover:border-purple/40 transition-colors">
                        {uploadingId === ws.id ? (
                          <span className="text-text3 text-xs">Uploading…</span>
                        ) : (
                          <span className="text-text3 text-xs">Drop CSV / Excel or click to upload</span>
                        )}
                      </div>
                      <input
                        type="file"
                        accept=".csv,.xlsx,.xls"
                        className="hidden"
                        onChange={(e) => {
                          const file = e.target.files?.[0];
                          if (file) handleUpload(ws.id, file);
                        }}
                      />
                    </label>
                  </div>
                )}

                <button
                  onClick={() => router.push(`/dashboard/${ws.id}`)}
                  disabled={!ws.table_name}
                  className="w-full bg-surface2 hover:bg-surface3 disabled:opacity-40 disabled:cursor-not-allowed text-text2 hover:text-text text-sm font-medium py-2 rounded-lg transition-colors"
                >
                  {ws.table_name ? "Open chat →" : "Upload data first"}
                </button>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
