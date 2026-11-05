import { useEffect, useState } from "react";
import { api, Match, score } from "./api";
import "./style.css";
import Incidents from "./Incidents";
import ModelLab from "./ModelLab";
import Offside from "./Offside";
import System from "./System";

const pages = [
  "Overview",
  "Match Explorer",
  "Incident Review",
  "Model Lab",
  "Offside Lab",
  "System / About",
];
export default function App() {
  const [page, setPage] = useState("Overview");
  const [competition, setCompetition] = useState("");
  const [status, setStatus] = useState("");
  const [offset, setOffset] = useState(0);
  const [total, setTotal] = useState(0);
  const pageSize = 25;
  const [rows, setRows] = useState<Match[]>([]);
  const [competitions, setCompetitions] = useState<
    { id: string; name: string }[]
  >([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [mode, setMode] = useState("");
  const [modelStatus, setModelStatus] = useState("Checking");
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    Promise.all([
      api<{ items: Match[]; total: number }>(
        `/api/matches?competition=${encodeURIComponent(competition)}&status=${encodeURIComponent(status)}&limit=${pageSize}&offset=${offset}`,
      ),
      api<{ id: string; name: string }[]>("/api/competitions"),
      api<{ mode: string }>("/health"),
      api<{ status: string }>("/api/models"),
    ])
      .then(([m, c, h, model]) => {
        if (active) {
          setRows(m.items);
          setTotal(m.total);
          setCompetitions(c);
          setMode(h.mode);
          setModelStatus(model.status === "AVAILABLE" ? "Available" : "Not registered");
        }
      })
      .catch((e) => {
        if (active) setError(e.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [competition, status, retry, offset]);
  return (
    <div className="shell">
      <aside>
        <div className="brand">
          <span className="brandmark">P</span>PitchSight
          <span className="beta">LAB</span>
        </div>
        <p className="nav-label">RESEARCH WORKSPACE</p>
        <nav>
          {pages.map((name, i) => (
            <button
              key={name}
              className={page === name ? "selected" : ""}
              onClick={() => setPage(name)}
            >
              <span>{["◈", "▤", "▷", "◉", "⌖", "⚙"][i]}</span>
              {name}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <span className="dot" /> Local workspace
          <p>Human judgment stays central.</p>
          <small>Unofficial research software</small>
        </div>
      </aside>
      <main>
        <header>
          <div className="breadcrumb">
            Workspace <span>/</span> {page}
          </div>
          <div className="pill">
            {mode === "demo"
              ? "DEMO DATA"
              : mode === "live"
                ? "LIVE API"
                : "CONNECTING"}
          </div>
        </header>
        <section className="content">
          <div className="heading">
            <div>
              <p className="eyebrow">FOOTBALL · EVIDENCE · PERSPECTIVE</p>
              <h1>
                {page === "Overview" ? "A clearer view of the game." : page}
              </h1>
              <p className="sub">
                {page === "Overview"
                  ? "Explore matches, review incidents, and put research into practice."
                  : "A local, transparent workspace for football research."}
              </p>
            </div>
            <span className="version">RESEARCH EDITION / 01</span>
          </div>
          {error && (
            <div role="alert" className="error">
              {error} <button onClick={() => setRetry(retry + 1)}>Retry</button>
            </div>
          )}
          {(page === "Overview" || page === "Match Explorer") && (
            <>
              {page === "Overview" && (
                <>
                  <div className="stats">
                    <article>
                      <label>Matching records</label>
                      <strong>
                        {loading
                          ? "…"
                          : total.toString().padStart(2, "0")}
                      </strong>
                      <small>
                        {mode === "demo"
                          ? "Fictional engineering fixtures"
                          : "Provider match metadata"}
                      </small>
                    </article>
                    <article>
                      <label>Competitions</label>
                      <strong>
                        {competitions.length.toString().padStart(2, "0")}
                      </strong>
                      <small>Premier League · Champions League</small>
                    </article>
                    <article>
                      <label>Model availability</label>
                    <strong className="small-value">{modelStatus}</strong>
                      <small>No predictions without a trained model</small>
                    </article>
                  </div>
                  <div className="feature">
                    <div>
                      <p className="eyebrow">THE REVIEW WORKBENCH</p>
                      <h2>Every angle matters.</h2>
                      <p>
                        Bring your authorized clips together.
                        <br />
                        Inspect the evidence. Record your decision.
                      </p>
                      <button
                        className="primary"
                        onClick={() => setPage("Incident Review")}
                      >
                        Open incident review ↗
                      </button>
                    </div>
                    <div className="pitch-art">
                      <div className="circle" />
                      <span className="player one" />
                      <span className="player two" />
                      <span className="player three" />
                      <div className="scanline" />
                      <small>MULTI-VIEW RESEARCH</small>
                    </div>
                  </div>
                </>
              )}
              <div className="section-title">
                <h2>
                  {page === "Overview" ? "Match notebook" : "Explore matches"}
                </h2>
                <span>
                  {mode === "demo"
                    ? "FICTIONAL FIXTURES · NOT REAL RESULTS"
                    : "FOOTBALL-DATA.ORG"}
                </span>
              </div>
              <div className="filters">
                <select
                  aria-label="Competition"
                  value={competition}
                  onChange={(e) => {
                    setCompetition(e.target.value);
                    setOffset(0);
                  }}
                >
                  <option value="">All competitions</option>
                  {competitions.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
                <select
                  aria-label="Match status"
                  value={status}
                  onChange={(e) => {
                    setStatus(e.target.value);
                    setOffset(0);
                  }}
                >
                  <option value="">All statuses</option>
                  <option>FINISHED</option>
                  <option>SCHEDULED</option>
                  <option>TIMED</option>
                  <option>IN_PLAY</option>
                  <option>PAUSED</option>
                  <option>POSTPONED</option>
                  <option>SUSPENDED</option>
                  <option>CANCELLED</option>
                  <option>AWARDED</option>
                </select>
              </div>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>COMPETITION / DATE</th>
                      <th>FIXTURE</th>
                      <th>SCORE</th>
                      <th>STATUS</th>
                      <th>SOURCE</th>
                    </tr>
                  </thead>
                  <tbody>
                    {!loading && !error &&
                      rows.map((m) => (
                        <tr key={m.id}>
                          <td>
                            <b>
                              {m.competition_id.endsWith("PL")
                                ? "Premier League"
                                : "Champions League"}
                            </b>
                            <small>
                              {new Date(m.kickoff).toLocaleDateString()}
                            </small>
                          </td>
                          <td className="fixture">
                            {m.home}
                            <span>vs</span>
                            {m.away}
                          </td>
                          <td className="score">{score(m)}</td>
                          <td>
                            <span className="status">
                              {m.status.toLowerCase()}
                            </span>
                          </td>
                          <td>
                            <small className="source">{m.provenance}</small>
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
                {loading && (
                  <p className="empty">Loading local match records…</p>
                )}
                {!loading && !error && !rows.length && (
                  <p className="empty">No matches for these filters.</p>
                )}
              </div>
              <div className="filters" aria-label="Match pagination">
                <button
                  disabled={loading || !!error || offset === 0}
                  onClick={() => setOffset(Math.max(0, offset - pageSize))}
                >Previous</button>
                <span role="status">
                  {loading ? "Loading matches…" : error ? "Matches unavailable" :
                    `${total ? offset + 1 : 0}–${Math.min(offset + rows.length, total)} of ${total} matches`}
                </span>
                <button
                  disabled={loading || !!error || offset + pageSize >= total}
                  onClick={() => setOffset(offset + pageSize)}
                >Next</button>
              </div>
            </>
          )}
          {page === "Incident Review" && <Incidents />}
          {page === "Model Lab" && <ModelLab />}
          {page === "Offside Lab" && <Offside />}
          {page === "System / About" && <System />}
          {!pages.includes(page) && (
            <div className="empty panel">
              <h2>{page}</h2>
              <p>
                {page === "Model Lab"
                  ? "MODEL UNAVAILABLE — No trained model is registered."
                  : page === "System / About"
                    ? "PitchSight is an unofficial research decision-support tool. Match metadata does not contain labeled incident video."
                    : "This workspace is being implemented."}
              </p>
            </div>
          )}
          <footer>
            PitchSight / Research, with perspective.
            <span>Decision support. Human responsibility.</span>
          </footer>
        </section>
      </main>
    </div>
  );
}
