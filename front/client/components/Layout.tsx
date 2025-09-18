import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { vectorStatus } from "@/lib/api";
import { useState } from "react";

export default function Layout() {
  const { user, logout } = useAuth();
  const [apiOk, setApiOk] = useState<null | boolean>(null);
  const [apiMsg, setApiMsg] = useState<string>("");

  const testApi = async () => {
    try {
      const res = await vectorStatus();
      setApiOk(true);
      setApiMsg(`Vector index: ${res.index_count ?? "ok"}`);
    } catch (e: any) {
      setApiOk(false);
      setApiMsg(e?.message || "API error");
    }
  };

  return (
    <div className="min-h-screen grid grid-cols-1 lg:grid-cols-[280px_1fr]">
      <aside className="bg-slate-900 text-slate-100 p-4 lg:min-h-screen">
        <Link to="/chat" className="block mb-6">
          <div className="text-xl font-bold tracking-tight">
            RAG Console
          </div>
          <div className="text-xs text-slate-400">{user?.username || user?.email || "Signed out"}</div>
        </Link>
        <nav className="space-y-1 text-sm">
          <NavLink to="/chat" className={({ isActive }) => `block px-3 py-2 rounded-md ${isActive ? "bg-slate-800" : "hover:bg-slate-800/60"}`}>Chat</NavLink>
          <NavLink to="/documents" className={({ isActive }) => `block px-3 py-2 rounded-md ${isActive ? "bg-slate-800" : "hover:bg-slate-800/60"}`}>Documents</NavLink>
          <NavLink to="/history" className={({ isActive }) => `block px-3 py-2 rounded-md ${isActive ? "bg-slate-800" : "hover:bg-slate-800/60"}`}>History</NavLink>
        </nav>
        <div className="mt-6 space-y-2">
          <Button onClick={testApi} variant="secondary" className="w-full bg-blue-600 hover:bg-blue-500 text-white">
            Test API
          </Button>
          <Button onClick={logout} variant="ghost" className="w-full text-slate-200">Logout</Button>
        </div>
        {apiOk !== null && (
          <div className={`mt-6 text-xs p-2 rounded border ${apiOk ? "border-emerald-400 text-emerald-300" : "border-rose-400 text-rose-300"}`}>
            {apiMsg}
          </div>
        )}
        <div className="mt-6 text-xs text-slate-400">
          <div>User: <span className="text-slate-200">{user?.email || "-"}</span></div>
          <div>LLM: <span className="text-slate-200">{user?.llm_provider || "-"} {user?.llm_model || ""}</span></div>
        </div>
      </aside>
      <main className="bg-gradient-to-br from-slate-50 via-white to-slate-100 min-h-screen">
        <Outlet />
      </main>
    </div>
  );
}
