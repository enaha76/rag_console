import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ragQuery, ragStream, queryHistory } from "@/lib/api";

interface Message {
  id: string;
  role: "user" | "assistant";
  text: string;
  createdAt: string;
  meta?: { processing_time_ms?: number; total_tokens?: number; sources?: any[] };
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [stream, setStream] = useState(true);
  const [includeSources, setIncludeSources] = useState(true);
  const [maxChunks, setMaxChunks] = useState(5);
  const [temperature, setTemperature] = useState(0.7);
  const [scoreThreshold, setScoreThreshold] = useState(0.3);
  const [maxTokens, setMaxTokens] = useState(1000);
  const [showParams, setShowParams] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [hydrating, setHydrating] = useState<boolean>(true);

  const bottomRef = useRef<HTMLDivElement>(null);
  const scrollToBottom = () => bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  useEffect(() => scrollToBottom(), [messages.length]);
  // Initialize or load a session_id and hydrate messages from history
  useEffect(() => {
    try {
      const key = "chat_session_id";
      let sid = sessionStorage.getItem(key);
      if (!sid) {
        sid = crypto.randomUUID();
        sessionStorage.setItem(key, sid);
      }
      setSessionId(sid);
    } catch {
      // Fallback: generate without storage
      setSessionId(crypto.randomUUID());
    }
  }, []);

  useEffect(() => {
    (async () => {
      if (!sessionId) return;
      setHydrating(true);
      try {
        const hist = await queryHistory(0, 50, sessionId);
        const items = (hist?.queries || []).slice().reverse(); // oldest -> newest
        const hydrated: Message[] = [];
        for (const q of items) {
          hydrated.push({ id: String(q.id) + ":u", role: "user", text: q.query_text, createdAt: q.created_at || new Date().toISOString() });
          if (q.response?.response_text) {
            hydrated.push({ id: String(q.id) + ":a", role: "assistant", text: q.response.response_text, createdAt: q.response.generated_at || q.created_at || new Date().toISOString(), meta: { processing_time_ms: q.processing_time_ms, total_tokens: q.total_tokens, sources: q.response?.context_chunks } });
          }
        }
        if (hydrated.length) setMessages(hydrated);
      } catch (e) {
        // Ignore hydrate errors
      } finally {
        setHydrating(false);
      }
    })();
  }, [sessionId]);

  const disableSubmit = !query.trim() || loading;

  async function send() {
    if (disableSubmit) return;
    setLoading(true);
    const userMsg: Message = { id: crypto.randomUUID(), role: "user", text: query, createdAt: new Date().toISOString() };
    const assistantMsg: Message = { id: crypto.randomUUID(), role: "assistant", text: "", createdAt: new Date().toISOString(), meta: {} };
    setMessages((m) => [...m, userMsg, assistantMsg]);
    setQuery("");

    const payload = {
      query: userMsg.text,
      max_chunks: maxChunks,
      score_threshold: scoreThreshold,
      temperature,
      max_tokens: maxTokens,
      include_sources: includeSources,
      session_id: sessionId || undefined,
    };

    const start = performance.now();
    try {
      if (stream) {
        await ragStream(payload, (chunk) => {
          setMessages((prev) => prev.map((msg) => msg.id === assistantMsg.id ? { ...msg, text: msg.text + chunk } : msg));
        });
      } else {
        const res = await ragQuery(payload);
        setMessages((prev) => prev.map((msg) => msg.id === assistantMsg.id ? { ...msg, text: res.response || "", meta: { processing_time_ms: res.processing_time_ms, total_tokens: res.total_tokens, sources: res.context_documents } } : msg));
      }
      const ms = Math.round(performance.now() - start);
      setMessages((prev) => prev.map((msg) => msg.id === assistantMsg.id ? { ...msg, meta: { ...(msg.meta || {}), processing_time_ms: (msg.meta?.processing_time_ms ?? 0) || ms } } : msg));
    } catch (e: any) {
      setMessages((prev) => prev.map((msg) => msg.id === assistantMsg.id ? { ...msg, text: `Error: ${e?.message || "Failed to generate"}` } : msg));
    } finally {
      setLoading(false);
    }
  }

  function clear() {
    setMessages([]);
  }

  return (
    <div className="max-w-5xl mx-auto p-4 lg:p-8">
      <header className="mb-4 lg:mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Chat</h1>
          <p className="text-slate-600">Ask questions against your knowledge base.</p>
        </div>
        <Button
          aria-haspopup="dialog"
          title="Query settings"
          onClick={() => setShowParams(true)}
          className="bg-slate-100 hover:bg-slate-200 text-slate-800"
        >
          {/* Gear icon */}
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
            <path fillRule="evenodd" d="M11.078 2.25c-.317 0-.61.18-.752.463l-1.5 3A.844.844 0 018.078 6h-2.5a.75.75 0 00-.53.22l-2 2a.75.75 0 000 1.06l1.768 1.768a.844.844 0 010 1.193L3.048 13.01a.75.75 0 000 1.061l2 2c.14.14.331.22.53.22h2.5c.325 0 .62.186.75.477l1.5 3a.844.844 0 001.504 0l1.5-3a.844.844 0 01.75-.477h2.5c.199 0 .39-.08.53-.22l2-2a.75.75 0 000-1.06l-1.768-1.769a.844.844 0 010-1.192L20.952 9.28a.75.75 0 000-1.06l-2-2a.75.75 0 00-.53-.22h-2.5a.844.844 0 01-.75-.477l-1.5-3a.844.844 0 00-.752-.463zm.922 8.25a2.25 2.25 0 100 4.5 2.25 2.25 0 000-4.5z" clipRule="evenodd" />
          </svg>
          <span className="ml-2 hidden sm:inline">Settings</span>
        </Button>
      </header>

      {showParams ? (
        <div className="fixed inset-0 z-50">
          <div className="absolute inset-0 bg-black/40" onClick={() => setShowParams(false)} />
          <div className="absolute inset-x-4 md:inset-x-auto md:right-8 top-16 md:top-20 md:w-[520px] rounded-2xl bg-white shadow-xl border border-slate-200 p-4">
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-medium text-slate-800">Query parameters</h2>
              <Button onClick={() => setShowParams(false)} className="bg-slate-100 hover:bg-slate-200 text-slate-800">Close</Button>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
              <div>
                <Label htmlFor="maxChunks">Max context chunks</Label>
                <Input id="maxChunks" type="number" min={1} max={50} value={maxChunks} onChange={(e) => setMaxChunks(Number(e.target.value))} />
              </div>
              <div>
                <Label htmlFor="temperature">Temperature</Label>
                <Input id="temperature" type="number" step="0.1" min={0} max={2} value={temperature} onChange={(e) => setTemperature(Number(e.target.value))} />
              </div>
              <div>
                <Label htmlFor="scoreThreshold">Similarity threshold</Label>
                <Input id="scoreThreshold" type="number" step="0.05" min={0} max={1} value={scoreThreshold} onChange={(e) => setScoreThreshold(Number(e.target.value))} />
              </div>
              <div>
                <Label htmlFor="maxTokens">Max tokens</Label>
                <Input id="maxTokens" type="number" min={64} max={8000} value={maxTokens} onChange={(e) => setMaxTokens(Number(e.target.value))} />
              </div>
              <div className="col-span-2 md:col-span-1 flex items-center gap-2">
                <input id="includeSources" type="checkbox" checked={includeSources} onChange={(e) => setIncludeSources(e.target.checked)} className="h-4 w-4" />
                <Label htmlFor="includeSources">Include sources</Label>
              </div>
              <div className="col-span-2 md:col-span-1 flex items-center gap-2">
                <input id="stream" type="checkbox" checked={stream} onChange={(e) => setStream(e.target.checked)} className="h-4 w-4" />
                <Label htmlFor="stream">Stream response</Label>
              </div>
            </div>
          </div>
        </div>
      ) : null}

      {/* Chat window */}
      <section className="rounded-2xl p-4 lg:p-6 bg-gradient-to-br from-white to-slate-50 border border-slate-200 shadow-sm">
        <div className="space-y-4 max-h-[75vh] overflow-y-auto pr-1">
          {hydrating ? (
            <div className="flex items-center gap-2 text-slate-500 text-sm">
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"></path>
              </svg>
              Loading previous messages…
            </div>
          ) : messages.length === 0 ? (
            <div className="text-sm text-slate-500">Start the conversation by asking a question below.</div>
          ) : null}
          {messages.map((m, idx) => {
            const isLast = idx === messages.length - 1;
            const showSpinner = loading && isLast && m.role === "assistant" && !m.text;
            return (
            <div key={m.id} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm shadow ${m.role === "user" ? "bg-blue-600 text-white" : "bg-slate-100 text-slate-800"}`}>
                <div className="whitespace-pre-wrap leading-relaxed">
                  {showSpinner ? (
                    <div className="flex items-center gap-2 text-slate-500">
                      <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"></path>
                      </svg>
                      Generating response…
                    </div>
                  ) : (
                    m.text
                  )}
                </div>
                <div className="mt-2 text-[11px] opacity-75 flex items-center gap-2">
                  <span>{new Date(m.createdAt).toLocaleTimeString()}</span>
                  {m.role === "assistant" && (m.meta?.processing_time_ms || m.meta?.total_tokens) && (
                    <>
                      <span>•</span>
                      {m.meta?.processing_time_ms ? <span>{m.meta.processing_time_ms} ms</span> : null}
                      {m.meta?.total_tokens ? <span>{m.meta.total_tokens} tokens</span> : null}
                    </>
                  )}
                </div>
                {m.role === "assistant" && m.meta?.sources?.length ? (
                  <details className="mt-2">
                    <summary className="cursor-pointer">Sources ({m.meta.sources.length})</summary>
                    <ul className="mt-2 list-disc pl-5 text-[12px] space-y-1">
                      {m.meta.sources.map((s: any, i: number) => (
                        <li key={i}>
                          <span className="font-medium">{s.source}</span> p.{s.page_number} — score {Math.round((s.score || 0) * 100)}%
                        </li>
                      ))}
                    </ul>
                  </details>
                ) : null}
              </div>
            </div>
          );})}
          <div ref={bottomRef} />
        </div>

        {/* Composer */}
        <div className="mt-4 rounded-xl border border-slate-200 bg-white p-2">
          <div className="flex items-end gap-2">
            <div className="flex-1">
              <Label htmlFor="query" className="sr-only">Your question</Label>
              <Input id="query" placeholder="Ask anything..." value={query} onChange={(e) => setQuery(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }} />
            </div>
            <Button onClick={send} disabled={disableSubmit} className="bg-blue-600 hover:bg-blue-500 text-white min-w-24">{loading ? "Sending..." : "Send"}</Button>
            <Button onClick={clear} variant="ghost">Clear</Button>
          </div>
        </div>
      </section>
    </div>
  );
}
