"use client";

import { Fragment, useCallback, useEffect, useState } from "react";

import {
  createRun,
  type Experiment,
  getRun,
  listExperiments,
  listRuns,
  retryRun,
  type RunDetail,
  type RunListItem,
} from "@/lib/api";
import { useLab } from "../lab-context";
import { RunChart } from "./run-chart";

const ACTIVE = new Set(["pending", "scheduled", "running"]);

function StatusPill({ status }: { status: string }) {
  return <span className={`run-status run-${status}`}>{status}</span>;
}

function RunDetailBlock({ runId }: { runId: string }) {
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
    <div className="run-detail">
      {run.error && (
        <p className="error mono">
          {run.error}{" "}
          <button
            type="button"
            className="link-btn"
            onClick={() => retryRun(run.id).then(load)}
          >
            retry
          </button>
        </p>
      )}
      {run.agent_session_id && (
        <p className="mono conv-id">
          <code>claude --resume {run.agent_session_id}</code>{" "}
          <button
            type="button"
            className="link-btn"
            onClick={() => navigator.clipboard?.writeText(run.agent_session_id ?? "")}
          >
            copy
          </button>
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
    </div>
  );
}

export default function ExperimentsTab() {
  const lab = useLab();
  const [experiment, setExperiment] = useState<Experiment | null>(null);
  const [runs, setRuns] = useState<RunListItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [dispatching, setDispatching] = useState(false);
  const [open, setOpen] = useState<string | null>(null);

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

  // poll while any run is active
  useEffect(() => {
    if (!experiment) return;
    if (!runs.some((r) => ACTIVE.has(r.status))) return;
    const t = setInterval(() => refreshRuns(experiment.id), 5000);
    return () => clearInterval(t);
  }, [experiment, runs, refreshRuns]);

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

  const agentStep = experiment.workflow.steps?.find(
    (s) => (s.config as Record<string, unknown>)?.agent,
  );
  const fallbackAgent = (agentStep?.config as Record<string, string>)?.agent;

  return (
    <div className="experiments">
      <RunChart runs={runs} fallbackAgent={fallbackAgent} />

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
          A run is queued <code>pending</code>. Execute it on a host with the agent
          CLI + repo checkout: <code>iterlab-runner --once</code>.
        </p>
      </section>

      <section className="panel">
        <h2>Runs</h2>
        {runs.length === 0 ? (
          <p className="muted">No runs yet.</p>
        ) : (
          <table className="lb runs-table">
            <thead>
              <tr>
                <th className="num">#</th>
                <th>Status</th>
                <th>Solution</th>
                <th className="num">Score</th>
                <th className="num">Cost</th>
                <th>When</th>
              </tr>
            </thead>
            <tbody>
              {[...runs].reverse().map((r) => {
                const sol =
                  (r.candidate?.extra?.name as string) ??
                  (Object.values(r.context).find(
                    (v) => v && typeof v === "object" && "solution" in v,
                  ) as { solution?: string })?.solution ??
                  "—";
                return (
                  <Fragment key={r.id}>
                    <tr
                      className="run-row"
                      onClick={() => setOpen(open === r.id ? null : r.id)}
                    >
                      <td className="num">{r.iteration}</td>
                      <td>
                        <StatusPill status={r.status} />
                      </td>
                      <td className="mono">{sol}</td>
                      <td className="num primary">
                        {typeof r.candidate?.score === "number"
                          ? `${r.candidate.score.toFixed(1)}%`
                          : "—"}
                      </td>
                      <td className="num">
                        {typeof r.candidate?.cost_usd === "number"
                          ? `$${r.candidate.cost_usd.toFixed(2)}`
                          : "—"}
                      </td>
                      <td className="muted">
                        {new Date(r.created_at).toLocaleString()}
                      </td>
                    </tr>
                    {open === r.id && (
                      <tr>
                        <td colSpan={6}>
                          <RunDetailBlock runId={r.id} />
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
