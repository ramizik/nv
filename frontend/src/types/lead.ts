// TS mirror of shared/schemas/lead_analysis.schema.json — the one object the whole UI renders.
export type ScoreLabel = "hot" | "warm" | "cold";

export interface TranscriptTurn {
  speaker: "lead" | "agent";
  text: string;
  ts?: string;
}

export interface Extracted {
  service_interest?: string[];
  timeline?: string;
  deadline_weeks?: number | null;
  urgency?: "low" | "medium" | "high";
  financing_interest?: boolean;
  budget_signal?: string;
  insurance_mentioned?: boolean;
  decision_stage?: string;
}

export interface Score {
  label: ScoreLabel;
  value?: number;
  confidence: number;
  reason_tags?: string[];
  urgency_reasoning?: string;
}

export interface DealValue {
  currency?: string;
  low?: number;
  high?: number;
  basis?: string;
}

export interface ContextHit {
  label: string;
  value: string;
  source?: string;
  matched?: boolean;
}

export interface AgentAction {
  type: string;
  label: string;
  status: "done" | "pending" | "failed";
  ts?: string;
  detail?: string;
}

export interface NextBestAction {
  recommendation?: string;
  draft_followup?: string;
  channel?: "call" | "sms" | "email";
}

export interface Notification {
  platform?: string;
  sent?: boolean;
  preview_markdown?: string;
}

export interface SystemStatus {
  component: string;
  status: "online" | "mock" | "degraded" | "offline";
  detail?: string;
}

export interface LeadAnalysis {
  lead_id: string;
  received_at?: string;
  channel?: string;
  after_hours?: boolean;
  lead?: { name?: string; phone?: string; email?: string };
  summary?: string;
  transcript: TranscriptTurn[];
  extracted: Extracted;
  score: Score;
  estimated_deal_value?: DealValue;
  clinic_context_hits: ContextHit[];
  actions: AgentAction[];
  next_best_action?: NextBestAction;
  notification?: Notification;
  system_status: SystemStatus[];
}
