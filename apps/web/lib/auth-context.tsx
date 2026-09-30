"use client";

import { createContext, useContext, useState, ReactNode } from "react";
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

function getInitialAuthState(): boolean {
  if (typeof window === "undefined") return false;
  return !!localStorage.getItem("token");
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(getInitialAuthState);
  const [loading, setLoading] = useState(false);
  const router = useRouter();

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
  if (!context) throw new Error("useAuth must be used within aAuthProvider");
  return context;
}
