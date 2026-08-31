"use client";

import { useCallback, useEffect, useState } from "react";

import {
  createRun,
  type Experiment,
  getRun,
  listExperiments,
  listRuns,
  type Run,
  type RunDetail,
} from "@/lib/api";
import { useLab } from "../lab-context";

const ACTIVE = new Set(["pending", "scheduled", "running"]);

function StatusPill({ status }: { status: string }) {
  return <span className={`run-status run-${status}`}>{status}</span>;
}

function RunCard({ runId }: { runId: string }) {
  const [run, setRun] = useState<RunDetail | null>(null);

  const load = useCallback(() => getRun(runId).then(setRun).catch(() => {}), [runId]);
  useEffect(() => {
    load();
  }, [load]);
  useEffect(() => {
    if (run && ACTIVE.has(run.status)) {
      const t = setInterval(load, 5000);
      return () => clearInterval(t);
    }
  }, [run, load]);

  if (!run) return null;

  return (
    <div className="panel run-card">
      <div className="run-head">
        <div>
          <strong>Run #{run.iteration}</strong> <StatusPill status={run.status} />
        </div>
        <span className="muted">{new Date(run.created_at).toLocaleString()}</span>
      </div>

      {run.summary && <p>{run.summary}</p>}
      {run.error && <p className="error mono">{run.error}</p>}

      {run.agent_session_id && (
        <p className="mono conv-id">
          agent conversation:{" "}
          <code>{run.agent_session_id}</code>{" "}
          <button
            type="button"
            className="link-btn"
            onClick={() => navigator.clipboard?.writeText(run.agent_session_id ?? "")}
          >
            copy
          </button>
          <span className="muted"> — review with </span>
          <code>claude --resume {run.agent_session_id}</code>
        </p>
      )}

      <ol className="steps">
        {run.steps.map((s) => (
          <li key={s.id} className={`step step-${s.status}`}>
            <span className="step-name">{s.name ?? s.handler}</span>
            <StatusPill status={s.status} />
            {s.error && <span className="error mono"> {s.error}</span>}
            {s.output != null && (
              <pre className="step-out">{JSON.stringify(s.output, null, 2)}</pre>
            )}
          </li>
        ))}
      </ol>

      {run.benchmark_results.length > 0 && (
        <table className="lb">
          <thead>
            <tr>
              <th>Benchmark</th>
              <th className="num">Score</th>
              <th>Pass</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody>
            {run.benchmark_results.map((r) => (
              <tr key={r.id}>
                <td>{r.benchmark_id.slice(0, 8)}</td>
                <td className="num">{r.score ?? "—"}</td>
                <td>{r.passed == null ? "—" : r.passed ? "✓" : "✗"}</td>
                <td className="mono">{JSON.stringify(r.details)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default function ExperimentsTab() {
  const lab = useLab();
  const [experiment, setExperiment] = useState<Experiment | null>(null);
  const [runs, setRuns] = useState<Run[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [dispatching, setDispatching] = useState(false);

  const refreshRuns = useCallback((expId: string) => {
    listRuns(expId).then(setRuns).catch((e) => setError(e?.message));
  }, []);

  useEffect(() => {
    listExperiments(lab.id)
      .then((xs) => {
        const exp = xs[0] ?? null;
        setExperiment(exp);
        if (exp) refreshRuns(exp.id);
      })
      .catch((e) => setError(e?.message));
  }, [lab.id, refreshRuns]);

  async function dispatch() {
    if (!experiment) return;
    setDispatching(true);
    setError(null);
    try {
      await createRun(experiment.id);
      refreshRuns(experiment.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "failed to dispatch");
    } finally {
      setDispatching(false);
    }
  }

  if (error) return <p className="error">{error}</p>;
  if (!experiment)
    return <p className="muted">No experiment configured (set a workflow in the lab YAML).</p>;

  return (
    <div className="experiments">
      <section className="panel">
        <div className="lb-head">
          <h2>{experiment.name}</h2>
          <button type="button" onClick={dispatch} disabled={dispatching} className="ghost-btn">
            {dispatching ? "Dispatching…" : "Dispatch run"}
          </button>
        </div>
        {experiment.description && <p className="muted">{experiment.description}</p>}
        <ol className="mini-list">
          {experiment.workflow.steps?.map((s, i) => (
            <li key={i}>
              <strong>{i + 1}.</strong> {s.name ?? s.handler}{" "}
              <span className="muted">· {s.handler}</span>
            </li>
          ))}
        </ol>
        <p className="muted hint">
          A run is queued as <code>pending</code>. Execute it on a host with the
          agent CLI + repo checkout: <code>iterlab-runner --once</code>.
        </p>
      </section>

      {runs.length === 0 ? (
        <p className="muted">No runs yet.</p>
      ) : (
        runs.map((r) => <RunCard key={r.id} runId={r.id} />)
      )}
    </div>
  );
}
