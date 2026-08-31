"use client";

import { useState } from "react";

import type { RunListItem } from "@/lib/api";

const W = 760;
const H = 260;
const PAD = { l: 44, r: 16, t: 16, b: 30 };

function scored(runs: RunListItem[]): { run: RunListItem; score: number }[] {
  return runs
    .filter((r) => typeof r.candidate?.score === "number")
    .map((r) => ({ run: r, score: r.candidate!.score as number }))
    .sort(
      (a, b) =>
        new Date(a.run.created_at).getTime() - new Date(b.run.created_at).getTime(),
    );
}

function contextValue(ctx: Record<string, unknown>, key: string): unknown {
  for (const v of Object.values(ctx)) {
    if (v && typeof v === "object" && key in (v as Record<string, unknown>)) {
      return (v as Record<string, unknown>)[key];
    }
  }
  return undefined;
}

export function RunChart({
  runs,
  fallbackAgent,
}: {
  runs: RunListItem[];
  fallbackAgent?: string;
}) {
  const [hover, setHover] = useState<{ i: number; x: number; y: number } | null>(null);
  const pts = scored(runs);

  if (pts.length === 0) {
    return (
      <div className="panel">
        <h2>Progress</h2>
        <p className="muted">No scored runs yet. Dispatch one to see it here.</p>
      </div>
    );
  }

  const scores = pts.map((p) => p.score);
  const lo = Math.floor(Math.min(...scores) - 1);
  const hi = Math.ceil(Math.max(...scores) + 1);
  const px = (i: number) =>
    pts.length === 1
      ? (PAD.l + (W - PAD.r)) / 2
      : PAD.l + (i / (pts.length - 1)) * (W - PAD.l - PAD.r);
  const py = (s: number) => H - PAD.b - ((s - lo) / (hi - lo || 1)) * (H - PAD.t - PAD.b);

  const yTicks = 4;
  const ticks = Array.from({ length: yTicks + 1 }, (_, k) => lo + (k / yTicks) * (hi - lo));

  const hovered = hover ? pts[hover.i] : null;
  const hCtx = (hovered?.run.context ?? {}) as Record<string, unknown>;
  const hAgent =
    (contextValue(hCtx, "agent") as string) ?? fallbackAgent ?? "—";
  const hPrompt = contextValue(hCtx, "prompt") as string | undefined;
  const hSolution =
    (contextValue(hCtx, "solution") as string) ??
    (hovered?.run.candidate?.extra?.name as string) ??
    `run #${hovered?.run.iteration}`;

  return (
    <div className="panel chart-panel">
      <div className="lb-head">
        <h2>Progress</h2>
        <span className="muted">score (ladder win %) per run</span>
      </div>

      <div className="chart-wrap">
        <svg viewBox={`0 0 ${W} ${H}`} className="run-chart" role="img">
          {ticks.map((t, k) => (
            <g key={k}>
              <line
                x1={PAD.l}
                x2={W - PAD.r}
                y1={py(t)}
                y2={py(t)}
                className="grid"
              />
              <text x={PAD.l - 8} y={py(t) + 4} className="axis" textAnchor="end">
                {t.toFixed(0)}
              </text>
            </g>
          ))}

          {pts.length > 1 && (
            <polyline
              className="series"
              points={pts.map((p, i) => `${px(i)},${py(p.score)}`).join(" ")}
            />
          )}

          {pts.map((p, i) => (
            <g key={p.run.id}>
              <circle
                cx={px(i)}
                cy={py(p.score)}
                r={hover?.i === i ? 6 : 4}
                className="dot"
                onMouseEnter={() => setHover({ i, x: px(i), y: py(p.score) })}
                onMouseLeave={() => setHover(null)}
              />
              <text x={px(i)} y={H - PAD.b + 16} className="axis" textAnchor="middle">
                #{p.run.iteration}
              </text>
            </g>
          ))}
        </svg>

        {hovered && hover && (
          <div
            className="chart-tip"
            style={{
              left: `${(hover.x / W) * 100}%`,
              top: `${(hover.y / H) * 100}%`,
            }}
          >
            <div className="tip-title">
              {hSolution} · <strong>{hovered.score.toFixed(1)}%</strong>
            </div>
            <dl>
              <div>
                <dt>run</dt>
                <dd>
                  #{hovered.run.iteration} · {hovered.run.status}
                </dd>
              </div>
              <div>
                <dt>agent</dt>
                <dd>{hAgent}</dd>
              </div>
              <div>
                <dt>when</dt>
                <dd>{new Date(hovered.run.created_at).toLocaleString()}</dd>
              </div>
              {typeof hovered.run.candidate?.cost_usd === "number" && (
                <div>
                  <dt>cost</dt>
                  <dd>${hovered.run.candidate.cost_usd.toFixed(2)}</dd>
                </div>
              )}
              {hovered.run.agent_session_id && (
                <div>
                  <dt>convo</dt>
                  <dd className="mono">{hovered.run.agent_session_id}</dd>
                </div>
              )}
            </dl>
            {hPrompt && (
              <>
                <div className="tip-label">prompt</div>
                <pre className="tip-prompt">{hPrompt}</pre>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
