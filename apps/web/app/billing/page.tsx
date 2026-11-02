"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { RequireAuth } from "@/components/require-auth";
import { api, ApiError, BillingSummary, InvoiceResult } from "@/lib/api";

function dollars(cents: number) {
    return `$${(cents / 100).toFixed(2)}`;
}

function BillingContent() {
    const [summary, setSummary] = useState<BillingSummary | null>(null);
    const [invoice, setInvoice] = useState<InvoiceResult | null>(null);
    const [loading, setLoading] = useState(true);
    const [generating, setGenerating] = useState(false);
    const [error, setError] = useState<string | null>(null);

    async function loadSummary() {
        try {
            setSummary(await api.getBillingSummary());
        } catch (err) {
            setError(err instanceof ApiError ? err.message : "Failed to load billing");
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => {
        // Fetch-on-mount is a legitimate effect pattern; the set-state-in-effect
        // rule over-flags it (https://github.com/facebook/react/issues/34743).
        // eslint-disable-next-line react-hooks/set-state-in-effect
        loadSummary();
    }, []);

    async function handleGenerate() {
        setGenerating(true);
        setError(null);
        try {
            setInvoice(await api.generateInvoice());
            await loadSummary();
        } catch (err) {
            setError(err instanceof ApiError ? err.message : "Failed to generate invoice");
        } finally {
            setGenerating(false);
        }


    }

    return (
        <div className="max-w-2xl mx-auto p-8">
            <Link href="/tickets" className="text-sm text-blue-600 mb-4 inline-block">
                ← Back to tickets
            </Link>
            <h1 className="text-2xl font-semibold mb-6">Usage &amp; billing</h1>

            {loading ? (
                <p className="text-gray-500">Loading...</p>
            ) : summary ? (
                <div className="p-6 bg-white border rounded mb-6">
                    <p className="text-sm text-gray-500 mb-1">Unbilled usage</p>
                    <p className="text-3xl font-semibold">{dollars(summary.amount_due_cents)}</p>
                    <p className="text-sm text-gray-500 mt-2">
                        {summary.unbilled_tickets} processed tickets ×{" "}
                        {dollars(summary.price_per_ticket_cents)} per ticket
                    </p>
                    <button
                        onClick={handleGenerate}
                        disabled={generating || summary.unbilled_tickets === 0}
                        className="mt-4 bg-blue-600 text-white rounded px-4 py-2 disabled:opacity-50"
                    >
                        {generating ? "Generating..." : "Generate invoice"}
                    </button>
                </div>
            ) : null}

            {error && <p className="text-red-600 text-sm mb-4">{error}</p>}

            {invoice && (
                <div className="p-4 border rounded bg-green-50">
                    <p className="font-medium">
                        Invoice created for {invoice.tickets_billed} tickets (
                        {dollars(invoice.amount_due_cents)})
                    </p>
                    {invoice.hosted_invoice_url && (
                        <a
                            href={invoice.hosted_invoice_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-600 text-sm"
                        >
                            View invoice (Stripe test mode) →
                        </a>
                    )}
                </div>
            )}
        </div>
    );

}

export default function BillingPage() {
    return (
        <RequireAuth>
            <BillingContent />
        </RequireAuth>
    );
}








