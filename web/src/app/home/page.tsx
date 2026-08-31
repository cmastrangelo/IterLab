"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/lib/auth";

export default function HomePage() {
  const { user, loading, logout } = useAuth();
  const router = useRouter();
  const [signingOut, setSigningOut] = useState(false);

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [user, loading, router]);

  if (loading || !user) {
    return (
      <main className="center">
        <p className="muted">Loading…</p>
      </main>
    );
  }

  async function onLogout() {
    setSigningOut(true);
    await logout();
    router.replace("/login");
  }

  return (
    <>
      <header className="topbar">
        <div className="brand">IterLab</div>
        <div className="account">
          <span>{user.full_name ? `${user.full_name} · ${user.email}` : user.email}</span>
          <button type="button" onClick={onLogout} disabled={signingOut}>
            {signingOut ? "Signing out…" : "Sign out"}
          </button>
        </div>
      </header>

      <main className="construction">
        <div>
          <div className="emoji">🚧</div>
          <h1>Under construction</h1>
          <p>
            You’re signed in. Projects, Labs, Experiments, and Workers will live
            here — the backend abstractions are in place and the UI is next.
          </p>
        </div>
      </main>
    </>
  );
}
