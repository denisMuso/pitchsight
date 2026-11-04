import { useEffect, useState } from "react";
import { api } from "./api";
type Health = { status: string; mode: string; research_only: boolean };
type Sync = {
  id: number;
  created_at: string;
  mode: string;
  status: string;
  detail: string;
};
export default function System() {
  const [health, setHealth] = useState<Health | null>(null),
    [ready, setReady] = useState<{ database: string; model: string } | null>(
      null,
    ),
    [sync, setSync] = useState<Sync[]>([]),
    [error, setError] = useState("");
  useEffect(() => {
    Promise.all([
      api<Health>("/health"),
      api<{ database: string; model: string }>("/ready"),
      api<{ items: Sync[] }>("/api/sync/status"),
    ])
      .then(([h, r, s]) => {
        setHealth(h);
        setReady(r);
        setSync(s.items);
      })
      .catch((e) => setError(e.message));
  }, []);
  return (
    <>
      <div className="panel">
        <p className="eyebrow">LOCAL WORKSPACE / TRANSPARENT LIMITS</p>
        <h2>Research, with human responsibility.</h2>
        <p className="muted">
          PitchSight is an unofficial decision-support application. It is not
          affiliated with IFAB, SoccerNet, the Premier League, or UEFA. Match
          metadata does not contain labeled VAR video. Authorized footage and
          independent human judgment remain essential.
        </p>
        <div className="stats">
          <article>
            <label>Backend</label>
            <strong className="small-value">
              {health?.status || "Connecting"}
            </strong>
            <small>Loopback only · single local worker</small>
          </article>
          <article>
            <label>Database</label>
            <strong className="small-value">
              {ready?.database || "Checking"}
            </strong>
            <small>SQLite · {health?.mode || "unknown"} mode</small>
          </article>
          <article>
            <label>Model registry</label>
            <strong className="small-value">
              {ready?.model === "AVAILABLE" ? "Available" : "Unavailable"}
            </strong>
            <small>No model means no predictions</small>
          </article>
        </div>
      </div>
      {error && <p className="error">{error}</p>}
      <div className="panel">
        <h2>Source and sync history</h2>
        {sync.map((s) => (
          <div key={s.id}>
            <p>
              {s.mode.toUpperCase()} · {s.status}
            </p>
            <p className="muted">{s.detail}</p>
            <small className="muted">
              {new Date(s.created_at).toLocaleString()}
            </small>
          </div>
        ))}
        {!sync.length && <p className="muted">No sync has been recorded.</p>}
      </div>
      <div className="panel">
        <h2>Sources & research context</h2>
        <div className="stack">
          <a
            href="https://www.football-data.org/documentation/api"
            target="_blank"
            rel="noreferrer"
          >
            football-data.org — match metadata
          </a>
          <a
            href="https://github.com/SoccerNet/sn-mvfoul"
            target="_blank"
            rel="noreferrer"
          >
            SoccerNet MV-Foul — authorized research dataset
          </a>
          <a
            href="https://www.theifab.com/laws/latest/offside/"
            target="_blank"
            rel="noreferrer"
          >
            IFAB Law 11 — offside position and offence
          </a>
          <a href="http://127.0.0.1:8000/docs" target="_blank" rel="noreferrer">
            Local API documentation
          </a>
        </div>
        <p className="muted">
          Footage, labels and checkpoints stay local. Synthetic examples are for
          engineering checks. No professional officiating accuracy is claimed.
        </p>
      </div>
    </>
  );
}
