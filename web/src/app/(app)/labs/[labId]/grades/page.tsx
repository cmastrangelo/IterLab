"use client";

import { useEffect, useState } from "react";

import { type AgentGrade, getLabGrades, type LabGrades, type PromptGrade } from "@/lib/api";
import { useLab } from "../lab-context";

function delta(v: number | null): string {
  if (v === null) return "—";
  const sign = v > 0 ? "+" : "";
  return `${sign}${v.toFixed(1)}`;
}

function deltaClass(v: number | null): string {
  if (v === null) return "muted";
  return v > 0 ? "delta-pos" : v < 0 ? "delta-neg" : "muted";
}

function pct(v: number): string {
  return `${Math.round(v * 100)}%`;
}

function AgentsTable({ rows }: { rows: AgentGrade[] }) {
  if (rows.length === 0) return <p className="muted">No graded runs yet.</p>;
  return (
    <div className="table-wrap">
      <table className="lb">
        <thead>
          <tr>
            <th>Agent</th>
            <th className="num">Runs</th>
            <th className="num">Candidates</th>
            <th className="num primary">Avg Δ vs frontier</th>
            <th className="num">Best Δ</th>
            <th className="num">New-best rate</th>
            <th className="num">Avg score</th>
            <th className="num">Avg cost</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((a) => (
            <tr key={a.agent}>
              <td>{a.agent}</td>
              <td className="num">{a.runs}</td>
              <td className="num">{a.candidates}</td>
              <td className={`num primary ${deltaClass(a.avg_delta)}`}>{delta(a.avg_delta)}</td>
              <td className={`num ${deltaClass(a.best_delta)}`}>{delta(a.best_delta)}</td>
              <td className="num">{pct(a.new_best_rate)}</td>
              <td className="num">{a.avg_score.toFixed(1)}</td>
              <td className="num">
                {a.avg_cost_usd != null ? `$${a.avg_cost_usd.toFixed(2)}` : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PromptsTable({ rows }: { rows: PromptGrade[] }) {
  if (rows.length === 0) return <p className="muted">No graded prompt versions yet.</p>;
  const groups = new Map<string, PromptGrade[]>();
  for (const p of rows) {
    const arr = groups.get(p.slug) ?? [];
    arr.push(p);
    groups.set(p.slug, arr);
  }
  return (
    <>
      {[...groups.entries()].map(([slug, versions]) => (
        <div key={slug} className="table-wrap grade-group">
          <h3>
            <code>{slug}</code>
          </h3>
          <table className="lb">
            <thead>
              <tr>
                <th className="num">v</th>
                <th>Basis</th>
                <th className="num">Uses</th>
                <th className="num primary">Avg Δ / lift</th>
                <th className="num">Best Δ</th>
                <th className="num">New-best rate</th>
                <th className="num">Avg score</th>
                <th className="num">Avg cost</th>
              </tr>
            </thead>
            <tbody>
              {versions.map((p) => (
                <tr key={p.prompt_id}>
                  <td className="num">
                    <strong>{p.version}</strong>
                  </td>
                  <td className="muted">{p.basis}</td>
                  <td className="num">{p.uses}</td>
                  <td className={`num primary ${deltaClass(p.avg_delta)}`}>
                    {delta(p.avg_delta)}
                  </td>
                  <td className={`num ${deltaClass(p.best_delta)}`}>{delta(p.best_delta)}</td>
                  <td className="num">{pct(p.new_best_rate)}</td>
                  <td className="num">{p.avg_score.toFixed(1)}</td>
                  <td className="num">
                    {p.avg_cost_usd != null ? `$${p.avg_cost_usd.toFixed(2)}` : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </>
  );
}

export default function GradesTab() {
  const lab = useLab();
  const [grades, setGrades] = useState<LabGrades | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setGrades(null);
    setError(null);
    getLabGrades(lab.id)
      .then(setGrades)
      .catch((e) => setError(e?.message ?? "failed to load grades"));
  }, [lab.id]);

  if (error) return <p className="error">{error}</p>;
  if (!grades) return <p className="muted">Loading grades…</p>;

  return (
    <div className="grades">
      <p className="muted hint">
        Not a benchmark of solutions — a ranking of the <em>choices behind them</em>.
        Each run is graded against the frontier that existed when it started
        (<code>best score it produced − best score that already existed</code>).
        A prompt used at iteration 0 is graded the same way; a prompt used to
        iterate is graded on how much it lifted its own run&rsquo;s first attempt.{" "}
        {grades.note}
      </p>

      <section className="panel">
        <h2>Agents</h2>
        <AgentsTable rows={grades.agents} />
      </section>

      <section className="panel">
        <h2>Prompts</h2>
        <PromptsTable rows={grades.prompts} />
      </section>
    </div>
  );
}
