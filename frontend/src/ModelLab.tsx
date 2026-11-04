import { useEffect, useState } from "react";
import { api } from "./api";
type Run = {
  provenance: string;
  model_version: string;
  run_id: string;
  temporal: {
    accuracy: number;
    device: string;
    history: { epoch: number; train_loss: number; validation_loss: number }[];
    classifier_ms_per_incident: number;
    peak_cuda_mib: number | null;
  };
  baseline: { accuracy: number };
};
export default function ModelLab() {
  const [runs, setRuns] = useState<Run[]>([]),
    [status, setStatus] = useState("Loading model registry…"),
    [error, setError] = useState("");
  useEffect(() => {
    Promise.all([
      api<{ items: Run[] }>("/api/experiments"),
      api<{ status: string }>("/api/models"),
    ])
      .then(([r, m]) => {
        setRuns(r.items);
        setStatus(m.status);
      })
      .catch((e) => setError(e.message));
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
          <p className="muted">MLflow run: {r.run_id}</p>
        </article>
      ))}
    </>
  );
}
