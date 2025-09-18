import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { login as apiLogin, signup as apiSignup, setToken, getToken, AuthUser } from "@/lib/api";

interface AuthState {
  token: string | null;
  user: AuthUser | null;
}

interface AuthContextValue extends AuthState {
  login: (args: { email: string; password: string }) => Promise<boolean>;
  signup: (args: { email: string; username: string; password: string; llm_provider?: string; llm_model?: string }) => Promise<boolean>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setTok] = useState<string | null>(getToken());
  const [user, setUser] = useState<AuthUser | null>(null);

  const logout = useCallback(() => {
    setToken(null);
    setTok(null);
    setUser(null);
  }, []);

  const login = useCallback(async (args: { email: string; password: string }) => {
    try {
      const res = await apiLogin(args);
      if (!res?.access_token) return false;
      setTok(res.access_token);
      setUser(res.user);
      return true;
    } catch {
      return false;
    }
  }, []);

  const signup = useCallback(async (args: { email: string; username: string; password: string; llm_provider?: string; llm_model?: string }) => {
    try {
      const res = await apiSignup(args);
      if (!res?.access_token) return false;
      setTok(res.access_token);
      setUser(res.user);
      return true;
    } catch {
      return false;
    }
  }, []);

  const value = useMemo(() => ({ token, user, login, signup, logout }), [login, logout, signup, token, user]);

  useEffect(() => {
    // global 401 handler: monkey-patch fetch to catch 401 and logout
    const orig = window.fetch;
    window.fetch = async (input: any, init?: RequestInit) => {
      const res = await orig(input, init);
      if (res.status === 401) logout();
      return res;
    };
    return () => {
      window.fetch = orig;
    };
  }, [logout]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
