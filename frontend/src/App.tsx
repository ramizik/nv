// Dashboard root. One button -> POST /api/simulate -> render the whole LeadAnalysis across
// 9 panels. Falls back to the bundled golden fixture if the backend is unreachable, so the
// demo surface always shows something.
import { useEffect, useState } from "react";
import type { LeadAnalysis } from "./types/lead";
import { simulate, health, goldenFixture } from "./lib/api";
import {
  LeadSummaryPanel, ScorePanel, TranscriptPanel, ExtractedPanel, ContextPanel,
  TimelinePanel, NextBestActionPanel, ChatPreviewPanel, SystemHealthPanel,
} from "./components/panels";

export default function App() {
  const [data, setData] = useState<LeadAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [banner, setBanner] = useState<string | null>(null);
  const [backends, setBackends] = useState<{ inference: string; chat: string } | null>(null);

  useEffect(() => {
    health()
      .then((h) => setBackends({ inference: h.inference_backend, chat: h.chat_backend }))
      .catch(() => setBackends(null));
  }, []);

  async function runSimulate() {
    setLoading(true);
    setBanner(null);
    try {
      setData(await simulate());
    } catch {
      // Backend down — show the bundled golden fixture so the demo never dead-ends.
      setData(goldenFixture);
      setBanner("Backend unreachable — showing bundled golden fixture. Start the backend on :8080 for live runs.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <header className="header">
        <div className="brand">
          <h1><span className="spark">◆</span> Local Voice Lead Closer</h1>
          <span className="sub">on-prem agent · Dell Pro Max GB10</span>
        </div>
        <div className="header-right">
          <div className="health-pills">
            <span className={`pill ${backends ? "online" : "offline"}`}><span className="dot" />API {backends ? "online" : "down"}</span>
            {backends && <span className={`pill ${backends.inference === "nemotron" ? "online" : "mock"}`}><span className="dot" />infer:{backends.inference}</span>}
            {backends && <span className={`pill ${backends.chat === "discord" ? "online" : "mock"}`}><span className="dot" />chat:{backends.chat}</span>}
          </div>
          <button className="btn-simulate" onClick={runSimulate} disabled={loading}>
            {loading ? "Analyzing…" : "▶ Simulate Inbound Call"}
          </button>
        </div>
      </header>

      {banner && <div className="banner err">{banner}</div>}

      {!data ? (
        <div className="banner idle">
          Click <b>Simulate Inbound Call</b> to run the after-hours veneers lead through the agent.
        </div>
      ) : (
        <div className="grid">
          <LeadSummaryPanel a={data} />
          <ScorePanel score={data.score} />
          <TranscriptPanel turns={data.transcript} />
          <ExtractedPanel e={data.extracted} />
          <ContextPanel hits={data.clinic_context_hits} />
          <TimelinePanel actions={data.actions} />
          <NextBestActionPanel nba={data.next_best_action} />
          <ChatPreviewPanel n={data.notification} />
          <SystemHealthPanel status={data.system_status} />
        </div>
      )}
    </div>
  );
}
