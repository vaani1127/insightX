"use client";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { createWorkspace, deleteWorkspace, listWorkspaces, uploadFile } from "@/lib/api";
import { clearSession, getUser, isLoggedIn, StoredUser } from "@/lib/auth";

interface Workspace {
  id: string;
  name: string;
  description: string;
  table_name: string | null;
  columns: string[] | null;
  row_count: number;
  created_at: string;
}

// ── Delete Modal ───────────────────────────────────────────────────────────
function DeleteModal({ name, onConfirm, onCancel, deleting }: {
  name: string;
  onConfirm: () => void;
  onCancel: () => void;
  deleting: boolean;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onCancel}
      />
      {/* Modal */}
      <div className="relative bg-surface border border-border rounded-2xl p-6 w-full max-w-sm shadow-2xl animate-fade-up">
        <div className="flex items-start gap-4 mb-5">
          <div className="w-10 h-10 rounded-xl bg-red/10 flex items-center justify-center flex-shrink-0">
            <svg className="w-5 h-5 text-red" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6M9 7h6m-7 0a1 1 0 01-1-1V5a1 1 0 011-1h6a1 1 0 011 1v1a1 1 0 01-1 1H9z" />
            </svg>
          </div>
          <div>
            <h2 className="font-semibold text-sm text-text">Delete workspace</h2>
            <p className="text-text3 text-xs mt-1 leading-relaxed">
              <span className="text-text2 font-medium">"{name}"</span> and all its data, uploaded files, and query history will be permanently deleted. This cannot be undone.
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={onCancel}
            disabled={deleting}
            className="flex-1 bg-surface2 hover:bg-surface3 disabled:opacity-50 text-text2 text-sm font-medium py-2 rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={deleting}
            className="flex-1 bg-red/10 hover:bg-red/20 disabled:opacity-50 text-red border border-red/20 text-sm font-medium py-2 rounded-lg transition-colors"
          >
            {deleting ? "Deleting…" : "Delete"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Drop Zone ──────────────────────────────────────────────────────────────
const ACCEPTED = [".csv", ".xlsx", ".xls"];
const ACCEPTED_MIME = ["text/csv", "application/vnd.ms-excel",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"];

function DropZone({ workspaceId, onUpload }: {
  workspaceId: string;
  onUpload: (id: string, file: File) => Promise<void>;
}) {
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const dragCounter = useRef(0);

  function validate(file: File): string | null {
    const ext = "." + file.name.split(".").pop()?.toLowerCase();
    if (!ACCEPTED.includes(ext) && !ACCEPTED_MIME.includes(file.type))
      return "Only CSV and Excel files (.csv, .xlsx, .xls) are supported.";
    if (file.size > 50 * 1024 * 1024)
      return "File must be under 50 MB.";
    return null;
  }

  async function handleFile(file: File) {
    const err = validate(file);
    if (err) { setError(err); return; }
    setError(null);
    setUploading(true);
    try {
      await onUpload(workspaceId, file);
    } catch (e: unknown) {
      setError(
        (e as { response?: { data?: { detail?: string } } })
          ?.response?.data?.detail ?? "Upload failed. Please try again."
      );
    } finally {
      setUploading(false);
    }
  }

  function onDragEnter(e: React.DragEvent) {
    e.preventDefault();
    dragCounter.current++;
    if (dragCounter.current === 1) setDragging(true);
  }

  function onDragLeave(e: React.DragEvent) {
    e.preventDefault();
    dragCounter.current--;
    if (dragCounter.current === 0) setDragging(false);
  }

  function onDragOver(e: React.DragEvent) {
    e.preventDefault();
    e.dataTransfer.dropEffect = "copy";
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    dragCounter.current = 0;
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }

  return (
    <div className="mb-4">
      <div
        onDragEnter={onDragEnter}
        onDragLeave={onDragLeave}
        onDragOver={onDragOver}
        onDrop={onDrop}
        onClick={() => !uploading && inputRef.current?.click()}
        className={`
          relative rounded-xl border-2 border-dashed p-6 text-center cursor-pointer
          transition-all duration-200 select-none
          ${uploading
            ? "border-purple/40 bg-purple/5 cursor-default"
            : dragging
            ? "border-purple bg-purple/10 scale-[1.02]"
            : error
            ? "border-red/40 bg-red/5 hover:border-red/60"
            : "border-border bg-surface2 hover:border-purple/40 hover:bg-purple/5"
          }
        `}
      >
        {uploading ? (
          <div className="flex flex-col items-center gap-2">
            <div className="w-6 h-6 border-2 border-purple border-t-transparent rounded-full animate-spin" />
            <p className="text-purple text-xs font-medium">Uploading…</p>
          </div>
        ) : dragging ? (
          <div className="flex flex-col items-center gap-2 pointer-events-none">
            <div className="w-10 h-10 rounded-xl bg-purple/20 flex items-center justify-center text-purple text-xl">↓</div>
            <p className="text-purple text-xs font-medium">Drop to upload</p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2">
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center text-lg ${error ? "bg-red/10 text-red" : "bg-surface3 text-text3"}`}>
              {error ? "!" : "↑"}
            </div>
            <div>
              <p className={`text-xs font-medium ${error ? "text-red" : "text-text2"}`}>
                {error ?? "Drop your file here"}
              </p>
              <p className="text-text3 text-xs mt-0.5">
                {error ? "Click to try again" : "or click to browse · CSV, XLSX up to 50 MB"}
              </p>
            </div>
          </div>
        )}
      </div>

      <input
        ref={inputRef}
        type="file"
        accept=".csv,.xlsx,.xls"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) handleFile(file);
          e.target.value = "";
        }}
      />
    </div>
  );
}

// ── Dashboard ──────────────────────────────────────────────────────────────
export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<StoredUser | null>(null);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; name: string } | null>(null);
  const [deleting, setDeleting] = useState(false);

  const filtered = workspaces.filter((ws) =>
    ws.name.toLowerCase().includes(search.toLowerCase())
  );

  useEffect(() => {
    if (!isLoggedIn()) { router.push("/login"); return; }
    setUser(getUser());
    loadWorkspaces();
  }, []);

  async function loadWorkspaces() {
    setLoading(true);
    try {
      const res = await listWorkspaces();
      setWorkspaces(res.data);
    } catch { /* handled by interceptor */ }
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
    await uploadFile(workspaceId, file);
    await loadWorkspaces();
  }

  async function confirmDelete() {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await deleteWorkspace(deleteTarget.id);
      setWorkspaces((ws) => ws.filter((w) => w.id !== deleteTarget.id));
      setDeleteTarget(null);
    } finally {
      setDeleting(false);
    }
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

        {/* Search */}
        {workspaces.length > 0 && (
          <div className="relative mb-6">
            <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text3 pointer-events-none" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" />
            </svg>
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search workspaces…"
              className="w-full bg-surface border border-border rounded-lg pl-9 pr-4 py-2 text-sm text-text placeholder:text-text3 focus:outline-none focus:border-purple/50 transition-colors"
            />
            {search && (
              <button onClick={() => setSearch("")} className="absolute right-3 top-1/2 -translate-y-1/2 text-text3 hover:text-text2 text-xs">✕</button>
            )}
          </div>
        )}

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
        ) : filtered.length === 0 ? (
          <div className="text-center py-16 text-text3">
            <p className="text-sm">No workspaces match <span className="text-text2">"{search}"</span></p>
            <button onClick={() => setSearch("")} className="mt-2 text-xs text-purple hover:text-purple/80 transition-colors">Clear search</button>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {filtered.map((ws) => (
              <div key={ws.id} className="bg-surface border border-border rounded-xl p-5 hover:border-purple/30 transition-colors group">
                {/* Card header */}
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <h2 className="font-semibold text-sm">{ws.name}</h2>
                    {ws.description && <p className="text-text3 text-xs mt-0.5">{ws.description}</p>}
                  </div>
                  <button
                    onClick={() => setDeleteTarget({ id: ws.id, name: ws.name })}
                    className="opacity-0 group-hover:opacity-100 text-text3 hover:text-red text-xs transition-all"
                  >
                    Delete
                  </button>
                </div>

                {/* Upload zone or dataset info */}
                {ws.table_name ? (
                  <div className="mb-4 bg-green/5 border border-green/20 rounded-xl p-4 flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-green/15 flex items-center justify-center text-green text-sm flex-shrink-0">✓</div>
                    <div>
                      <p className="text-green text-xs font-medium">Dataset loaded</p>
                      <p className="text-text3 text-xs mt-0.5">{ws.row_count.toLocaleString()} rows · {ws.columns?.length ?? 0} columns</p>
                    </div>
                  </div>
                ) : (
                  <DropZone workspaceId={ws.id} onUpload={handleUpload} />
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

      {deleteTarget && (
        <DeleteModal
          name={deleteTarget.name}
          deleting={deleting}
          onConfirm={confirmDelete}
          onCancel={() => !deleting && setDeleteTarget(null)}
        />
      )}
    </div>
  );
}
