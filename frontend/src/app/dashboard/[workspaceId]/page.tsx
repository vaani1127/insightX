"use client";
import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from "recharts";
import { clearHistory, getHistory, getSchema, getWorkspace, runQuery, submitFeedback } from "@/lib/api";
import { getUser, isLoggedIn } from "@/lib/auth";

// ── Types ──────────────────────────────────────────────────────────────────
interface Turn {
  id: string;
  query: string;
  result: QueryResponse | null;
  error?: string;
}

interface QueryResponse {
  narrative: string;
  sql: string;
  result: { columns: string[]; rows: unknown[][]; row_count: number };
  insights: { key_finding: string; anomalies: string[]; follow_up_questions: string[] };
  trust_layer: {
    sql: string; confidence: string; confidence_reason: string;
    data_sources: string[]; metrics_used: string[];
    assumptions: { field: string; value: string; reason: string }[];
    hallucination_check: { passed: boolean; discrepancies: string[] };
  };
  visualization: string;
  anomaly_flags: { column: string; value: number; z_score: number; severity: string }[];
  query_history_id: string;
}

const CHART_COLORS = ["#7c6df8","#1fd98c","#4fa3f7","#f5a623","#f05050","#22d4d4"];

const SUGGESTED = [
  "Show me total revenue",
  "Break down by region",
  "Compare this week vs last week",
  "Why did sales drop last month?",
  "Weekly summary",
  "Top 5 products by revenue",
];

const LOADING_STEPS = [
  "Parsing intent & resolving time references…",
  "Generating SQL via metric dictionary…",
  "Running privacy & PII guard…",
  "Executing query against DuckDB…",
  "Generating insights & root cause…",
  "Cross-checking with hallucination guard…",
];

// ── Helpers ────────────────────────────────────────────────────────────────
function formatVal(v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "number") {
    if (Math.abs(v) > 1_000_000) return `${(v / 1_000_000).toFixed(2)}M`;
    if (Math.abs(v) > 10_000) return v.toLocaleString(undefined, { maximumFractionDigits: 0 });
    return v.toLocaleString(undefined, { maximumFractionDigits: 2 });
  }
  return String(v);
}

function toChartData(columns: string[], rows: unknown[][]): Record<string, unknown>[] {
  return rows.map((row) => {
    const obj: Record<string, unknown> = {};
    columns.forEach((col, i) => { obj[col] = row[i]; });
    return obj;
  });
}

// ── Sub-components ─────────────────────────────────────────────────────────
function LoadingCard({ step }: { step: number }) {
  return (
    <div className="bg-surface border border-border rounded-xl p-4 max-w-md animate-fade-up">
      <p className="text-text3 text-xs mb-3 font-mono">Processing…</p>
      <div className="space-y-2">
        {LOADING_STEPS.map((label, i) => (
          <div key={i} className="flex items-center gap-2">
            <div className={`w-1.5 h-1.5 rounded-full flex-shrink-0 transition-all ${
              i < step ? "bg-green" : i === step ? "bg-purple animate-pulse-slow" : "bg-surface3"
            }`} />
            <span className={`text-xs ${i <= step ? "text-text2" : "text-text3"}`}>{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function AutoChart({ columns, rows, chartType }: { columns: string[]; rows: unknown[][]; chartType: string }) {
  const data = toChartData(columns, rows);
  const numCol = columns.find((_, i) => rows[0] && typeof rows[0][i] === "number");
  const dimCol = columns.find((c) => c !== numCol);

  if (chartType === "metric" && rows.length === 1) {
    const val = rows[0][0];
    return (
      <div className="text-center py-6">
        <div className="text-4xl font-bold text-purple">{formatVal(val)}</div>
        <div className="text-text3 text-sm mt-1">{columns[0]}</div>
      </div>
    );
  }

  if (chartType === "pie" && dimCol && numCol) {
    return (
      <ResponsiveContainer width="100%" height={260}>
        <PieChart>
          <Pie data={data} dataKey={numCol} nameKey={dimCol} cx="50%" cy="50%" outerRadius={90} label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
            {data.map((_, i) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
          </Pie>
          <Tooltip formatter={(v: unknown) => formatVal(v)} />
        </PieChart>
      </ResponsiveContainer>
    );
  }

  if (chartType === "line" && dimCol && numCol) {
    return (
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
          <XAxis dataKey={dimCol} tick={{ fill: "#6b6b80", fontSize: 11 }} />
          <YAxis tick={{ fill: "#6b6b80", fontSize: 11 }} tickFormatter={(v) => formatVal(v)} />
          <Tooltip formatter={(v: unknown) => formatVal(v)} contentStyle={{ background: "#18181f", border: "1px solid rgba(255,255,255,0.07)", borderRadius: 8 }} />
          <Line type="monotone" dataKey={numCol} stroke="#7c6df8" strokeWidth={2} dot={{ fill: "#7c6df8", r: 3 }} />
        </LineChart>
      </ResponsiveContainer>
    );
  }

  if (dimCol && numCol) {
    return (
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
          <XAxis dataKey={dimCol} tick={{ fill: "#6b6b80", fontSize: 11 }} />
          <YAxis tick={{ fill: "#6b6b80", fontSize: 11 }} tickFormatter={(v) => formatVal(v)} />
          <Tooltip formatter={(v: unknown) => formatVal(v)} contentStyle={{ background: "#18181f", border: "1px solid rgba(255,255,255,0.07)", borderRadius: 8 }} />
          <Bar dataKey={numCol} fill="#7c6df8" radius={[4, 4, 0, 0]}>
            {data.map((_, i) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    );
  }

  return null;
}

function TrustLayer({ trust }: { trust: QueryResponse["trust_layer"] }) {
  const [open, setOpen] = useState(false);
  const conf = trust.confidence;
  const confColor = conf === "high" ? "text-green" : conf === "medium" ? "text-amber" : "text-red";

  return (
    <div className="border border-border rounded-lg overflow-hidden mt-3">
      <button onClick={() => setOpen((o) => !o)} className="w-full flex items-center justify-between px-4 py-3 hover:bg-surface2 transition-colors text-left">
        <div className="flex items-center gap-2">
          <span className="text-xs text-text3">How did I get this?</span>
          <span className={`text-xs font-medium ${confColor}`}>{conf} confidence</span>
          {trust.hallucination_check.passed
            ? <span className="text-xs text-green bg-green/10 px-2 py-0.5 rounded-full">✓ verified</span>
            : <span className="text-xs text-amber bg-amber/10 px-2 py-0.5 rounded-full">⚠ check claims</span>
          }
        </div>
        <span className="text-text3 text-xs">{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <div className="px-4 pb-4 space-y-4 animate-fade-up">
          {/* SQL */}
          <div>
            <p className="text-text3 text-xs mb-1.5 font-medium">SQL Executed</p>
            <pre className="bg-surface2 rounded-lg p-3 text-xs font-mono text-text2 overflow-x-auto whitespace-pre-wrap">{trust.sql}</pre>
          </div>

          {/* Confidence reason */}
          <div>
            <p className="text-text3 text-xs mb-1">{trust.confidence_reason}</p>
          </div>

          {/* Data sources + metrics */}
          <div className="flex flex-wrap gap-2">
            {trust.data_sources.map((s) => (
              <span key={s} className="text-xs bg-blue/10 text-blue px-2 py-0.5 rounded-full">📊 {s}</span>
            ))}
            {trust.metrics_used.map((m) => (
              <span key={m} className="text-xs bg-purple/10 text-purple px-2 py-0.5 rounded-full">⚙ {m}</span>
            ))}
          </div>

          {/* Assumptions */}
          {trust.assumptions.length > 0 && (
            <div>
              <p className="text-text3 text-xs mb-1.5 font-medium">Assumptions</p>
              <div className="flex flex-wrap gap-2">
                {trust.assumptions.map((a, i) => (
                  <span key={i} className="text-xs bg-amber/10 text-amber px-2 py-0.5 rounded-full" title={a.reason}>⚠ {a.value}</span>
                ))}
              </div>
            </div>
          )}

          {/* Hallucination discrepancies */}
          {!trust.hallucination_check.passed && trust.hallucination_check.discrepancies.length > 0 && (
            <div className="bg-amber/5 border border-amber/20 rounded-lg p-3">
              <p className="text-amber text-xs font-medium mb-1">Claim discrepancies detected:</p>
              {trust.hallucination_check.discrepancies.map((d, i) => (
                <p key={i} className="text-text3 text-xs">{d}</p>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ResponseCard({ turn, onFollowUp }: { turn: Turn; onFollowUp: (q: string) => void }) {
  const [feedback, setFeedback] = useState<"up" | "down" | null>(null);
  const [correction, setCorrection] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const r = turn.result;

  if (turn.error) {
    return (
      <div className="bg-red/5 border border-red/20 rounded-xl p-4 animate-fade-up">
        <p className="text-red text-sm">{turn.error}</p>
      </div>
    );
  }
  if (!r) return null;

  const { columns, rows } = r.result;

  async function handleFeedback(helpful: boolean, correctionText?: string) {
    if (submitted || !r?.query_history_id) return;
    await submitFeedback(r.query_history_id, helpful, correctionText).catch(() => {});
    setFeedback(helpful ? "up" : "down");
    setSubmitted(true);
  }

  return (
    <div className="bg-surface border border-border rounded-xl p-5 space-y-4 animate-fade-up">
      {/* Key finding */}
      {r.insights.key_finding && (
        <div className="bg-purple/5 border border-purple/20 rounded-lg px-4 py-3">
          <p className="text-purple text-xs font-medium mb-0.5">Key finding</p>
          <p className="text-text text-sm">{r.insights.key_finding}</p>
        </div>
      )}

      {/* Narrative */}
      <p className="text-text2 text-sm leading-relaxed">{r.narrative}</p>

      {/* Anomalies */}
      {r.insights.anomalies.length > 0 && (
        <div className="space-y-1">
          {r.insights.anomalies.map((a, i) => (
            <div key={i} className="text-amber text-xs bg-amber/5 border border-amber/15 rounded-lg px-3 py-2">{a}</div>
          ))}
        </div>
      )}

      {/* Chart */}
      {r.visualization !== "table" && rows.length > 0 && (
        <AutoChart columns={columns} rows={rows} chartType={r.visualization} />
      )}

      {/* Table */}
      {rows.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-border">
          <table className="w-full text-xs font-mono">
            <thead>
              <tr className="border-b border-border">
                {columns.map((c) => (
                  <th key={c} className="px-3 py-2 text-left text-text3 font-medium">{c}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.slice(0, 20).map((row, ri) => (
                <tr key={ri} className="border-b border-border/50 hover:bg-surface2 transition-colors">
                  {(row as unknown[]).map((cell, ci) => (
                    <td key={ci} className="px-3 py-2 text-text2">{formatVal(cell)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          {rows.length > 20 && (
            <div className="px-3 py-2 text-text3 text-xs text-center">Showing 20 of {rows.length} rows</div>
          )}
        </div>
      )}

      {/* Trust layer */}
      <TrustLayer trust={r.trust_layer} />

      {/* Follow-ups */}
      {r.insights.follow_up_questions.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {r.insights.follow_up_questions.map((q, i) => (
            <button key={i} onClick={() => onFollowUp(q)} className="text-xs bg-surface2 hover:bg-surface3 border border-border text-text2 px-3 py-1.5 rounded-full transition-colors">
              {q}
            </button>
          ))}
        </div>
      )}

      {/* Feedback */}
      <div className="pt-1">
        {submitted ? (
          <p className="text-green text-xs">✓ Thanks for your feedback!</p>
        ) : feedback === "down" ? (
          <div className="space-y-2 animate-fade-up">
            <p className="text-text3 text-xs">What was wrong? (optional)</p>
            <textarea
              value={correction}
              onChange={(e) => setCorrection(e.target.value)}
              placeholder="e.g. The answer ignored the date filter…"
              rows={2}
              className="w-full bg-surface2 border border-border rounded-lg px-3 py-2 text-xs text-text placeholder:text-text3 focus:outline-none focus:border-purple/50 resize-none"
            />
            <div className="flex gap-2">
              <button
                onClick={() => handleFeedback(false, correction)}
                className="text-xs bg-red/10 hover:bg-red/20 text-red border border-red/20 px-3 py-1.5 rounded-lg transition-colors"
              >
                Submit
              </button>
              <button
                onClick={() => setFeedback(null)}
                className="text-xs text-text3 hover:text-text2 px-3 py-1.5 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <span className="text-text3 text-xs">Was this helpful?</span>
            <button
              onClick={() => handleFeedback(true)}
              className="text-sm px-2 py-0.5 rounded transition-colors text-text3 hover:text-green"
            >👍</button>
            <button
              onClick={() => setFeedback("down")}
              className="text-sm px-2 py-0.5 rounded transition-colors text-text3 hover:text-red"
            >👎</button>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────
export default function WorkspacePage() {
  const params = useParams();
  const router = useRouter();
  const workspaceId = params.workspaceId as string;

  const [workspace, setWorkspace] = useState<{ name: string; columns: string[] | null } | null>(null);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingStep, setLoadingStep] = useState(0);
  const [activePanel, setActivePanel] = useState<"schema" | "history" | null>(null);
  const [schemaData, setSchemaData] = useState<{ columns: { name: string; type: string }[] } | null>(null);
  const [historyData, setHistoryData] = useState<{ id: string; query: string; created_at: string }[]>([]);
  const chatRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (!isLoggedIn()) { router.push("/login"); return; }
    loadWorkspace();
  }, [workspaceId]);

  useEffect(() => {
    chatRef.current?.scrollTo({ top: chatRef.current.scrollHeight, behavior: "smooth" });
  }, [turns, loading]);

  async function loadWorkspace() {
    try {
      const res = await getWorkspace(workspaceId);
      setWorkspace({ name: res.data.name, columns: res.data.columns });
    } catch { router.push("/dashboard"); }
  }

  async function sendQuery(q: string) {
    const query = q.trim();
    if (!query || loading) return;
    setInput("");
    setLoading(true);
    setLoadingStep(0);

    const turnId = crypto.randomUUID();
    setTurns((t) => [...t, { id: turnId, query, result: null }]);

    // Animate loading steps
    const delays = [0, 700, 1500, 2300, 3500, 4800];
    delays.forEach((d, i) => setTimeout(() => setLoadingStep(i), d));

    try {
      const res = await runQuery(query, workspaceId);
      setTurns((t) => t.map((turn) => turn.id === turnId ? { ...turn, result: res.data } : turn));
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string | { reason?: string } } } })?.response?.data?.detail;
      const msg = typeof detail === "string" ? detail : detail?.reason ?? "Failed to process query. Check the backend.";
      setTurns((t) => t.map((turn) => turn.id === turnId ? { ...turn, error: msg } : turn));
    } finally {
      setLoading(false);
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }

  async function openSchema() {
    setActivePanel("schema");
    try {
      const res = await getSchema(workspaceId);
      setSchemaData(res.data);
    } catch {}
  }

  async function openHistory() {
    setActivePanel("history");
    try {
      const res = await getHistory(workspaceId);
      setHistoryData(res.data);
    } catch {}
  }

  async function handleClearHistory() {
    await clearHistory(workspaceId);
    setTurns([]);
    setHistoryData([]);
  }

  return (
    <div className="h-screen flex flex-col bg-bg">
      {/* Header */}
      <header className="flex items-center justify-between px-5 py-3 border-b border-border flex-shrink-0">
        <div className="flex items-center gap-3">
          <button onClick={() => router.push("/dashboard")} className="text-text3 hover:text-text2 text-sm transition-colors">← Dashboard</button>
          <span className="text-border">|</span>
          <span className="font-semibold text-sm">{workspace?.name ?? "…"}</span>
          {workspace?.columns && (
            <span className="text-text3 text-xs">{workspace.columns.length} columns</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs bg-green/10 text-green px-2 py-0.5 rounded-full">✓ Hallucination Guard</span>
          <span className="text-xs bg-blue/10 text-blue px-2 py-0.5 rounded-full">✓ Anomaly Detection</span>
          <button onClick={openSchema} className={`text-xs px-3 py-1.5 rounded-lg border transition-colors ${activePanel === "schema" ? "border-purple/50 text-purple bg-purple/10" : "border-border text-text3 hover:text-text2"}`}>Schema</button>
          <button onClick={openHistory} className={`text-xs px-3 py-1.5 rounded-lg border transition-colors ${activePanel === "history" ? "border-purple/50 text-purple bg-purple/10" : "border-border text-text3 hover:text-text2"}`}>History</button>
          {activePanel && <button onClick={() => setActivePanel(null)} className="text-text3 hover:text-text2 text-xs">✕</button>}
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Chat area */}
        <div className="flex flex-col flex-1 overflow-hidden">
          <div ref={chatRef} className="flex-1 overflow-y-auto px-5 py-6 space-y-6">
            {turns.length === 0 && !loading && (
              <div className="text-center py-16 animate-fade-up">
                <div className="w-12 h-12 rounded-xl bg-purple/15 flex items-center justify-center text-purple text-2xl font-bold mx-auto mb-4">X</div>
                <p className="text-text2 font-medium mb-2">Ask anything about your data</p>
                <p className="text-text3 text-sm mb-8">InsightX will generate SQL, run it, and explain the results with full transparency.</p>
                <div className="flex flex-wrap justify-center gap-2">
                  {SUGGESTED.map((q) => (
                    <button key={q} onClick={() => sendQuery(q)} className="text-xs bg-surface border border-border hover:border-purple/30 text-text2 px-3 py-2 rounded-full transition-colors">
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {turns.map((turn) => (
              <div key={turn.id} className="space-y-3">
                {/* User bubble */}
                <div className="flex justify-end">
                  <div className="bg-purple/10 border border-purple/20 text-text text-sm px-4 py-2.5 rounded-2xl rounded-tr-sm max-w-lg">
                    {turn.query}
                  </div>
                </div>
                {/* Response or loading */}
                {turn.result || turn.error ? (
                  <ResponseCard turn={turn} onFollowUp={sendQuery} />
                ) : loading && turn.id === turns[turns.length - 1]?.id ? (
                  <LoadingCard step={loadingStep} />
                ) : null}
              </div>
            ))}
          </div>

          {/* Input */}
          <div className="px-5 py-4 border-t border-border flex-shrink-0">
            <div className="flex gap-3 items-end">
              <textarea
                ref={inputRef}
                rows={1}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendQuery(input); }
                }}
                placeholder="Ask a question about your data… (Enter to send, Shift+Enter for new line)"
                disabled={loading}
                className="flex-1 bg-surface border border-border rounded-xl px-4 py-3 text-sm text-text placeholder:text-text3 resize-none focus:outline-none focus:border-purple/50 disabled:opacity-50 transition-colors max-h-32"
                style={{ minHeight: 48 }}
              />
              <button
                onClick={() => sendQuery(input)}
                disabled={loading || !input.trim()}
                className="bg-purple hover:bg-purple/90 disabled:opacity-40 text-white text-sm font-medium px-4 py-3 rounded-xl transition-colors flex-shrink-0"
              >
                {loading ? "…" : "Send"}
              </button>
            </div>
            <p className="text-text3 text-xs mt-2 text-center">All queries are verified — SQL shown, claims checked, PII blocked.</p>
          </div>
        </div>

        {/* Side panel */}
        {activePanel && (
          <div className="w-80 border-l border-border flex flex-col animate-slide-in flex-shrink-0">
            {activePanel === "schema" && (
              <>
                <div className="px-4 py-3 border-b border-border">
                  <p className="font-medium text-sm">Dataset Schema</p>
                </div>
                <div className="overflow-y-auto flex-1 p-4">
                  {schemaData?.columns.map((c) => (
                    <div key={c.name} className="flex items-center justify-between py-2 border-b border-border/50 last:border-0">
                      <span className="text-sm font-mono text-text2">{c.name}</span>
                      <span className="text-xs text-text3 bg-surface2 px-2 py-0.5 rounded">{c.type}</span>
                    </div>
                  ))}
                </div>
              </>
            )}
            {activePanel === "history" && (
              <>
                <div className="px-4 py-3 border-b border-border flex items-center justify-between">
                  <p className="font-medium text-sm">Query History</p>
                  <button onClick={handleClearHistory} className="text-text3 hover:text-red text-xs transition-colors">Clear all</button>
                </div>
                <div className="overflow-y-auto flex-1 p-2">
                  {historyData.length === 0 ? (
                    <p className="text-text3 text-xs text-center py-8">No history yet.</p>
                  ) : historyData.map((h) => (
                    <button key={h.id} onClick={() => { setActivePanel(null); sendQuery(h.query); }}
                      className="w-full text-left px-3 py-2.5 rounded-lg hover:bg-surface2 transition-colors border-b border-border/30 last:border-0">
                      <p className="text-sm text-text2 truncate">{h.query}</p>
                      <p className="text-xs text-text3 mt-0.5">{new Date(h.created_at).toLocaleString()}</p>
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
