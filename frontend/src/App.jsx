import { useEffect, useState } from 'react';

function App() {
  const apiBaseUrl = (import.meta.env.VITE_API_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");
  const [claim, setClaim] = useState("");
  const [response, setResponse] = useState(null);
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
  }
};

  const handleSubmit = (event) => {
    event.preventDefault();
    if (!hasClaim) {
      return;
    }
    submitClaim();
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>Sentinels of Truth</h1>
        <p className="app-subtitle">
          Minimal claim verification with sources and review queue.
        </p>
      </header>

      <section className="panel">
        <h2 className="section-title">Submit a claim</h2>
        <form className="claim-form" onSubmit={handleSubmit}>
          <input
            type="text"
            placeholder="Enter your claim"
            value={claim}
            onChange={(e) => setClaim(e.target.value)}
            className="text-input"
          />
          <button className="primary-button" type="submit" disabled={!hasClaim}>
            Verify
          </button>
        </form>
      </section>

      <section className="panel">
        <div className="section-head">
          <h2 className="section-title">Latest result</h2>
          {response?.status && (
            <span className="status-chip">{response.status}</span>
          )}
        </div>
        {!response && (
          <p className="muted">No results yet.</p>
        )}
        {response && (
          <div className="result-block">
            <dl className="data-grid">
              <div className="data-row">
                <dt>Claim</dt>
                <dd>{response.claim || claim}</dd>
              </div>
              <div className="data-row">
                <dt>Decision</dt>
                <dd>{response.decision}</dd>
              </div>
              {response.message && (
                <div className="data-row">
                  <dt>Message</dt>
                  <dd>{response.message}</dd>
                </div>
              )}
              {response.confidence !== undefined && (
                <div className="data-row">
                  <dt>Confidence</dt>
                  <dd>{response.confidence}</dd>
                </div>
              )}
              {response.reason && (
                <div className="data-row">
                  <dt>Reason</dt>
                  <dd>{response.reason}</dd>
                </div>
              )}
            </dl>

            {Array.isArray(response.sources) && response.sources.length > 0 && (
              <div className="list-block">
                <p className="list-title">Sources</p>
                <ul className="list">
                  {response.sources.map((source) => (
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
              </div>
            )}
            {Array.isArray(response.source_assessment) && response.source_assessment.length > 0 && (
              <div className="list-block">
                <p className="list-title">Source credibility</p>
                <ul className="list">
                  {response.source_assessment.map((item) => (
                    <li key={item.url}>
                      <a
                        className="link"
                        href={item.url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        {item.url}
                      </a>
                      <span className="meta">{item.credibility}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </section>

      <section className="panel">
        <div className="section-head">
          <h2 className="section-title">Human review queue</h2>
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
                  <span className="queue-label">Decision</span>
                  <span className="queue-value">{item.decision}</span>
                </div>
                <div className="queue-row">
                  <span className="queue-label">Status</span>
                  <span className="queue-value">{item.status}</span>
                </div>
                {item.message && (
                  <div className="queue-row">
                    <span className="queue-label">Message</span>
                    <span className="queue-value">{item.message}</span>
                  </div>
                )}
                {item.reason && (
                  <div className="queue-row">
                    <span className="queue-label">Reason</span>
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

