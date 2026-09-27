"use client";

import { useEffect } from "react";
import { ApiError } from "@/lib/api";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  const isBackendUnreachable = !(error instanceof ApiError);

  return (
    <main className="page">
      <h1 style={{ fontSize: "1.3rem", margin: 0 }}>
        {isBackendUnreachable ? "Backend unavailable" : "Request failed"}
      </h1>
      <div className="empty-state" style={{ marginTop: "1rem" }}>
        {isBackendUnreachable ? (
          <>
            This page couldn&apos;t reach the Switchyard API. Confirm the
            backend is running and that{" "}
            <code className="mono">NEXT_PUBLIC_API_BASE_URL</code> points at
            it, then retry.
          </>
        ) : (
          <>
            The API returned an error
            {error instanceof ApiError ? ` (HTTP ${error.status})` : ""}:{" "}
            {error.message || "no further detail was given."}
          </>
        )}
      </div>
      <button type="button" className="primary" onClick={() => reset()}>
        Retry
      </button>
    </main>
  );
}
