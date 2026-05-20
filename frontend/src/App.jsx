import { useEffect, useState } from 'react';

const VERDICT_CONFIG = {
  SUPPORTED: { label: "Supported", color: "#059669", bg: "#ecfdf5", icon: "✓" },
  DISPUTED: { label: "Disputed", color: "#d97706", bg: "#fffbeb", icon: "⚠" },
  FALSE: { label: "False", color: "#dc2626", bg: "#fef2f2", icon: "✗" },
  INSUFFICIENT_EVIDENCE: { label: "Insufficient Evidence", color: "#6366f1", bg: "#eef2ff", icon: "?" },
  FAKE: { label: "False", color: "#dc2626", bg: "#fef2f2", icon: "✗" },
  VERIFIED: { label: "Supported", color: "#059669", bg: "#ecfdf5", icon: "✓" },
};

const ARCHIVE_LABELS = {
  ARCHIVED: "Stored in archive",
  ALREADY_ARCHIVED: "Already in archive",
  DUPLICATE_DETECTED: "Duplicate detected",
  ESCALATED: "Escalated to human review",
  UNDER_REVIEW: "Under investigation",
};

const PIPELINE_STEPS = [
  { key: "retrieval", label: "Retrieval", icon: "🔍" },
  { key: "credibility_analysis", label: "Credibility", icon: "📊" },
  { key: "contradiction_scan", label: "Contradiction Scan", icon: "⚡" },
  { key: "verdict", label: "Verdict", icon: "⚖️" },
];

function VerdictChip({ verdict }) {
  const config = VERDICT_CONFIG[verdict] || { label: verdict, color: "#64748b", bg: "#f1f5f9", icon: "—" };
  return (
    <span
      className="verdict-chip"
      style={{ color: config.color, background: config.bg, borderColor: `${config.color}30` }}
    >
      <span className="verdict-icon">{config.icon}</span>
      {config.label}
    </span>
  );
}

function ConfidenceBar({ value }) {
  const clampedValue = Math.max(0, Math.min(100, value));
  let barColor;
  if (clampedValue >= 70) barColor = "#059669";
  else if (clampedValue >= 40) barColor = "#d97706";
  else barColor = "#dc2626";

  return (
    <div className="confidence-bar-container">
      <div className="confidence-bar-track">
        <div
          className="confidence-bar-fill"
          style={{ width: `${clampedValue}%`, background: barColor }}
        />
      </div>
      <span className="confidence-bar-label" style={{ color: barColor }}>{clampedValue}/100</span>
    </div>
  );
}

function PipelineViz({ steps, active }) {
  return (
    <div className="pipeline-viz">
      {PIPELINE_STEPS.map((step, idx) => {
        const matched = steps?.find(s => s.step === step.key);
        const isActive = active && matched;
        return (
          <div key={step.key} className="pipeline-step-wrap">
            <div
              className={`pipeline-step ${isActive ? "pipeline-step-active" : ""}`}
              title={matched?.detail || ""}
            >
              <span className="pipeline-icon">{step.icon}</span>
              <span className="pipeline-label">{step.label}</span>
            </div>
            {idx < PIPELINE_STEPS.length - 1 && (
              <div className={`pipeline-arrow ${isActive ? "pipeline-arrow-active" : ""}`}>→</div>
            )}
          </div>
        );
      })}
    </div>
  );
}

function App() {
  const apiBaseUrl = (import.meta.env.VITE_API_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");
  const [claim, setClaim] = useState("");
  const [response, setResponse] = useState(null);
  const [loading, setLoading] = useState(false);
  const [reviewQueue, setReviewQueue] = useState([]);
  const [queueError, setQueueError] = useState(null);

  const hasClaim = claim.trim().length > 0;

  const fetchReviewQueue = async () => {
    try {
      const res = await fetch(`${apiBaseUrl}/review-queue`);
      const data = await res.json();
      setReviewQueue(data.items || []);
      setQueueError(null);
    } catch (error) {
      console.error("Error loading review queue:", error);
      setQueueError("Failed to load review queue.");
    }
  };

  useEffect(() => {
    fetchReviewQueue();
  }, []);
  
  const submitClaim = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${apiBaseUrl}/submit-claim`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ 
          text: claim,
      }),
    });

    const data = await res.json();
    setResponse(data);
    fetchReviewQueue();
  } catch (error) {
    console.error("Error submitting claim:", error);
  } finally {
    setLoading(false);
  }
};

  const handleSubmit = (event) => {
    event.preventDefault();
    if (!hasClaim || loading) {
      return;
    }
    submitClaim();
  };

  const verdict = response?.verdict || response?.status;
  const archiveAction = response?.archive_action;

  return (
    <div className="app">
      <header className="app-header">
        <h1>Sentinels of Truth</h1>
        <p className="app-subtitle">
          AI-powered claim verification with explainable evidence aggregation.
        </p>
      </header>

      <section className="panel pipeline-panel">
        <p className="pipeline-title">Verification Pipeline</p>
        <PipelineViz steps={response?.analysis_steps} active={!!response} />
      </section>

      <section className="panel">
        <h2 className="section-title">Submit a claim</h2>
        <form className="claim-form" onSubmit={handleSubmit}>
          <input
            type="text"
            id="claim-input"
            placeholder="Enter a claim to verify…"
            value={claim}
            onChange={(e) => setClaim(e.target.value)}
            className="text-input"
          />
          <button className="primary-button" id="verify-button" type="submit" disabled={!hasClaim || loading}>
            {loading ? "Analyzing…" : "Verify"}
          </button>
        </form>
      </section>

      <section className="panel" id="results-panel">
        <div className="section-head">
          <h2 className="section-title">Verification Result</h2>
          {verdict && <VerdictChip verdict={verdict} />}
        </div>
        {!response && (
          <p className="muted">Submit a claim above to see results.</p>
        )}
        {response && (
          <div className="result-block">
            <dl className="data-grid">
              <div className="data-row">
                <dt>Claim</dt>
                <dd>{response.claim || claim}</dd>
              </div>
              <div className="data-row">
                <dt>Verdict</dt>
                <dd>
                  <VerdictChip verdict={verdict} />
                </dd>
              </div>
              {archiveAction && (
                <div className="data-row">
                  <dt>Archive Status</dt>
                  <dd className="archive-status">{ARCHIVE_LABELS[archiveAction] || archiveAction}</dd>
                </div>
              )}
              {response.confidence !== undefined && (
                <div className="data-row">
                  <dt>Confidence</dt>
                  <dd>
                    <ConfidenceBar value={response.confidence} />
                  </dd>
                </div>
              )}
              {response.reason && (
                <div className="data-row">
                  <dt>Reasoning</dt>
                  <dd className="reason-text">{response.reason}</dd>
                </div>
              )}
              {response.credibility_average !== undefined && response.credibility_average > 0 && (
                <div className="data-row">
                  <dt>Avg. Credibility</dt>
                  <dd>
                    <ConfidenceBar value={response.credibility_average} />
                  </dd>
                </div>
              )}
            </dl>

            {Array.isArray(response.source_assessment) && response.source_assessment.length > 0 && (
              <div className="list-block">
                <p className="list-title">Source Credibility Assessment</p>
                <ul className="source-assess-list">
                  {response.source_assessment.map((item) => {
                    let credColor;
                    if (item.credibility >= 80) credColor = "#059669";
                    else if (item.credibility >= 60) credColor = "#d97706";
                    else credColor = "#dc2626";
                    return (
                      <li key={item.url} className="source-item">
                        <a
                          className="link source-url"
                          href={item.url}
                          target="_blank"
                          rel="noreferrer"
                        >
                          {new URL(item.url).hostname.replace("www.", "")}
                        </a>
                        <span className="source-score" style={{ color: credColor, borderColor: `${credColor}30`, background: `${credColor}10` }}>
                          {item.credibility}/100
                        </span>
                        <span className="source-label">{item.label}</span>
                      </li>
                    );
                  })}
                </ul>
              </div>
            )}

            {Array.isArray(response.analysis_steps) && response.analysis_steps.length > 0 && (
              <div className="list-block">
                <p className="list-title">Analysis Trace</p>
                <ul className="trace-list">
                  {response.analysis_steps.map((step, idx) => (
                    <li key={idx} className="trace-item">
                      <span className="trace-step">{step.step}</span>
                      <span className="trace-detail">{step.detail}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </section>

      <section className="panel" id="review-panel">
        <div className="section-head">
          <h2 className="section-title">Human Review Queue</h2>
          <span className="count-chip">{reviewQueue.length}</span>
        </div>
        {queueError && <p className="muted">{queueError}</p>}
        {!queueError && reviewQueue.length === 0 && (
          <p className="muted">No claims awaiting review.</p>
        )}
        {reviewQueue.length > 0 && (
          <ul className="queue-list">
            {reviewQueue.map((item) => (
              <li key={item.id} className="queue-item">
                <div className="queue-row">
                  <span className="queue-label">Claim</span>
                  <span className="queue-value">{item.claim}</span>
                </div>
                <div className="queue-row">
                  <span className="queue-label">Verdict</span>
                  <span className="queue-value">
                    <VerdictChip verdict={item.verdict || item.verification_status || item.decision} />
                  </span>
                </div>
                <div className="queue-row">
                  <span className="queue-label">Escalation</span>
                  <span className="queue-value">{item.status}</span>
                </div>
                {item.message && (
                  <div className="queue-row">
                    <span className="queue-label">Note</span>
                    <span className="queue-value">{item.message}</span>
                  </div>
                )}
                {item.reason && (
                  <div className="queue-row">
                    <span className="queue-label">Reasoning</span>
                    <span className="queue-value">{item.reason}</span>
                  </div>
                )}
                {Array.isArray(item.sources) && item.sources.length > 0 && (
                  <div className="queue-row">
                    <span className="queue-label">Sources</span>
                    <span className="queue-value">
                      <ul className="list">
                        {item.sources.map((source) => (
                          <li key={source}>
                            <a
                              className="link"
                              href={source}
                              target="_blank"
                              rel="noreferrer"
                            >
                              {source}
                            </a>
                          </li>
                        ))}
                      </ul>
                    </span>
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

export default App;
