"use client";

import Link from "next/link";

import { useLab } from "./lab-context";

export default function LabOverview() {
  const lab = useLab();
  const settings = Object.entries(lab.settings ?? {});

  return (
    <div className="overview">
      <section className="panel">
        <h2>Benchmarks</h2>
        {lab.benchmarks.length === 0 ? (
          <p className="muted">No benchmarks configured for this lab.</p>
        ) : (
          <ul className="mini-list">
            {lab.benchmarks.map((b) => (
              <li key={b.id}>
                <Link href={`/labs/${lab.id}/benchmarks?b=${b.slug}`}>{b.name}</Link>
                <span className="muted">
                  {" "}
                  · {b.adapter}
                  {b.primary_metric ? ` · ${b.primary_metric}` : ""}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      {settings.length > 0 && (
        <section className="panel">
          <h2>Settings</h2>
          <dl className="kv">
            {settings.map(([k, v]) => (
              <div key={k}>
                <dt>{k}</dt>
                <dd>{typeof v === "string" ? v : JSON.stringify(v)}</dd>
              </div>
            ))}
          </dl>
        </section>
      )}

      <section className="panel">
        <h2>Experiments</h2>
        <p className="muted">🚧 Not yet wired — candidate runs come next.</p>
      </section>
    </div>
  );
}
