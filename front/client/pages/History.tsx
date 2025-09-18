import { useEffect, useMemo, useState } from "react";
import { queryHistory } from "@/lib/api";
import { useNavigate } from "react-router-dom";

interface QueryItem {
  id: string;
  query_text: string;
  status?: string;
  processing_time_ms?: number;
  retrieved_chunks_count?: number;
  llm_provider?: string;
  llm_model?: string;
  total_tokens?: number;
  created_at?: string;
  session_id?: string;
  response?: {
    response_text?: string;
    context_chunks?: string[];
    generated_at?: string;
  } | null;
}

export default function HistoryPage() {
  const [items, setItems] = useState<QueryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [sessionFilter, setSessionFilter] = useState<string>("");
  const [sortBy, setSortBy] = useState<string>("created_at_desc");
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const navigate = useNavigate();

  function formatDuration(ms?: number) {
    if (ms == null) return "—";
    if (ms < 1000) return `${Math.round(ms)} ms`;
    if (ms < 60_000) return `${(ms / 1000).toFixed(1)} s`;
    const totalSeconds = Math.round(ms / 1000);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${minutes}:${seconds.toString().padStart(2, "0")} min`;
  }

  useEffect(() => {
    (async () => {
      try {
        setLoading(true);
        const res = await queryHistory(0, 50, sessionFilter || undefined);
        const list = (res.queries || []) as QueryItem[];
        setItems(list);
      } catch (e: any) {
        setError(e?.message || "Failed to load history");
      } finally {
        setLoading(false);
      }
    })();
  }, [sessionFilter]);

  const sessions = useMemo(() => {
    const s = new Set<string>();
    items.forEach((q) => { if (q.session_id) s.add(q.session_id); });
    return Array.from(s);
  }, [items]);

  const filtered = useMemo(() => {
    let list = items.slice();
    if (statusFilter !== "all") list = list.filter((q) => (q.status || "").toLowerCase() === statusFilter);
    switch (sortBy) {
      case "created_at_asc":
        list.sort((a,b) => new Date(a.created_at||0).getTime() - new Date(b.created_at||0).getTime());
        break;
      case "processing_time_desc":
        list.sort((a,b) => (b.processing_time_ms||0) - (a.processing_time_ms||0));
        break;
      case "processing_time_asc":
        list.sort((a,b) => (a.processing_time_ms||0) - (b.processing_time_ms||0));
        break;
      case "tokens_desc":
        list.sort((a,b) => (b.total_tokens||0) - (a.total_tokens||0));
        break;
      case "tokens_asc":
        list.sort((a,b) => (a.total_tokens||0) - (b.total_tokens||0));
        break;
      default:
        list.sort((a,b) => new Date(b.created_at||0).getTime() - new Date(a.created_at||0).getTime());
    }
    return list;
  }, [items, statusFilter, sortBy]);

  return (
    <div className="max-w-5xl mx-auto p-4 lg:p-8">
      <div className="flex items-center justify-between mb-3">
        <h1 className="text-2xl font-semibold text-slate-900">History</h1>
        <div className="flex items-center gap-2 text-sm">
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="border rounded px-2 py-1">
            <option value="all">All status</option>
            <option value="completed">Completed</option>
            <option value="processing">Processing</option>
            <option value="failed">Failed</option>
          </select>
          <select value={sortBy} onChange={(e) => setSortBy(e.target.value)} className="border rounded px-2 py-1">
            <option value="created_at_desc">Newest</option>
            <option value="created_at_asc">Oldest</option>
            <option value="processing_time_desc">Longest time</option>
            <option value="processing_time_asc">Shortest time</option>
            <option value="tokens_desc">Tokens high→low</option>
            <option value="tokens_asc">Tokens low→high</option>
          </select>
          <select value={sessionFilter} onChange={(e) => setSessionFilter(e.target.value)} className="border rounded px-2 py-1">
            <option value="">All sessions</option>
            {sessions.map((s) => (
              <option key={s} value={s}>{s.slice(0,8)}…</option>
            ))}
          </select>
        </div>
      </div>
      {loading ? (
        <p className="text-slate-600">Loading…</p>
      ) : error ? (
        <p className="text-rose-600">{error}</p>
      ) : filtered.length === 0 ? (
        <p className="text-slate-600">No queries yet.</p>
      ) : (
        <div className="rounded-xl border bg-white">
          <div className="grid grid-cols-8 text-sm font-medium text-slate-700 px-4 py-2 border-b">
            <div className="col-span-4">Query</div>
            <div>Time</div>
            <div>Status</div>
            <div>Tokens</div>
            <div>Model</div>
          </div>
          <div className="divide-y">
            {filtered.map((q) => {
              const isOpen = !!expanded[q.id];
              return (
                <div key={q.id} className="text-sm">
                  <div className="grid grid-cols-8 px-4 py-2 items-center">
                    <button className="col-span-4 text-left truncate hover:underline" title={q.query_text} onClick={() => setExpanded((e) => ({...e, [q.id]: !e[q.id]}))}>
                      {q.query_text}
                    </button>
                    <div>{formatDuration(q.processing_time_ms)}</div>
                    <div>
                      <span className={`text-xs px-2 py-1 rounded-full border ${q.status === 'completed' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : q.status === 'processing' ? 'bg-amber-50 text-amber-700 border-amber-200' : 'bg-rose-50 text-rose-700 border-rose-200'}`}>
                        {q.status || 'completed'}
                      </span>
                    </div>
                    <div>{q.total_tokens ?? '—'}</div>
                    <div className="truncate" title={`${q.llm_provider||'-'} ${q.llm_model||''}`}>{q.llm_provider || '-'} {q.llm_model || ''}</div>
                  </div>
                  {isOpen ? (
                    <div className="px-4 pb-3 text-slate-700">
                      {q.response?.response_text ? (
                        <details open className="mb-2">
                          <summary className="cursor-pointer text-slate-600">Assistant response</summary>
                          <div className="mt-2 whitespace-pre-wrap text-slate-800 bg-slate-50 border rounded p-3 max-h-60 overflow-auto">{q.response.response_text}</div>
                        </details>
                      ) : null}
                      <div className="flex items-center gap-2">
                        <button className="text-blue-600 hover:underline" onClick={() => {
                          try { sessionStorage.setItem('chat_session_id', q.session_id || ''); } catch {}
                          navigate('/chat');
                        }}>Open in Chat</button>
                        <button className="text-slate-600 hover:underline" onClick={() => navigator.clipboard.writeText(q.response?.response_text || '')}>Copy response</button>
                      </div>
                    </div>
                  ) : null}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
