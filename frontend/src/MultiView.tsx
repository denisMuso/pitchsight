import { useRef, useState } from "react";

type View = {
  id: string;
  view_name: string;
  url: string;
  thumbnail: string;
  metadata: { duration: number; samples: number };
};

export default function MultiView({ views }: { views: View[] }) {
  const videos = useRef<Record<string, HTMLVideoElement | null>>({});
  const [offsets, setOffsets] = useState<Record<string, number>>({});
  const [time, setTime] = useState(0);
  const [error, setError] = useState("");
  const duration = Math.max(
    0,
    ...views.map((v) => v.metadata.duration - (offsets[v.id] || 0)),
  );
  function seek(value: number) {
    setTime(value);
    for (const v of views) {
      const video = videos.current[v.id];
      if (video && video.readyState >= 1) {
        video.currentTime = Math.max(
          0,
          Math.min(v.metadata.duration, value + (offsets[v.id] || 0)),
        );
      }
    }
  }
  async function play() {
    setError("");
    seek(time);
    const results = await Promise.allSettled(
      views.map((v) => videos.current[v.id]?.play()),
    );
    if (results.some((r) => r.status === "rejected")) {
      Object.values(videos.current).forEach((v) => v?.pause());
      setError(
        "Playback could not start for every view. Check conversion status and keep this tab visible.",
      );
    }
  }
  return (
    <>
      {views.length > 0 && (
        <div className="panel">
          <h2>Multi-view timeline</h2>
          <p className="muted">
            Align the same event using each view's clip-time offset. Shared
            playback is approximate; slow-motion replays may run at different
            speeds.
          </p>
          <div className="row">
            <button onClick={play}>Play all views</button>
            <button
              onClick={() =>
                Object.values(videos.current).forEach((v) => v?.pause())
              }
            >
              Pause all views
            </button>
            <button onClick={() => seek(0)}>Reset timeline</button>
          </div>
          <label>
            Shared seek: {time.toFixed(2)} seconds
            <input
              aria-label="Shared video timeline"
              type="range"
              min={0}
              max={duration}
              step={0.04}
              value={time}
              onChange={(e) => seek(Number(e.target.value))}
            />
          </label>
          {error && (
            <p role="alert" className="error">
              {error}
            </p>
          )}
        </div>
      )}
      {views.map((v, index) => (
        <article className="panel" key={v.id}>
          <h2>{v.view_name}</h2>
          <video
            ref={(el) => {
              videos.current[v.id] = el;
            }}
            controls
            muted
            preload="metadata"
            poster={v.thumbnail}
            src={v.url}
            onTimeUpdate={(e) => {
              if (index === 0)
                setTime(
                  Math.max(
                    0,
                    e.currentTarget.currentTime - (offsets[v.id] || 0),
                  ),
                );
            }}
          />
          <label>
            Clip-time offset (seconds)
            <input
              aria-label={`Offset for ${v.view_name}`}
              type="number"
              min={0}
              max={v.metadata.duration}
              step={0.04}
              value={offsets[v.id] || 0}
              onChange={(e) =>
                setOffsets({
                  ...offsets,
                  [v.id]: Math.max(
                    0,
                    Math.min(v.metadata.duration, Number(e.target.value)),
                  ),
                })
              }
            />
          </label>
          <p className="muted">
            {v.metadata.duration.toFixed(2)} sec · {v.metadata.samples} sampled
            frames. Alignment is local to this review session.
          </p>
        </article>
      ))}
    </>
  );
}
