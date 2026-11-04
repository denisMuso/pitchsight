import { useEffect, useState } from "react";
import { api } from "./api";
type Incident = { id: string; title: string };
type Detail = {
  incident: Incident;
  views: {
    id: string;
    view_name: string;
    url: string;
    thumbnail: string;
    metadata: { duration: number; samples: number };
  }[];
  jobs: {
    id: string;
    state: string;
    kind: string;
    progress: number;
    error: string | null;
  }[];
  reviews: {
    id: number;
    decision: string;
    comments: string;
    created_at: string;
  }[];
  predictions: {
    id: number;
    model_version: string;
    result: Record<string, unknown>;
  }[];
};
export default function Incidents() {
  const [modelStatus, setModelStatus] = useState("Checking model registry…");
  const [items, setItems] = useState<Incident[]>([]),
    [selected, setSelected] = useState(""),
    [detail, setDetail] = useState<Detail | null>(null),
    [title, setTitle] = useState(""),
    [view, setView] = useState("Main camera"),
    [file, setFile] = useState<File | null>(null),
    [authorized, setAuthorized] = useState(false),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [decision, setDecision] = useState("INCONCLUSIVE"),
    [comments, setComments] = useState(""),
    [notice, setNotice] = useState("");
  async function refresh() {
    setItems((await api<{ items: Incident[] }>("/api/incidents")).items);
  }
  useEffect(() => {
    refresh().catch((e) => setError(e.message));
    api<{status:string}>("/api/models").then(m=>setModelStatus(m.status)).catch(e=>setError(e.message));
  }, []);
  useEffect(() => {
    if (!selected) return;
    let active = true;
    setDetail(null);
    const load = () =>
      api<Detail>(`/api/incidents/${selected}`)
        .then((d) => {
          if (active) setDetail(d);
        })
        .catch((e) => {
          if (active) setError(e.message);
        });
    load();
    const timer = setInterval(load, 1500);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [selected]);
  async function action(fn: () => Promise<void>) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await fn();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <div className="panel">
        <p className="eyebrow">AUTHORIZED FOOTAGE ONLY</p>
        <h2>Your evidence, organized.</h2>
        <p className="muted">
          Create an incident, attach camera views, and record an independent
          human review. Uploads are limited to 100 MiB, 120 seconds, and 4K.
          Model output is research evidence, not an officiating verdict.
        </p>
        <form
          className="row"
          onSubmit={(e) => {
            e.preventDefault();
            action(async () => {
              const item = await api<Incident>("/api/incidents", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ title }),
              });
              await refresh();
              setSelected(item.id);
              setTitle("");
            });
          }}
        >
          <input
            aria-label="Incident title"
            required
            maxLength={120}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Name a new incident"
          />
          <button className="primary" disabled={busy}>
            Create incident
          </button>
        </form>
      </div>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {notice && <p role="status">{notice}</p>}
      <div className="grid-two">
        <section className="panel stack">
          <label>
            Incident
            <select
              aria-label="Select incident"
              value={selected}
              onChange={(e) => setSelected(e.target.value)}
            >
              <option value="">Select an incident</option>
              {items.map((i) => (
                <option key={i.id} value={i.id}>
                  {i.title}
                </option>
              ))}
            </select>
          </label>
          {!items.length && (
            <p className="muted">
              No incidents yet. Create one to start reviewing.
            </p>
          )}
          {selected && (
            <>
              <h2>Add a camera view</h2>
              <form
                className="stack"
                onSubmit={(e) => {
                  e.preventDefault();
                  action(async () => {
                    if (!file) throw new Error("Choose a video");
                    const data = new FormData();
                    data.append("file", file);
                    data.append("view_name", view);
                    data.append("authorized", String(authorized));
                    await api(`/api/incidents/${selected}/videos`, {
                      method: "POST",
                      body: data,
                    });
                    setNotice(
                      "Video accepted. Playback preparation is queued.",
                    );
                  });
                }}
              >
                <input
                  aria-label="Camera view name"
                  required
                  maxLength={80}
                  value={view}
                  onChange={(e) => setView(e.target.value)}
                />
                <input
                  aria-label="Video file"
                  type="file"
                  required
                  accept=".mp4,.mov,.avi,.webm"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                />
                <label className="muted">
                  <input
                    type="checkbox"
                    required
                    checked={authorized}
                    onChange={(e) => setAuthorized(e.target.checked)}
                  />{" "}
                  I am authorized to process this clip locally.
                </label>
                <button className="primary" disabled={busy}>
                  {busy ? "Validating clip…" : "Upload view"}
                </button>
              </form>
              <h2>Processing</h2>
              {detail?.jobs.map((j) => (
                <div key={j.id}>
                  <p className="muted">
                    {j.kind} · {j.state} · {j.progress}%
                  </p>
                  <progress value={j.progress} max={100} />
                  {j.error && <p className="error">{j.error}</p>}
                </div>
              ))}
              {!detail?.jobs.length && (
                <p className="muted">No processing jobs.</p>
              )}
              <button
                className="secondary"
                disabled={busy}
                onClick={() =>
                  action(async () => {
                    await api(`/api/incidents/${selected}/analyze`, {
                      method: "POST",
                    });
                    setNotice("Analysis queued.");
                  })
                }
              >
                Analyze with registered model
              </button>
              <p className="muted">
                {detail?.predictions.length
                  ? "Recorded model output below."
                  : modelStatus === "AVAILABLE" ? "A registered research model is available for analysis." : `${modelStatus} — no predictions are simulated.`}
              </p>
            </>
          )}
        </section>
        <section className="stack">
          {detail?.views.map((v) => (
            <article className="panel" key={v.id}>
              <h2>{v.view_name}</h2>
              <video controls preload="none" poster={v.thumbnail} src={v.url} />
              <p className="muted">
                {v.metadata.duration.toFixed(2)} sec · {v.metadata.samples}{" "}
                sampled frames
              </p>
            </article>
          ))}
          {selected && (
            <article className="panel">
              <h2>Human review</h2>
              <form
                className="stack"
                onSubmit={(e) => {
                  e.preventDefault();
                  action(async () => {
                    await api(`/api/incidents/${selected}/reviews`, {
                      method: "POST",
                      headers: { "Content-Type": "application/json" },
                      body: JSON.stringify({ decision, comments }),
                    });
                    setComments("");
                    setNotice("Review saved with an audit timestamp.");
                  });
                }}
              >
                <select
                  aria-label="Review decision"
                  value={decision}
                  onChange={(e) => setDecision(e.target.value)}
                >
                  <option>INCONCLUSIVE</option>
                  <option>FOUL</option>
                  <option>NO FOUL</option>
                </select>
                <textarea
                  aria-label="Review comments"
                  placeholder="What does the evidence show?"
                  maxLength={4000}
                  value={comments}
                  onChange={(e) => setComments(e.target.value)}
                />
                <button className="primary" disabled={busy}>
                  Save human review
                </button>
              </form>
              {detail?.reviews.map((r) => (
                <div key={r.id}>
                  <p>{r.decision}</p>
                  <p className="muted">{r.comments}</p>
                  <small>{new Date(r.created_at).toLocaleString()}</small>
                </div>
              ))}
            </article>
          )}
          {detail?.predictions.map((p) => (
            <article className="panel" key={p.id}>
              <h2>Model {p.model_version}</h2>
              <pre>{JSON.stringify(p.result, null, 2)}</pre>
            </article>
          ))}
        </section>
      </div>
    </>
  );
}
