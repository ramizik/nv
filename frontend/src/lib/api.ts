// Backend client. See docs/integration-plan.md for the contract.
import type { LeadAnalysis } from "../types/lead";

const BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8090";

// Every lead the voice agent has captured, for the records book.
export async function listLeads(): Promise<LeadAnalysis[]> {
  const res = await fetch(`${BASE}/api/leads`);
  if (!res.ok) throw new Error(`leads failed: ${res.status}`);
  return res.json();
}

// Analyze a live lead transcript (e.g. a Discord voice/text interaction).
export async function analyze(body: unknown): Promise<LeadAnalysis> {
  const res = await fetch(`${BASE}/api/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`analyze failed: ${res.status}`);
  return res.json();
}

export async function health(): Promise<{ status: string; inference_backend: string; chat_backend: string }> {
  const res = await fetch(`${BASE}/api/health`);
  return res.json();
}
