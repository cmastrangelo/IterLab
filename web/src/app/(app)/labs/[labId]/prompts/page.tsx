"use client";

import { useEffect, useMemo, useState } from "react";

import { listLabPrompts, type Prompt } from "@/lib/api";
import { useLab } from "../lab-context";

function num(v: number | null, suffix = ""): string {
  return typeof v === "number" ? `${v.toFixed(1)}${suffix}` : "—";
}

export default function PromptsTab() {
  const lab = useLab();
  const [prompts, setPrompts] = useState<Prompt[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState<string | null>(null);

  useEffect(() => {
    setPrompts(null);
    setError(null);
    listLabPrompts(lab.id)
      .then(setPrompts)
      .catch((e) => setError(e?.message ?? "failed to load prompts"));
  }, [lab.id]);

  const groups = useMemo(() => {
    const by = new Map<string, Prompt[]>();
    for (const p of prompts ?? []) {
      const arr = by.get(p.slug) ?? [];
      arr.push(p);
      by.set(p.slug, arr);
    }
    for (const arr of by.values()) arr.sort((a, b) => a.version - b.version);
    return [...by.entries()];
  }, [prompts]);

  if (error) return <p className="error">{error}</p>;
  if (!prompts) return <p className="muted">Loading prompts…</p>;
  if (prompts.length === 0)
    return (
      <p className="muted">
        No prompts recorded yet. Every prompt an agent step sends is versioned here
        the first time it runs.
      </p>
    );

  const bindings = lab.prompt_bindings ?? {};

  return (
    <div className="prompts">
      <p className="muted hint">
        Prompt text is <strong>immutable</strong> — each version is a registered,
        content-hashed file (<code>prompts/&lt;lab&gt;/&lt;slug&gt;/v&lt;N&gt;.md</code>)
        that can never change once recorded, so per-version stats stay clean. The
        only knob is which version is <strong>active</strong>; a new wording is a
        new file.
      </p>

      {groups.map(([slug, versions]) => (
        <section key={slug} className="panel">
          <div className="lb-head">
            <h2>
              <code>{slug}</code>
            </h2>
            <span className="muted">
              {versions.length} version{versions.length === 1 ? "" : "s"}
              {typeof bindings[slug] === "number" && ` · active: v${bindings[slug]}`}
            </span>
          </div>

          <table className="lb prompt-versions">
            <thead>
              <tr>
                <th className="num">v</th>
                <th>Template</th>
                <th className="num">Candidates</th>
                <th className="num">Scored</th>
                <th className="num primary">Avg score</th>
                <th className="num">Best</th>
                <th>Added</th>
              </tr>
            </thead>
            <tbody>
              {versions.map((p) => {
                const isOpen = open === p.id;
                const active = bindings[p.slug] === p.version;
                return (
                  <tr
                    key={p.id}
                    className={`prompt-row${active ? " is-active-prompt" : ""}`}
                    onClick={() => setOpen(isOpen ? null : p.id)}
                  >
                    <td className="num">
                      <strong>{p.version}</strong>
                      {active && <span className="pill">active</span>}
                    </td>
                    <td className="prompt-text">
                      {isOpen ? (
                        <pre className="step-out">{p.text}</pre>
                      ) : (
                        <span className="mono">{p.text.slice(0, 120)}…</span>
                      )}
                    </td>
                    <td className="num">{p.uses}</td>
                    <td className="num">{p.scored}</td>
                    <td className="num primary">{num(p.avg_score)}</td>
                    <td className="num">{num(p.best_score)}</td>
                    <td className="muted">
                      {new Date(p.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </section>
      ))}
    </div>
  );
}
