import { useEffect, useState } from "react";
import { api } from "./api";
type Run = {
  provenance: string;
  model_version: string;
  run_id: string;
  temporal: {
    report?: Record<
      string,
      { precision: number; recall: number; "f1-score": number; support: number }
    >;
    confusion_matrix?: number[][];
    class_distribution?: number[];
    reliability?: { ece: number };
    temperature?: number;
    accuracy: number;
    device: string;
    history: { epoch: number; train_loss: number; validation_loss: number }[];
    classifier_ms_per_incident: number;
    peak_cuda_mib: number | null;
  };
  baseline: { accuracy: number };
};
export default function ModelLab() {
  const [progress, setProgress] = useState<
    {
      model_version: string;
      stage: string;
      updated_at: string;
      split?: string;
      completed?: number;
      total?: number;
      epoch?: number;
      max_epochs?: number;
    }[]
  >([]);
  const [preflight, setPreflight] = useState<{
    status: string;
    checked_at?: string;
    checks: { name: string; status: string; detail: string }[];
    effective_batch_size?: number;
    dataset?: {
      excluded_incidents: number;
      fingerprint: string;
      splits: Record<
        string,
        {
          incidents: number;
          class_counts: Record<string, number>;
          truncated_incidents: number;
        }
      >;
    } | null;
  } | null>(null);
  const [runs, setRuns] = useState<Run[]>([]),
    [status, setStatus] = useState("Loading model registry…"),
    [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    const load = () =>
      Promise.all([
        api<{ items: Run[] }>("/api/experiments"),
        api<{ status: string }>("/api/models"),
        api<{ items: typeof progress }>("/api/training/progress"),
      ])
        .then(([r, m, p]) => {
          if (!active) return;
          setRuns(r.items);
          setStatus(m.status);
          setProgress(p.items);
        })
        .catch((e) => {
          if (active) setError(e.message);
        });
    load();
    const timer = setInterval(load, 10000);
    api<NonNullable<typeof preflight>>("/api/training/preflight")
      .then(setPreflight)
      .catch((e) => setError(e.message));
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, []);
  return (
    <>
      <div className="panel">
        <p className="eyebrow">EXPERIMENTS & MODEL PROVENANCE</p>
        <h2>{status}</h2>
        <p className="muted">
          Frozen MobileNetV3 → temporal GRU → masked multi-view fusion. Models
          become available only after authorized labeled training and explicit
          local registration. Raw confidence is not calibrated probability.
        </p>
      </div>
      {error && <p className="error">{error}</p>}
      {progress.map((p) => (
        <section className="panel" key={p.model_version}>
          <h2>
            {p.model_version} · {p.stage}
          </h2>
          {p.total !== undefined && (
            <>
              <progress value={p.completed} max={p.total} />
              <p>
                {p.split}: {p.completed} / {p.total} incidents
              </p>
            </>
          )}
          {p.epoch !== undefined && (
            <p>
              Epoch {p.epoch} / {p.max_epochs}
            </p>
          )}
          <p className="muted">
            Last update {new Date(p.updated_at).toLocaleString()}. Progress is
            saved by the training process; an old timestamp may indicate
            interruption.
          </p>
        </section>
      ))}
      <section className="panel">
        <h2>Training preflight: {preflight?.status || "checking"}</h2>
        <p className="muted">
          Saved check, not a live resource reservation. Run python -m
          pitchsight.training.preflight --dataset PATH before training.
        </p>
        {preflight?.checked_at && (
          <p>
            Checked {new Date(preflight.checked_at).toLocaleString()} ·
            Effective batch {preflight.effective_batch_size}
          </p>
        )}
        {preflight?.checks.map((c) => (
          <p key={c.name}>
            <b>
              {c.name} · {c.status}
            </b>
            <br />
            {c.detail}
          </p>
        ))}
        {preflight?.dataset && (
          <details>
            <summary>Dataset class coverage and selected views</summary>
            <p>
              Excluded unknown-label incidents:{" "}
              {preflight.dataset.excluded_incidents}
            </p>
            {Object.entries(preflight.dataset.splits).map(([split, data]) => (
              <div key={split}>
                <h3>
                  {split}: {data.incidents} incidents
                </h3>
                <p>
                  {data.truncated_incidents} incidents have more views than the
                  configuration uses.
                </p>
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>CLASS</th>
                        <th>INCIDENTS</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(data.class_counts).map(
                        ([name, count]) => (
                          <tr key={name}>
                            <td>{name}</td>
                            <td>{count}</td>
                          </tr>
                        ),
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            ))}
            <p className="muted">
              Dataset fingerprint: <code>{preflight.dataset.fingerprint}</code>
            </p>
          </details>
        )}
      </section>
      {!runs.length && (
        <p className="empty">
          No recorded experiments. Run a local smoke test or train with
          authorized data.
        </p>
      )}
      {runs.map((r) => (
        <article className="panel" key={r.run_id}>
          <div className="section-title">
            <h2>{r.model_version}</h2>
            <span>{r.provenance}</span>
          </div>
          {r.provenance === "SYNTHETIC SMOKE TEST" && (
            <p className="error">
              Engineering fixture only. These scores do not measure football
              foul recognition.
            </p>
          )}
          <div className="stats">
            <article>
              <label>Fixture / test accuracy</label>
              <strong>{(r.temporal.accuracy * 100).toFixed(1)}%</strong>
              <small>{r.provenance}</small>
            </article>
            <article>
              <label>Logistic baseline</label>
              <strong>{(r.baseline.accuracy * 100).toFixed(1)}%</strong>
              <small>Same held-out fixture split</small>
            </article>
            <article>
              <label>Classifier latency</label>
              <strong>
                {r.temporal.classifier_ms_per_incident.toFixed(2)}
                <small>ms / incident</small>
              </strong>
              <small>{r.temporal.device} · excludes video/encoder work</small>
            </article>
          </div>
          <h2>Recorded learning curve</h2>
          <table>
            <thead>
              <tr>
                <th>EPOCH</th>
                <th>TRAIN LOSS</th>
                <th>VALIDATION LOSS</th>
              </tr>
            </thead>
            <tbody>
              {r.temporal.history.map((h) => (
                <tr key={h.epoch}>
                  <td>{h.epoch + 1}</td>
                  <td>{h.train_loss.toFixed(4)}</td>
                  <td>{h.validation_loss.toFixed(4)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {r.temporal.report && (
            <>
              <h2>Per-class test performance</h2>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>CLASS</th>
                      <th>PRECISION</th>
                      <th>RECALL</th>
                      <th>F1</th>
                      <th>SUPPORT</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(r.temporal.report)
                      .filter(
                        ([name, value]) =>
                          typeof value === "object" &&
                          !["macro avg", "weighted avg", "micro avg"].includes(
                            name,
                          ),
                      )
                      .map(([name, value]) => (
                        <tr key={name}>
                          <td>{name}</td>
                          <td>{value.precision.toFixed(3)}</td>
                          <td>{value.recall.toFixed(3)}</td>
                          <td>{value["f1-score"].toFixed(3)}</td>
                          <td>{value.support}</td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
              <p>
                Macro F1:{" "}
                {r.temporal.report["macro avg"]?.["f1-score"].toFixed(3)}
              </p>
            </>
          )}
          {r.temporal.confusion_matrix && (
            <details>
              <summary>
                Confusion matrix (rows: actual; columns: predicted)
              </summary>
              <p className="muted">
                Class order matches the per-class table above.
              </p>
              <div className="table-wrap">
                <table>
                  <tbody>
                    {r.temporal.confusion_matrix.map((row, i) => (
                      <tr key={i}>
                        <th>Class {i + 1}</th>
                        {row.map((count, j) => (
                          <td key={j}>{count}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </details>
          )}
          {r.temporal.reliability && (
            <p>
              Validation ECE: {r.temporal.reliability.ece.toFixed(4)} ·
              Temperature: {r.temporal.temperature?.toFixed(3)}. Calibration
              uses validation data only; this is not evidence of real-world
              calibration.
            </p>
          )}
          <p className="muted">MLflow run: {r.run_id}</p>
        </article>
      ))}
    </>
  );
}
