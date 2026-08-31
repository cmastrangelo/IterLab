"use client";

import { useState } from "react";

import type { RunListItem } from "@/lib/api";

const W = 760;
const H = 260;
const PAD = { l: 44, r: 16, t: 16, b: 30 };

interface Point {
  key: string;
  label: string;
  score: number;
  at: number;
  run: RunListItem;
  iteration: number;
  labels: Record<string, string>;
}

function points(runs: RunListItem[]): Point[] {
  const out: Point[] = [];
  for (const run of runs) {
    for (const c of run.candidates) {
      if (typeof c.score !== "number") continue;
      out.push({
        key: c.id,
        label: c.extra?.name ?? `run ${run.iteration}.${c.iteration}`,
        score: c.score,
        at: new Date(run.created_at).getTime() + c.iteration,
        run,
        iteration: c.iteration,
        labels: c.labels ?? {},
      });
    }
  }
  return out.sort((a, b) => a.at - b.at);
}

export function RunChart({
  runs,
  fallbackAgent,
}: {
  runs: RunListItem[];
  fallbackAgent?: string;
}) {
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);
  const pts = points(runs);

  if (pts.length === 0) {
    return (
      <div className="panel">
        <h2>Progress</h2>
        <p className="muted">No scored candidates yet. Dispatch a run to see them here.</p>
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

  const ticks = Array.from({ length: 5 }, (_, k) => lo + (k / 4) * (hi - lo));
  const p = hoverIdx != null ? pts[hoverIdx] : null;

  // agent step for this candidate's run + iteration
  const step = p?.run.steps.find(
    (s) => s.iteration === p.iteration && s.handler.includes("new_solution"),
  );
  const stepOut = (step?.output ?? {}) as Record<string, unknown>;
  const agent = (stepOut.agent as string) ?? fallbackAgent ?? "—";
  const prompt = stepOut.prompt as string | undefined;
  const promptSlug = stepOut.prompt_slug as string | undefined;
  const promptVersion = stepOut.prompt_version as number | undefined;
  const resumed = stepOut.resumed as boolean | undefined;

  return (
    <div className="panel chart-panel">
      <div className="lb-head">
        <h2>Progress</h2>
        <span className="muted">score (ladder win %) per candidate</span>
      </div>

      <div className="chart-wrap">
        <svg viewBox={`0 0 ${W} ${H}`} className="run-chart" role="img">
          {ticks.map((t, k) => (
            <g key={k}>
              <line x1={PAD.l} x2={W - PAD.r} y1={py(t)} y2={py(t)} className="grid" />
              <text x={PAD.l - 8} y={py(t) + 4} className="axis" textAnchor="end">
                {t.toFixed(0)}
              </text>
            </g>
          ))}

          {pts.length > 1 && (
            <polyline
              className="series"
              points={pts.map((pt, i) => `${px(i)},${py(pt.score)}`).join(" ")}
            />
          )}

          {pts.map((pt, i) => (
            <g key={pt.key}>
              <circle
                cx={px(i)}
                cy={py(pt.score)}
                r={hoverIdx === i ? 6 : 4}
                className="dot"
                onMouseEnter={() => setHoverIdx(i)}
                onMouseLeave={() => setHoverIdx(null)}
              />
              <text x={px(i)} y={H - PAD.b + 16} className="axis" textAnchor="middle">
                {pt.label.replace(/^solution_|\.py$/g, "")}
              </text>
            </g>
          ))}
        </svg>

        {p && hoverIdx != null && (
          <div
            className="chart-tip"
            style={{
              left: `${(px(hoverIdx) / W) * 100}%`,
              top: `${(py(p.score) / H) * 100}%`,
            }}
          >
            <div className="tip-title">
              {p.label} · <strong>{p.score.toFixed(1)}%</strong>
            </div>
            {Object.keys(p.labels).length > 0 && (
              <div className="tip-labels">
                {Object.entries(p.labels).map(([k, v]) => (
                  <span key={k} className="chip chip-label">
                    {k}: {v}
                  </span>
                ))}
              </div>
            )}
            <dl>
              <div>
                <dt>run</dt>
                <dd>
                  #{p.run.iteration} · iter {p.iteration}
                  {resumed ? " · resumed convo" : p.iteration === 0 ? " · new convo" : ""}
                </dd>
              </div>
              <div>
                <dt>agent</dt>
                <dd>{agent}</dd>
              </div>
              <div>
                <dt>when</dt>
                <dd>{new Date(p.run.created_at).toLocaleString()}</dd>
              </div>
              {typeof (stepOut.cost_usd as number) === "number" && (
                <div>
                  <dt>cost</dt>
                  <dd>${(stepOut.cost_usd as number).toFixed(2)}</dd>
                </div>
              )}
              {p.run.agent_session_id && (
                <div>
                  <dt>convo</dt>
                  <dd className="mono">{p.run.agent_session_id}</dd>
                </div>
              )}
            </dl>
            {prompt && (
              <>
                <div className="tip-label">
                  prompt (iteration {p.iteration + 1})
                  {promptSlug != null && (
                    <span className="mono">
                      {" "}
                      · {promptSlug} v{promptVersion ?? 0}
                    </span>
                  )}
                </div>
                <pre className="tip-prompt">{prompt}</pre>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
