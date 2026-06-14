// Backend client. See docs/integration-plan.md for the contract.
import type { LeadAnalysis } from "../types/lead";
import fixture from "../data/veneers_wedding.analysis.json";

const BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8080";

// The bundled golden fixture — lets the dashboard render even if the backend is down.
export const goldenFixture = fixture as unknown as LeadAnalysis;

export async function simulate(): Promise<LeadAnalysis> {
  const res = await fetch(`${BASE}/api/simulate`, { method: "POST" });
  if (!res.ok) throw new Error(`simulate failed: ${res.status}`);
  return res.json();
}

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
