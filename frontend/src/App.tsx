// Voice Lead Records. The record book of every caller the Discord voice agent has handled
// (people asking about cosmetic-dental services at BrightSmile). Records are created live —
// a voice/text interaction in Discord flows through the agent into the backend, which
// persists each qualified lead at /api/leads. This view lists them (auto-refreshing) and
// expands the full agent analysis when you click a row.
import { useEffect, useState } from "react";
import type { LeadAnalysis } from "./types/lead";
import { listLeads, health } from "./lib/api";
import {
  LeadSummaryPanel, ScorePanel, TranscriptPanel, ExtractedPanel, ContextPanel,
  TimelinePanel, NextBestActionPanel, ChatPreviewPanel, SystemHealthPanel,
  AppointmentPanel,
} from "./components/panels";

const money = (n?: number) => (n == null ? "—" : `$${n.toLocaleString()}`);
const POLL_MS = 5000;

function fmtWhen(a: LeadAnalysis): string {
  if (a.received_at) {
    const d = new Date(a.received_at);
    if (!isNaN(d.getTime()))
      return d.toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
    return a.received_at;
  }
  return a.lead_id;
}

export default function App() {
  const [leads, setLeads] = useState<LeadAnalysis[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [banner, setBanner] = useState<string | null>(null);
  const [backends, setBackends] = useState<{ inference: string; chat: string } | null>(null);

  async function refresh() {
    setLoading(true);
    try {
      setLeads(await listLeads());
      setBanner(null);
    } catch {
      setBanner("Backend unreachable on :8090 — start it to see live lead records.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    health()
      .then((h) => setBackends({ inference: h.inference_backend, chat: h.chat_backend }))
      .catch(() => setBackends(null));
    refresh();
    const t = setInterval(refresh, POLL_MS); // live updates as new Discord leads land
    return () => clearInterval(t);
  }, []);

  const selected = leads.find((l) => l.lead_id === selectedId) ?? null;

  return (
    <div className="app">
      <header className="header">
        <div className="brand">
          <h1><span className="spark">◆</span> Voice Lead Records</h1>
          <span className="sub">Discord voice agent · BrightSmile Aesthetics · GB10</span>
        </div>
        <div className="header-right">
          <div className="health-pills">
            <span className={`pill ${backends ? "online" : "offline"}`}><span className="dot" />API {backends ? "online" : "down"}</span>
            {backends && <span className={`pill ${backends.inference !== "mock" ? "online" : "mock"}`}><span className="dot" />infer:{backends.inference}</span>}
            {backends && <span className={`pill ${backends.chat !== "mock" ? "online" : "mock"}`}><span className="dot" />chat:{backends.chat}</span>}
          </div>
          <button className="btn-action" onClick={refresh} disabled={loading}>
            {loading ? "Refreshing…" : "↻ Refresh"}
          </button>
        </div>
      </header>

      {banner && <div className="banner err">{banner}</div>}

      <div className="records-head">
        <span className="rec-count">{leads.length} lead{leads.length === 1 ? "" : "s"} on record · auto-refresh on</span>
        {selected && <button className="link-btn" onClick={() => setSelectedId(null)}>✕ close detail</button>}
      </div>

      {leads.length === 0 ? (
        <div className="banner idle">
          No leads on record yet. Start a <b>voice or text interaction with the agent in Discord</b> —
          when a caller asks about a cosmetic-dental service, the agent qualifies them and their
          record appears here live.
        </div>
      ) : (
        <table className="leads-table">
          <thead>
            <tr>
              <th>Caller</th><th>Requested service</th><th>Intent</th>
              <th>Appointment</th><th>Est. value</th><th>Channel</th><th>Received</th>
            </tr>
          </thead>
          <tbody>
            {leads.map((l) => {
              const label = l.score?.label ?? "cold";
              const svc = (l.extracted?.service_interest ?? []).join(", ") || "—";
              const deal = l.estimated_deal_value;
              return (
                <tr
                  key={l.lead_id}
                  className={l.lead_id === selectedId ? "sel" : ""}
                  onClick={() => setSelectedId(l.lead_id === selectedId ? null : l.lead_id)}
                >
                  <td>
                    <div className="cl-name">{l.lead?.name ?? "Unknown caller"}</div>
                    <div className="cl-sub">{l.lead?.phone ?? l.lead_id}</div>
                  </td>
                  <td>{svc}</td>
                  <td>
                    <span className={`mini-badge ${label}`}>
                      {label.toUpperCase()}{l.score?.value != null ? ` ${l.score.value}` : ""}
                    </span>
                  </td>
                  <td>
                    <span className={`appt-tag ${l.appointment?.requested ? "requested" : "none"}`}>
                      {l.appointment?.requested ? (l.appointment.status ?? "requested").replace(/_/g, " ") : "—"}
                    </span>
                  </td>
                  <td className="mono">{deal ? `${money(deal.low)}–${money(deal.high)}` : "—"}</td>
                  <td><span className="chan-tag">{l.channel ?? "voice"}{l.after_hours ? " · after-hrs" : ""}</span></td>
                  <td className="mono dim">{fmtWhen(l)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}

      {selected && (
        <>
          <div className="detail-head">Agent analysis — <b>{selected.lead?.name ?? selected.lead_id}</b></div>
          <div className="grid">
            <LeadSummaryPanel a={selected} />
            <ScorePanel score={selected.score} />
            <TranscriptPanel turns={selected.transcript} />
            <ExtractedPanel e={selected.extracted} />
            <ContextPanel hits={selected.clinic_context_hits} />
            <TimelinePanel actions={selected.actions} />
            <NextBestActionPanel nba={selected.next_best_action} />
            <AppointmentPanel appointment={selected.appointment} />
            <ChatPreviewPanel n={selected.notification} />
            <SystemHealthPanel status={selected.system_status} />
          </div>
        </>
      )}
    </div>
  );
}
