"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
} from "react";
import { useRouter } from "next/navigation";
import { api } from "./api";

type AuthContextType = {
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (
    tenantName: string,
    email: string,
    password: string,
  ) => Promise<void>;
  logout: () => void;
  loading: boolean;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  useEffect(() => {
    // localStorage doesn't exist during server rendering, so the auth check
    // MUST happen here (post-mount, client-only) rather than during initial
    // render — reading it synchronously in render (even via a lazy useState
    // initializer) causes a real hydration mismatch: server always renders
    // "logged out", client would immediately compute "logged in", and React
    // has to discard and redo the whole tree. This effect is the correct,
    // necessary pattern here, despite the lint rule's generic objection.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setIsAuthenticated(!!localStorage.getItem("token"));
    setLoading(false);
  }, []);

  async function login(email: string, password: string) {
    const result = await api.login(email, password);
    localStorage.setItem("token", result.access_token);
    setIsAuthenticated(true);
    router.push("/tickets");
  }

  async function signup(tenantName: string, email: string, password: string) {
    const result = await api.signup(tenantName, email, password);
    localStorage.setItem("token", result.access_token);
    setIsAuthenticated(true);
    router.push("/tickets");
  }

  function logout() {
    localStorage.removeItem("token");
    setIsAuthenticated(false);
    router.push("/login");
  }

  return (
    <AuthContext.Provider
      value={{ isAuthenticated, login, signup, logout, loading }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
}
