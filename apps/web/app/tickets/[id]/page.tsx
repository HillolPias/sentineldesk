"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { RequireAuth } from "@/components/require-auth";
import { api, Ticket, ApiError } from "@/lib/api";

function TicketDetailContent() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const [ticket, setTicket] = useState<Ticket | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadTicket() {
    try {
      const data = await api.getTicket(id);
      setTicket(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load ticket");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    // loadTickets is intentionally omitted — it's redefined every render but
    // doesn't depend on changing props/state; including it would re-trigger
    // this effect on every render.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadTicket();
    const interval = setInterval(loadTicket, 4000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  async function handleApprove() {
    setActionLoading(true);
    setError(null);
    try {
      const updated = await api.approveTicket(id);
      setTicket(updated);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to approve");
    } finally {
      setActionLoading(false);
    }
  }

  async function handleReject() {
    setActionLoading(true);
    setError(null);
    try {
      const updated = await api.rejectTicket(id);
      setTicket(updated);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to reject");
    } finally {
      setActionLoading(false);
    }
  }

  if (loading) return <p className="p-8 text-gray-500">Loading...</p>;
  if (!ticket)
    return <p className="p-8 text-red-600">{error ?? "Ticket not found"}</p>;

  return (
    <div className="max-w-2xl mx-auto p-8">
      <Link href="/tickets" className="text-sm text-blue-600 mb-4 inline-block">
        &larr; Back to Tickets
      </Link>

      <h1 className="text-2xl font-semibold mb-1">{ticket.subject}</h1>
      <p className="text-sm text-gray-500 mb-6">
        {ticket.category ?? "uncategorized"} • {ticket.priority ?? "-"} priority
        • {ticket.status.replace("_", " ")}
      </p>

      <div className="mb-6">
        <h2 className="text-sm font-medium text-gray-500 mb-1">
          Customer message
        </h2>
        <p className="p-4 border rounded bg-gray-50 whitespace-pre-wrap">
          {ticket.body}
        </p>
      </div>

      {ticket.status === "pending" && (
        <p className="text-sm text-gray-500 italic">
          AI is still processing this ticket...
        </p>
      )}

      {ticket.ai_draft && (
        <div className="mb-6">
          <h2 className="text-sm font-medium text-gray-500 mb-1">
            AI-drafted reply
          </h2>
          <p className="p-4 border rounded bg-blue-50 whitespace-pre-wrap">
            {ticket.ai_draft}
          </p>
        </div>
      )}

      {error && <p className="text-red-600 text-sm mb-4">{error}</p>}

      {ticket.status === "pending_approval" && (
        <div className="flex gap-3">
          <button
            onClick={handleApprove}
            disabled={actionLoading}
            className="bg-green-600 text-white rounded px-4 py-2 disabled:opacity-50"
          >
            {actionLoading ? "..." : "Approve & send"}
          </button>
          <button
            onClick={handleReject}
            disabled={actionLoading}
            className="bg-red-600 text-white rounded px-4 py-2 disabled:opacity-50"
          >
            {actionLoading ? "..." : "Reject"}
          </button>
        </div>
      )}
    </div>
  );
}

export default function TicketDetailPage() {
  return (
    <RequireAuth>
      <TicketDetailContent />
    </RequireAuth>
  );
}
