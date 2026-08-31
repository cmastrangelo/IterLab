"use client";

import { type FormEvent, useEffect, useState } from "react";

import {
  type Agent,
  type AgentKind,
  createAgent,
  deleteAgent,
  listAgents,
  updateAgent,
} from "@/lib/api";

interface Draft {
  name: string;
  description: string;
  kind: AgentKind;
  command: string;
  args: string;
  working_dir: string;
  provider: string;
  model: string;
  credential_env: string;
}

const EMPTY: Draft = {
  name: "",
  description: "",
  kind: "cli",
  command: "claude",
  args: "",
  working_dir: "",
  provider: "anthropic",
  model: "",
  credential_env: "",
};

function toDraft(a: Agent): Draft {
  return {
    name: a.name,
    description: a.description ?? "",
    kind: a.kind,
    command: a.cli?.command ?? "claude",
    args: (a.cli?.args ?? []).join(" "),
    working_dir: a.cli?.working_dir ?? "",
    provider: a.api?.provider ?? "anthropic",
    model: a.api?.model ?? "",
    credential_env: a.api?.credential_env ?? "",
  };
}

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [editing, setEditing] = useState<Agent | null>(null);
  const [draft, setDraft] = useState<Draft>(EMPTY);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = () => listAgents().then(setAgents).catch((e) => setError(e?.message));

  useEffect(() => {
    refresh();
  }, []);

  function startNew() {
    setEditing(null);
    setDraft(EMPTY);
    setError(null);
  }

  function startEdit(a: Agent) {
    setEditing(a);
    setDraft(toDraft(a));
    setError(null);
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);

    const cli = {
      command: draft.command.trim() || "claude",
      args: draft.args.trim() ? draft.args.trim().split(/\s+/) : [],
      working_dir: draft.working_dir.trim() || null,
    };
    const api = {
      provider: draft.provider.trim() || "anthropic",
      model: draft.model.trim() || null,
      credential_env: draft.credential_env.trim() || null,
    };

    try {
      if (editing) {
        await updateAgent(editing.id, {
          name: draft.name,
          description: draft.description || null,
          ...(editing.kind === "cli" ? { cli } : { api }),
        });
      } else {
        await createAgent({
          name: draft.name,
          description: draft.description || null,
          kind: draft.kind,
          ...(draft.kind === "cli" ? { cli } : { api }),
        });
      }
      await refresh();
      startNew();
    } catch (err) {
      setError(err instanceof Error ? err.message : "failed to save");
    } finally {
      setBusy(false);
    }
  }

  async function onDelete(a: Agent) {
    if (!confirm(`Delete agent "${a.name}"?`)) return;
    await deleteAgent(a.id);
    if (editing?.id === a.id) startNew();
    await refresh();
  }

  return (
    <>
      <div className="lab-header">
        <div className="lab-title-row">
          <h1>Agents</h1>
        </div>
        <p className="lab-desc">
          An agent is a way to drive an LLM. <strong>CLI</strong> runs a local
          command (e.g. <code>claude</code>); <strong>API</strong> calls a hosted
          model. Agents are executed by a worker, never by the controller.
        </p>
      </div>

      <nav className="tabs">
        <span className="tab is-active">Configuration</span>
      </nav>

      <div className="tab-body agents-grid">
        <section className="panel">
          <h2>Configured agents</h2>
          {agents.length === 0 ? (
            <p className="muted">None yet.</p>
          ) : (
            <ul className="agent-list">
              {agents.map((a) => (
                <li key={a.id} className={editing?.id === a.id ? "is-active" : ""}>
                  <button type="button" className="agent-row" onClick={() => startEdit(a)}>
                    <span className="agent-name">{a.name}</span>
                    <span className={`chip chip-${a.kind}`}>{a.kind}</span>
                    {a.managed && <span className="chip">managed</span>}
                    <span className="agent-detail">
                      {a.kind === "cli"
                        ? `${a.cli?.command} ${(a.cli?.args ?? []).join(" ")}`.trim()
                        : `${a.api?.provider}${a.api?.model ? ` · ${a.api.model}` : ""}`}
                    </span>
                  </button>
                  {!a.managed && (
                    <button type="button" className="link-danger" onClick={() => onDelete(a)}>
                      delete
                    </button>
                  )}
                </li>
              ))}
            </ul>
          )}
          <button type="button" className="ghost-btn" onClick={startNew}>
            + New agent
          </button>
        </section>

        <section className="panel">
          <h2>{editing ? `Edit: ${editing.name}` : "New agent"}</h2>
          {editing?.managed ? (
            <p className="muted">
              This agent is provisioned from instance config and can&rsquo;t be
              edited here. Change <code>instance/agents/*.yaml</code> and restart.
            </p>
          ) : (
            <form onSubmit={onSubmit} className="agent-form">
              {error && <p className="error">{error}</p>}

              <label htmlFor="a-name">Name</label>
              <input
                id="a-name"
                required
                value={draft.name}
                onChange={(e) => setDraft({ ...draft, name: e.target.value })}
              />

              <label htmlFor="a-desc">Description</label>
              <input
                id="a-desc"
                value={draft.description}
                onChange={(e) => setDraft({ ...draft, description: e.target.value })}
              />

              {!editing && (
                <>
                  <label>Kind</label>
                  <div className="radio-row">
                    {(["cli", "api"] as AgentKind[]).map((k) => (
                      <label key={k} className="radio">
                        <input
                          type="radio"
                          name="kind"
                          checked={draft.kind === k}
                          onChange={() => setDraft({ ...draft, kind: k })}
                        />
                        {k.toUpperCase()}
                      </label>
                    ))}
                  </div>
                </>
              )}

              {(editing?.kind ?? draft.kind) === "cli" ? (
                <>
                  <label htmlFor="a-cmd">Command</label>
                  <input
                    id="a-cmd"
                    value={draft.command}
                    onChange={(e) => setDraft({ ...draft, command: e.target.value })}
                  />
                  <label htmlFor="a-args">Args (space-separated)</label>
                  <input
                    id="a-args"
                    value={draft.args}
                    placeholder="-p --permission-mode acceptEdits"
                    onChange={(e) => setDraft({ ...draft, args: e.target.value })}
                  />
                  <label htmlFor="a-wd">Working directory (optional)</label>
                  <input
                    id="a-wd"
                    value={draft.working_dir}
                    placeholder="left to the task's checkout"
                    onChange={(e) => setDraft({ ...draft, working_dir: e.target.value })}
                  />
                  <p className="muted hint">
                    Runs on the worker host — that machine needs the{" "}
                    <code>{draft.command || "claude"}</code> CLI installed and
                    authenticated.
                  </p>
                </>
              ) : (
                <>
                  <label htmlFor="a-prov">Provider</label>
                  <input
                    id="a-prov"
                    value={draft.provider}
                    onChange={(e) => setDraft({ ...draft, provider: e.target.value })}
                  />
                  <label htmlFor="a-model">Model</label>
                  <input
                    id="a-model"
                    value={draft.model}
                    placeholder="claude-sonnet-5"
                    onChange={(e) => setDraft({ ...draft, model: e.target.value })}
                  />
                  <label htmlFor="a-cred">Credential env var</label>
                  <input
                    id="a-cred"
                    value={draft.credential_env}
                    placeholder="ANTHROPIC_API_KEY"
                    onChange={(e) => setDraft({ ...draft, credential_env: e.target.value })}
                  />
                  <p className="muted hint">
                    Store the name of an env var, not the key. The worker resolves
                    it at dispatch time.
                  </p>
                </>
              )}

              <div className="form-actions">
                <button type="submit" disabled={busy}>
                  {busy ? "Saving…" : editing ? "Save changes" : "Create agent"}
                </button>
                {editing && (
                  <button type="button" className="ghost-btn" onClick={startNew}>
                    Cancel
                  </button>
                )}
              </div>
            </form>
          )}
        </section>
      </div>
    </>
  );
}
