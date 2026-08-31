"use client";

import { type ReactNode, use, useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { getLab, type LabDetail } from "@/lib/api";
import { LabProvider } from "./lab-context";

const TABS = [
  { slug: "", label: "Overview" },
  { slug: "experiments", label: "Experiments" },
  { slug: "benchmarks", label: "Benchmarks" },
];

export default function LabLayout({
  children,
  params,
}: {
  children: ReactNode;
  params: Promise<{ labId: string }>;
}) {
  const { labId } = use(params);
  const pathname = usePathname();

  const [lab, setLab] = useState<LabDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLab(null);
    setError(null);
    getLab(labId)
      .then(setLab)
      .catch((e) => setError(e?.message ?? "failed to load lab"));
  }, [labId]);

  if (error) return <p className="error">{error}</p>;
  if (!lab) return <p className="muted">Loading lab…</p>;

  const base = `/labs/${labId}`;
  const activeTab = pathname === base ? "" : pathname.slice(base.length + 1).split("/")[0];

  return (
    <LabProvider value={lab}>
      <div className="lab-header">
        <div className="lab-title-row">
          <h1>{lab.name}</h1>
          <span className={`badge badge-${lab.source}`}>{lab.source}</span>
        </div>
        {lab.description && <p className="lab-desc">{lab.description}</p>}
        {lab.repo_url && (
          <p className="lab-repo">
            <span className="muted">repo</span> <code>{lab.repo_url}</code>
            <span className="muted"> · {lab.repo_default_branch}</span>
          </p>
        )}
      </div>

      <nav className="tabs">
        {TABS.map((t) => (
          <Link
            key={t.slug}
            href={t.slug ? `${base}/${t.slug}` : base}
            className={`tab${activeTab === t.slug ? " is-active" : ""}`}
          >
            {t.label}
            {t.slug === "benchmarks" && (
              <span className="tab-count">{lab.benchmarks.length}</span>
            )}
          </Link>
        ))}
      </nav>

      <div className="tab-body">{children}</div>
    </LabProvider>
  );
}
