"use client";

import { useState, useEffect, SyntheticEvent } from "react";
import Link from "next/link";
import { RequireAuth } from "@/components/require-auth";
import { useAuth } from "@/lib/auth-context";
import { api, Ticket, ApiError } from "@/lib/api";

const STATUS_STYLES: Record<Ticket["status"], string> = {
  pending: "bg-grey-100 text-grey-700",
  pending_approval: "bg-yellow-100 text-yellow-800",
  sent: "bg-green-100 text-green-800",
  rejected: "bg-red-100 text-red-800",
};

function TicketsPageContent() {
  const { logout } = useAuth();
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(true);
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadTickets() {
    try {
      const data = await api.listTickets();
      setTickets(data);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Failed to load tickets",
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    // Polling fetch-on-mount is a legitimate effect pattern; this rule currently
    // over-flags it as a false positive: https://github.com/facebook/react/issues/34743
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadTickets();
    // Poll every 4s so tickets the worker is still processing update
    // without a manual refresh - a real product would use a websocket
    // or SSE here; polling is the simple, honest choice for this scope.
    const interval = setInterval(loadTickets, 4000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleCreate(e: SyntheticEvent) {
    e.preventDefault();
    setCreating(true);
    setError(null);
    try {
      await api.createTicket(subject, body);
      setSubject("");
      setBody("");
      await loadTickets();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Failed to create ticket",
      );
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="max-w-3xl mx-auto p-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-semibold">Tickets</h1>
        <button onClick={logout} className="text-sm text-gray-500">
          Log out
        </button>
      </div>

      <form
        onSubmit={handleCreate}
        className="mb-8 p-4 border rounded space-y-3"
      >
        <h2 className="font-medium">New Ticket</h2>
        <input
          placeholder="Subject"
          required
          value={subject}
          onChange={(e) => setSubject(e.target.value)}
          className="w-full border rounded px-3 py-2"
        />
        <textarea
          placeholder="Describe the issue"
          required
          value={body}
          onChange={(e) => setBody(e.target.value)}
          className="w-full border rounded px-3 py-2"
          rows={3}
        />
        <button
          type="submit"
          disabled={creating}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
        >
          {creating ? "Submitting..." : "Submit Ticket"}
        </button>
      </form>

      {error && <p className="text-red-600 text-sm mb-4">{error}</p>}

      {loading ? (
        <p className="text-gray-500">Loading...</p>
      ) : tickets.length === 0 ? (
        <p className="text-gray-500">No tickets yet.</p>
      ) : (
        <ul className="space-y-2">
          {tickets.map((t) => (
            <li key={t.id}>
              <Link
                href={`/tickets/${t.id}`}
                className="flex justify-between items-center p-4 border rounded hover:bg-gray-50"
              >
                <div>
                  <p className="font-medium">{t.subject}</p>
                  <p className="text-sm text-gray-500">
                    {t.category ?? "Uncategorized"} . {t.priority ?? "-"}
                  </p>
                </div>
                <span
                  className={`text-xs px-2 py-1 rounded ${STATUS_STYLES[t.status]}`}
                >
                  {t.status.replace("_", " ")}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function TicketsPage() {
  return (
    <RequireAuth>
      <TicketsPageContent />
    </RequireAuth>
  );
}
