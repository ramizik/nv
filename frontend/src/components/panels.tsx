// All dashboard panels. Each takes the relevant slice of LeadAnalysis and renders one
// operator-facing surface. Panel order mirrors DEMO_SCRIPT.md / integration-plan.md.
import type {
  LeadAnalysis, Score, Extracted, ContextHit, AgentAction,
  NextBestAction, Notification, SystemStatus, TranscriptTurn, DealValue,
} from "../types/lead";

export function Panel({ idx, title, span, children }: { idx?: string; title: string; span: string; children: React.ReactNode; }) {
  return (
    <section className={`panel ${span}`}>
      <h2 className="panel-title">{idx && <span className="idx">{idx}</span>} {title}</h2>
      {children}
    </section>
  );
}

const money = (n?: number) => `$${(n ?? 0).toLocaleString()}`;

export function LeadSummaryPanel({ a }: { a: LeadAnalysis }) {
  const d: DealValue = a.estimated_deal_value ?? {};
  return (
    <Panel idx="01" title="Lead Summary" span="col-5">
      <div className="lead-top">
        <div>
          <p className="lead-name">{a.lead?.name ?? "Unknown caller"}</p>
          <div className="lead-meta">📞 {a.lead?.phone ?? "n/a"} · {a.channel ?? "voice"}</div>
        </div>
        {a.after_hours && <span className="badge-afterhours">AFTER HOURS</span>}
      </div>
      <p className="summary-text">{a.summary ?? "—"}</p>
      <div className="deal">
        <div className="label">Estimated deal value</div>
        <div className="amount">{money(d.low)} – {money(d.high)}</div>
        {d.basis && <div className="basis">{d.basis}</div>}
      </div>
    </Panel>
  );
}

export function ScorePanel({ score }: { score: Score }) {
  const conf = Math.round((score.confidence ?? 0) * 100);
  return (
    <Panel idx="02" title="Qualification Score" span="col-7">
      <div className="score-wrap">
        <div className={`score-badge ${score.label}`}>
          <span className="lbl">{score.label.toUpperCase()}</span>
          <span className="val">{score.value ?? "?"}/100</span>
        </div>
        <div className="score-side">
          <div className="conf-row">
            <span>confidence</span>
            <span className="conf-bar"><span className="conf-fill" style={{ width: `${conf}%` }} /></span>
            <span>{conf}%</span>
          </div>
          <div className="chips">
            {(score.reason_tags ?? []).map((t) => (
              <span key={t} className={`chip ${score.label === "hot" ? "hot" : ""}`}>{t}</span>
            ))}
          </div>
          {score.urgency_reasoning && <div className="urgency"><b>Urgency:</b> {score.urgency_reasoning}</div>}
        </div>
      </div>
    </Panel>
  );
}

export function TranscriptPanel({ turns }: { turns: TranscriptTurn[] }) {
  return (
    <Panel idx="03" title="Transcript" span="col-5">
      <div className="transcript">
        {turns.length === 0 && <div className="empty">No call yet.</div>}
        {turns.map((t, i) => (
          <div key={i} className={`turn ${t.speaker}`}>
            <div className="who">{t.speaker === "lead" ? "Lead" : "Agent"}</div>
            <div className="bubble">{t.text}{t.ts && <span className="ts">{t.ts}</span>}</div>
          </div>
        ))}
      </div>
    </Panel>
  );
}

export function ExtractedPanel({ e }: { e: Extracted }) {
  const rows: [string, React.ReactNode][] = [
    ["Service interest", (e.service_interest ?? []).join(", ") || "—"],
    ["Timeline", e.timeline ?? "—"],
    ["Urgency", e.urgency ?? "—"],
    ["Financing interest", <Bool v={e.financing_interest} />],
    ["Budget signal", e.budget_signal ?? "—"],
    ["Insurance mentioned", <Bool v={e.insurance_mentioned} />],
    ["Decision stage", (e.decision_stage ?? "—").replace(/_/g, " ")],
  ];
  return (
    <Panel idx="04" title="Extracted Intents / Entities" span="col-7">
      <div className="kv">
        {rows.map(([k, v]) => (
          <div className="kv-row" key={k}><span className="k">{k}</span><span className="v">{v}</span></div>
        ))}
      </div>
    </Panel>
  );
}

function Bool({ v }: { v?: boolean }) {
  return <span className={v ? "tag-true" : "tag-false"}>{v ? "✓ yes" : "— no"}</span>;
}

export function ContextPanel({ hits }: { hits: ContextHit[] }) {
  return (
    <Panel idx="05" title="Company Context Retrieved" span="col-5">
      {hits.length === 0 && <div className="empty">No context consulted yet.</div>}
      {hits.map((h, i) => (
        <div className="hit" key={i}>
          <div className={`mk ${h.matched ? "ok" : "no"}`}>{h.matched ? "✓" : "·"}</div>
          <div className="body">
            <div className="h">{h.label}</div>
            <div className="s">{h.value}</div>
            {h.source && <div className="src">{h.source}</div>}
          </div>
        </div>
      ))}
    </Panel>
  );
}

export function TimelinePanel({ actions }: { actions: AgentAction[] }) {
  return (
    <Panel idx="06" title="Agent Action Timeline" span="col-7">
      <div className="timeline">
        {actions.length === 0 && <div className="empty">No actions yet.</div>}
        {actions.map((act, i) => (
          <div className="tl-item" key={i}>
            <div className={`tl-dot ${act.status}`} />
            <div className="tl-body">
              <div className="t">{act.label}</div>
              <div className="meta">{act.type} · {act.status}{act.ts ? ` · ${act.ts}` : ""}</div>
            </div>
          </div>
        ))}
      </div>
    </Panel>
  );
}

export function NextBestActionPanel({ nba }: { nba?: NextBestAction }) {
  return (
    <Panel idx="07" title="Next Best Action" span="col-5">
      {!nba ? <div className="empty">—</div> : (
        <>
          <div className="nba-rec">{nba.recommendation}</div>
          <div className="nba-draft">
            <div className="lbl"><span>Drafted follow-up</span><span className="chan">via {nba.channel ?? "call"}</span></div>
            <div className="body">{nba.draft_followup}</div>
          </div>
        </>
      )}
    </Panel>
  );
}

// minimal **bold** renderer for the chat markdown
function renderMd(md: string) {
  return md.split("\n").map((line, i) => (
    <div key={i}>
      {line.split(/(\*\*[^*]+\*\*)/g).map((seg, j) =>
        seg.startsWith("**") && seg.endsWith("**")
          ? <strong key={j}>{seg.slice(2, -2)}</strong>
          : <span key={j}>{seg}</span>
      )}
    </div>
  ));
}

export function ChatPreviewPanel({ n }: { n?: Notification }) {
  return (
    <Panel idx="08" title="Chat Notification Preview" span="col-7">
      {!n?.preview_markdown ? <div className="empty">No alert yet.</div> : (
        <>
          <div className="chat-card">
            <div className="chat-head">
              <div className="chat-avatar">A</div>
              <span className="chat-bot">Lead Closer</span>
              <span className="chat-tag">BOT</span>
            </div>
            <div className="chat-body">{renderMd(n.preview_markdown)}</div>
          </div>
          <div className={`chat-status ${n.sent ? "sent" : ""}`}>
            {n.sent ? `✓ posted to ${n.platform}` : `⚠ preview only (${n.platform})`}
          </div>
        </>
      )}
    </Panel>
  );
}

export function SystemHealthPanel({ status }: { status: SystemStatus[] }) {
  return (
    <Panel idx="09" title="System Health / Model Status" span="col-12">
      {status.map((s, i) => (
        <div className="sys-row" key={i}>
          <div><span className="c">{s.component}</span> <span className="d">{s.detail}</span></div>
          <span className={`sys-status ${s.status}`}>{s.status}</span>
        </div>
      ))}
    </Panel>
  );
}
