"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/lib/auth";

export default function IndexPage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    router.replace(user ? "/labs" : "/login");
  }, [user, loading, router]);

  return (
    <main className="center">
      <p className="muted">Loading…</p>
    </main>
  );
}
