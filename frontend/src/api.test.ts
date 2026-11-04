import { expect, test, vi, afterEach } from "vitest";
import { api, score, Match } from "./api";
afterEach(() => vi.unstubAllGlobals());
test("missing scores are not fabricated", () => {
  expect(score({ home_score: null, away_score: null } as Match)).toBe("—");
  expect(score({ home_score: 0, away_score: 0 } as Match)).toBe("0 : 0");
});
test("API surfaces typed model unavailable errors", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue(
        new Response(
          JSON.stringify({ detail: { code: "MODEL UNAVAILABLE" } }),
          { status: 503 },
        ),
      ),
  );
  await expect(api("/api/incidents/example/analyze")).rejects.toThrow(
    "MODEL UNAVAILABLE",
  );
});
test("API preserves backend data", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({ items: [], total: 0 }))),
  );
  await expect(api("/api/matches")).resolves.toEqual({ items: [], total: 0 });
});
