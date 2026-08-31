"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { type Lab, listLabs } from "@/lib/api";

export default function LabsIndex() {
  const router = useRouter();
  const [state, setState] = useState<"loading" | "empty" | "error">("loading");
  const [message, setMessage] = useState("");

  useEffect(() => {
    listLabs()
      .then((labs: Lab[]) => {
        if (labs.length > 0) router.replace(`/labs/${labs[0].id}`);
        else setState("empty");
      })
      .catch((e) => {
        setState("error");
        setMessage(e?.message ?? "failed to load labs");
      });
  }, [router]);

  if (state === "loading") return <p className="muted">Loading labs…</p>;
  if (state === "error") return <p className="error">{message}</p>;

  return (
    <div className="panel">
      <h1>No labs yet</h1>
      <p className="muted">
        Labs are provisioned from this deployment&rsquo;s <code>instance/</code>{" "}
        configuration, or created via the API. Add a{" "}
        <code>instance/labs/*.yaml</code> file and restart the backend.
      </p>
    </div>
  );
}
