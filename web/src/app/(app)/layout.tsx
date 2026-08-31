"use client";

import { type ReactNode, useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { type Lab, listLabs } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function AppLayout({ children }: { children: ReactNode }) {
  const { user, loading, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  const [labs, setLabs] = useState<Lab[]>([]);
  const [labsError, setLabsError] = useState<string | null>(null);

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  useEffect(() => {
    if (!user) return;
    listLabs()
      .then(setLabs)
      .catch((e) => setLabsError(e?.message ?? "failed to load labs"));
  }, [user]);

  if (loading || !user) {
    return (
      <main className="center">
        <p className="muted">Loading…</p>
      </main>
    );
  }

  const activeLabId = pathname.match(/\/labs\/([^/]+)/)?.[1];

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="sidebar-brand">IterLab</div>

        <div className="sidebar-section">
          <div className="sidebar-heading">Labs</div>
          <nav className="sidebar-nav">
            {labs.map((lab) => (
              <Link
                key={lab.id}
                href={`/labs/${lab.id}`}
                className={`sidebar-link${activeLabId === lab.id ? " is-active" : ""}`}
              >
                <span className="dot" data-source={lab.source} />
                {lab.name}
              </Link>
            ))}
            {labs.length === 0 && !labsError && (
              <span className="sidebar-empty">No labs yet</span>
            )}
            {labsError && <span className="sidebar-empty error">{labsError}</span>}
          </nav>
        </div>
      </aside>

      <div className="main-col">
        <header className="topbar">
          <div />
          <div className="account">
            <span>{user.full_name ? `${user.full_name} · ${user.email}` : user.email}</span>
            <button
              type="button"
              onClick={async () => {
                await logout();
                router.replace("/login");
              }}
            >
              Sign out
            </button>
          </div>
        </header>
        <main className="content">{children}</main>
      </div>
    </div>
  );
}
