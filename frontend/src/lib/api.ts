// Backend client. See docs/integration-plan.md for the contract.
import type { LeadAnalysis } from "../types/lead";

function defaultApiBase(): string {
  if (typeof window !== "undefined") {
    const { protocol, hostname } = window.location;
    if (hostname && hostname !== "localhost" && hostname !== "127.0.0.1") {
      return `${protocol}//${hostname}:8090`;
    }
  }
  return "http://localhost:8090";
}

const ENV_BASE = (import.meta.env.VITE_API_BASE ?? "").trim();
const BASE =
  ENV_BASE && !/^https?:\/\/(localhost|127\.0\.0\.1):8090\/?$/.test(ENV_BASE)
    ? ENV_BASE
    : defaultApiBase();

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

// ---- Appointments ----
export interface Appointment {
  lead_id: string;
  name: string;
  phone: string;
  service_interest?: string[];
  timeline?: string;
  label?: string;
  score?: number;
  after_hours?: boolean;
  received_at?: string;
  estimated_value?: string;
  recommended_action?: string;
  appointment: {
    scheduled: boolean;
    when?: string | null;
    notes?: string | null;
    email: { sent: boolean; to: string[]; error?: string | null };
  };
}

// All patients who called AND scheduled a consult.
export async function listAppointments(): Promise<Appointment[]> {
  const res = await fetch(`${BASE}/api/appointments`);
  if (!res.ok) throw new Error(`appointments failed: ${res.status}`);
  return res.json();
}

// Schedule a consult for a lead — backend emails both clinic owners every time.
export async function scheduleAppointment(leadId: string, when?: string, notes?: string): Promise<Appointment> {
  const res = await fetch(`${BASE}/api/leads/${leadId}/schedule`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ when, notes }),
  });
  if (!res.ok) throw new Error(`schedule failed: ${res.status}`);
  return res.json();
}
