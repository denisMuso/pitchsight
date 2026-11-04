import { useEffect, useState } from "react";
import { api } from "./api";
type Result = {
  status: string;
  reference_x: number;
  second_last_x: number;
  margin_metres: number;
  margin_interval: number[];
  offence: string;
};
const initial = [
  { name: "Attacker", x: 77, y: 28, color: "#b8ed8a" },
  { name: "Ball", x: 65, y: 38, color: "#fff" },
  { name: "Opponent 1", x: 96, y: 34, color: "#e2b980" },
  { name: "Opponent 2", x: 74, y: 22, color: "#e2b980" },
  { name: "Opponent 3", x: 60, y: 48, color: "#e2b980" },
];
export default function Offside() {
  const [players, setPlayers] = useState(initial),
    [drag, setDrag] = useState<number | null>(null),
    [direction, setDirection] = useState(1),
    [uncertainty, setUncertainty] = useState(0.25),
    [result, setResult] = useState<Result | null>(null),
    [error, setError] = useState(""),
    [calibration, setCalibration] = useState(
      "0,0,0,0\n1000,0,105,0\n1000,600,105,68\n0,600,0,68",
    ),
    [calResult, setCalResult] = useState<Record<string, unknown> | null>(null);
  useEffect(() => {
    setResult(null);
    const controller = new AbortController();
    const timer = setTimeout(() => {
      api<Result>("/api/offside/position", {
        method: "POST",
        signal: controller.signal,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          attacker: players[0].x,
          ball: players[1].x,
          opponents: players.slice(2).map((p) => p.x),
          direction,
          uncertainty,
        }),
      })
        .then((r) => {
          setResult(r);
          setError("");
        })
        .catch((e) => {
          if (e.name !== "AbortError") setError(e.message);
        });
    }, 80);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [players, direction, uncertainty]);
  return (
    <>
      <div className="panel">
        <p className="eyebrow">SYNTHETIC POSITION LABORATORY</p>
        <h2>Explore the line. Keep the context.</h2>
        <p className="muted">
          Drag the attacker, ball, and opponents. Positions represent eligible
          body-part projections at the relevant teammate touch. This simplified
          2D model does not decide an offside offence.
        </p>
        <div className="row">
          <label>
            Attacking direction{" "}
            <select
              aria-label="Attacking direction"
              value={direction}
              onChange={(e) => setDirection(Number(e.target.value))}
            >
              <option value={1}>Left → right</option>
              <option value={-1}>Right → left</option>
            </select>
          </label>
          <label>
            Coordinate uncertainty ±{uncertainty.toFixed(2)} m{" "}
            <input
              aria-label="Coordinate uncertainty"
              type="range"
              min="0"
              max="3"
              step="0.05"
              value={uncertainty}
              onChange={(e) => setUncertainty(Number(e.target.value))}
            />
          </label>
          <button
            className="secondary"
            onClick={() => {
              setPlayers(initial);
              setDirection(1);
              setUncertainty(0.25);
            }}
          >
            Reset example
          </button>
        </div>
      </div>
      {error && <p className="error">{error}</p>}
      <div className="grid-two">
        <div className="panel">
          <svg
            className="pitch"
            aria-label="Interactive synthetic football pitch"
            viewBox="-4 -4 113 76"
            onPointerMove={(e) => {
              if (drag === null) return;
              const rect = e.currentTarget.getBoundingClientRect();
              const x = Math.max(
                0,
                Math.min(105, ((e.clientX - rect.left) / rect.width) * 113 - 4),
              );
              const y = Math.max(
                0,
                Math.min(68, ((e.clientY - rect.top) / rect.height) * 76 - 4),
              );
              setPlayers((p) =>
                p.map((v, i) => (i === drag ? { ...v, x, y } : v)),
              );
            }}
            onPointerUp={() => setDrag(null)}
            onPointerCancel={() => setDrag(null)}
          >
            <g fill="none" stroke="#57785c" strokeWidth=".35">
              <rect width="105" height="68" />
              <path d="M52.5 0V68 M0 14H16.5V54H0 M105 14H88.5V54H105" />
              <circle cx="52.5" cy="34" r="9.15" />
            </g>
            {result && (
              <>
                <rect
                  x={result.reference_x - 2 * uncertainty}
                  y="0"
                  width={4 * uncertainty}
                  height="68"
                  fill="#d8ad6c"
                  opacity=".13"
                />
                <line
                  x1={result.reference_x}
                  x2={result.reference_x}
                  y1="0"
                  y2="68"
                  stroke="#e4ba7c"
                  strokeWidth=".4"
                  strokeDasharray="2 1"
                />
              </>
            )}
            {players.map((p, i) => (
              <g
                key={p.name}
                style={{ cursor: "grab" }}
                onPointerDown={(e) => {
                  e.currentTarget.setPointerCapture(e.pointerId);
                  setDrag(i);
                }}
              >
                <circle
                  cx={p.x}
                  cy={p.y}
                  r={i === 1 ? 1 : 1.8}
                  fill={p.color}
                />
                <text
                  x={p.x}
                  y={p.y - 3}
                  textAnchor="middle"
                  fontSize="2.4"
                  fill={p.color}
                >
                  {p.name}
                </text>
              </g>
            ))}
          </svg>
          <p className="muted">
            105 × 68 m synthetic pitch · dashed line = position reference
          </p>
          {players.map((p, i) => (
            <label className="row muted" key={p.name}>
              {p.name} x
              <input
                aria-label={`${p.name} x coordinate`}
                type="number"
                min="0"
                max="105"
                step="0.1"
                value={p.x.toFixed(1)}
                onChange={(e) => {
                  const x = Number(e.target.value);
                  if (Number.isFinite(x) && x >= 0 && x <= 105)
                    setPlayers((ps) =>
                      ps.map((v, j) => (i === j ? { ...v, x } : v)),
                    );
                }}
              />
            </label>
          ))}
        </div>
        <div className="panel">
          <p className="eyebrow">POSITION RESULT</p>
          <h2 aria-live="polite">{result?.status || "Computing…"}</h2>
          {result && (
            <>
              <p>Margin: {result.margin_metres.toFixed(2)} m</p>
              <p className="muted">
                Bounded interval:{" "}
                {result.margin_interval.map((v) => v.toFixed(2)).join(" to ")} m
              </p>
              <p className="muted">
                Second-last opponent x: {result.second_last_x.toFixed(2)} m
              </p>
            </>
          )}
          <h2>Offence: not determined</h2>
          <p className="muted">
            Being in an offside position is not itself an offence. Active
            involvement, interference, deliberate play, saves, and restart
            exceptions need a human decision. Level players and players in their
            own half are not in an offside position.
          </p>
          <a
            href="https://www.theifab.com/laws/latest/offside/"
            target="_blank"
            rel="noreferrer"
          >
            Read IFAB Law 11 ↗
          </a>
          <p className="error">
            Camera calibration, body height and contact timing create
            uncertainty. This is not professional VAR measurement.
          </p>
        </div>
      </div>
      <div className="panel">
        <h2>Ground-plane calibration</h2>
        <p className="muted">
          One correspondence per line: image x, image y, pitch x, pitch y.
          Defaults are synthetic. At least four non-collinear points.
          Reprojection error on selected points does not establish
          broadcast-video precision.
        </p>
        <textarea
          aria-label="Calibration correspondences"
          value={calibration}
          onChange={(e) => setCalibration(e.target.value)}
        />
        <button
          className="primary"
          onClick={async () => {
            try {
              const rows = calibration
                .trim()
                .split("\n")
                .map((line) => line.split(",").map(Number));
              if (
                rows.some(
                  (r) => r.length !== 4 || r.some((v) => !Number.isFinite(v)),
                )
              )
                throw new Error("Each line needs four finite numbers");
              setCalResult(
                await api("/api/offside/calibrate", {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({
                    image_points: rows.map((r) => r.slice(0, 2)),
                    pitch_points: rows.map((r) => r.slice(2)),
                  }),
                }),
              );
              setError("");
            } catch (e) {
              setError((e as Error).message);
              setCalResult(null);
            }
          }}
        >
          Compute homography
        </button>
        {calResult && <pre>{JSON.stringify(calResult, null, 2)}</pre>}
      </div>
    </>
  );
}
