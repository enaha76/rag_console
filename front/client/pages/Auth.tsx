import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/AuthContext";
import { useNavigate } from "react-router-dom";

export default function AuthPage() {
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [provider, setProvider] = useState<string>("");
  const [model, setModel] = useState<string>("");
  const nav = useNavigate();
  const { login, signup } = useAuth();

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      if (mode === "login") {
        const form = new FormData(e.target as HTMLFormElement);
        const ok = await login({
          email: String(form.get("email")),
          password: String(form.get("password")),
        });
        if (!ok) throw new Error("Invalid credentials");
      } else {
        const form = new FormData(e.target as HTMLFormElement);
        const ok = await signup({
          email: String(form.get("email")),
          username: String(form.get("username")),
          password: String(form.get("password")),
          llm_provider: provider || undefined,
          llm_model: model || undefined,
        });
        if (!ok) throw new Error("Signup failed");
      }
      nav("/chat");
    } catch (e: any) {
      setError(e?.message || "Authentication error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen grid place-items-center bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <div className="w-full max-w-md p-6 rounded-2xl bg-white/5 backdrop-blur border border-white/10 text-slate-100 shadow-xl">
        <div className="flex justify-between items-center mb-4">
          <h1 className="text-xl font-semibold">{mode === "login" ? "Welcome back" : "Create organization"}</h1>
          <button onClick={() => setMode(mode === "login" ? "signup" : "login")} className="text-blue-300 hover:text-blue-200 text-sm">
            {mode === "login" ? "Need an account?" : "Have an account?"}
          </button>
        </div>
        <form onSubmit={onSubmit} className="space-y-4">
          {mode === "login" ? (
            <>
              <div>
                <Label htmlFor="email" className="text-slate-200">Email</Label>
                <Input id="email" name="email" type="email" required placeholder="you@example.com" className="mt-1 bg-white/10 border-white/20 text-slate-100 placeholder:text-slate-400" />
              </div>
              <div>
                <Label htmlFor="password" className="text-slate-200">Password</Label>
                <Input id="password" name="password" type="password" required className="mt-1 bg-white/10 border-white/20 text-slate-100" />
              </div>
            </>
          ) : (
            <>
              <div className="grid grid-cols-1 gap-3">
                <div>
                  <Label htmlFor="email" className="text-slate-200">Email</Label>
                  <Input id="email" name="email" type="email" required className="mt-1 bg-white/10 border-white/20 text-slate-100" />
                </div>
                <div>
                  <Label htmlFor="username" className="text-slate-200">Username</Label>
                  <Input id="username" name="username" required className="mt-1 bg-white/10 border-white/20 text-slate-100" />
                </div>
                <div>
                  <Label htmlFor="password" className="text-slate-200">Password</Label>
                  <Input id="password" name="password" type="password" required className="mt-1 bg-white/10 border-white/20 text-slate-100" />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label htmlFor="llm_provider" className="text-slate-200">LLM Provider (optional)</Label>
                    <select
                      id="llm_provider"
                      name="llm_provider"
                      className="mt-1 bg-white/10 border-white/20 text-slate-100 w-full rounded px-3 py-2"
                      value={provider}
                      onChange={(e) => {
                        setProvider(e.target.value);
                        setModel("");
                      }}
                    >
                      <option value="">Select provider</option>
                      <option value="openai">OpenAI</option>
                      <option value="anthropic">Anthropic</option>
                    </select>
                  </div>
                  <div>
                    <Label htmlFor="llm_model" className="text-slate-200">LLM Model (optional)</Label>
                    <select
                      id="llm_model"
                      name="llm_model"
                      className="mt-1 bg-white/10 border-white/20 text-slate-100 w-full rounded px-3 py-2"
                      value={model}
                      onChange={(e) => setModel(e.target.value)}
                      disabled={!provider}
                    >
                      <option value="">{provider ? "Select model" : "Select provider first"}</option>
                      {provider === "openai" && (
                        <>
                          <option value="gpt-4.1-nano">gpt-4.1-nano</option>
                          <option value="gpt-4.1-mini">gpt-4.1-mini</option>
                          <option value="gpt-4.1">gpt-4.1</option>
                        </>
                      )}
                      {provider === "anthropic" && (
                        <>
                          <option value="claude-3-5-sonnet-20241022">Claude 3.5 Sonnet (2024-10-22)</option>
                          <option value="claude-3-5-haiku-20241022">Claude 3.5 Haiku (2024-10-22)</option>
                          <option value="claude-3-opus-20240229">Claude 3 Opus (2024-02-29)</option>
                          <option value="claude-3-sonnet-20240229">Claude 3 Sonnet (2024-02-29)</option>
                          <option value="claude-3-haiku-20240307">Claude 3 Haiku (2024-03-07)</option>
                        </>
                      )}
                    </select>
                  </div>
                </div>
              </div>
            </>
          )}
          {error && <div className="text-rose-300 text-sm">{error}</div>}
          <Button type="submit" disabled={loading} className="w-full bg-blue-600 hover:bg-blue-500 text-white">
            {loading ? "Please wait..." : mode === "login" ? "Login" : "Create & Login"}
          </Button>
        </form>
      </div>
    </div>
  );
}
