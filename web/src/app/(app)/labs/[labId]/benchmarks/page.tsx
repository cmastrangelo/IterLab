"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";

import {
  type Benchmark,
  getBenchmarkHealth,
  getLeaderboard,
  type Leaderboard,
  type LeaderboardColumn,
} from "@/lib/api";
import { useLab } from "../lab-context";

function fmt(value: unknown, kind: LeaderboardColumn["kind"]): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "boolean") return value ? "yes" : "no";
  if (typeof value === "number") {
    if (kind === "percent") return `${value.toFixed(1)}%`;
    if (kind === "integer") return String(value);
    return value.toFixed(1);
  }
  return String(value);
}

function LeaderboardTable({ benchmark }: { benchmark: Benchmark }) {
  const [board, setBoard] = useState<Leaderboard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    setError(null);
    setBoard(null);
    getLeaderboard(benchmark.id)
      .then(setBoard)
      .catch(async (e) => {
        // surface why the adapter is unavailable
        try {
          const h = await getBenchmarkHealth(benchmark.id);
          setError(h.ok ? (e?.message ?? "failed") : h.detail);
        } catch {
          setError(e?.message ?? "failed to load leaderboard");
        }
      })
      .finally(() => setLoading(false));
  }, [benchmark.id]);

  if (loading) return <p className="muted">Loading leaderboard…</p>;
  if (error)
    return (
      <div className="panel">
        <p className="error">Leaderboard unavailable</p>
        <p className="muted mono">{error}</p>
      </div>
    );
  if (!board) return null;

  return (
    <div className="panel">
      <div className="lb-head">
        <h2>{board.title}</h2>
        <span className="muted">
          {board.rows.length} entrants
          {board.updated_at
            ? ` · updated ${new Date(board.updated_at).toLocaleString()}`
            : ""}
        </span>
      </div>
      {board.note && <p className="muted">{board.note}</p>}
      <div className="table-wrap">
        <table className="lb">
          <thead>
            <tr>
              <th className="num">#</th>
              <th>Entrant</th>
              {board.columns.map((c) => (
                <th key={c.key} className={`num${c.primary ? " primary" : ""}`}>
                  {c.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {board.rows.map((row) => (
              <tr
                key={row.entrant}
                className={row.is_baseline ? "is-baseline" : row.is_candidate ? "is-candidate" : ""}
              >
                <td className="num">{row.rank}</td>
                <td>
                  {row.entrant}
                  {row.is_baseline && <span className="pill">baseline</span>}
                </td>
                {board.columns.map((c) => (
                  <td key={c.key} className={`num${c.primary ? " primary" : ""}`}>
                    {fmt(row.values[c.key], c.kind)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function BenchmarksInner() {
  const lab = useLab();
  const params = useSearchParams();
  const selectedSlug = params.get("b") ?? lab.benchmarks[0]?.slug;
  const selected = useMemo(
    () => lab.benchmarks.find((b) => b.slug === selectedSlug) ?? lab.benchmarks[0],
    [lab.benchmarks, selectedSlug],
  );

  if (lab.benchmarks.length === 0) {
    return <p className="muted">No benchmarks configured for this lab.</p>;
  }

  return (
    <div className="benchmarks">
      <div className="pill-row">
        {lab.benchmarks.map((b) => (
          <Link
            key={b.id}
            href={`/labs/${lab.id}/benchmarks?b=${b.slug}`}
            className={`pill-tab${b.slug === selected?.slug ? " is-active" : ""}`}
          >
            {b.name}
          </Link>
        ))}
      </div>

      {selected && (
        <>
          {selected.description && <p className="muted">{selected.description}</p>}
          <LeaderboardTable benchmark={selected} />
        </>
      )}
    </div>
  );
}

export default function BenchmarksTab() {
  return (
    <Suspense fallback={<p className="muted">Loading…</p>}>
      <BenchmarksInner />
    </Suspense>
  );
}
