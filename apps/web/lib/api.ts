const API_URL = process.env.NEXT_PUBLIC_API_URL;

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("token");
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "COntent-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });

  if (!response.ok) {
    const body = await response
      .json()
      .catch(() => ({ detail: "Unknown error" }));
    throw new ApiError(response.status, body.detail || "Request failed");
  }

  // 204/empty responses have no body to parse
  const text = await response.text();
  return text ? JSON.parse(text) : (undefined as T);
}

export const api = {
  signup: (tenant_name: string, email: string, password: string) =>
    request<{ access_token: string; token_type: string }>("/auth/signup", {
      method: "POST",
      body: JSON.stringify({ tenant_name, email, password }),
    }),

  login: (email: string, password: string) =>
    request<{ access_token: string; token_type: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  listTickets: () => request<Ticket[]>(`/tickets`),

  getTicket: (id: string) => request<Ticket>(`/tickets/${id}`),

  createTicket: (subject: string, body: string) =>
    request<Ticket>(`/tickets`, {
      method: "POST",
      body: JSON.stringify({ subject, body }),
    }),

  approveTicket: (id: string) =>
    request<Ticket>(`/tickets/${id}/approve`, { method: "POST" }),

  rejectTicket: (id: string) =>
    request<Ticket>(`/tickets/${id}/reject`, { method: "POST" }),
};

export type Ticket = {
  id: string;
  subject: string;
  body: string;
  status: "pending" | "pending_approval" | "sent" | "rejected";
  category: string | null;
  ai_draft: string | null;
  priority: string | null;
  created_at: string;
  updated_at: string;
};

export { ApiError };
