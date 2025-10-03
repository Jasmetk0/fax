import { useCallback, useEffect, useRef, useState } from "react";
import { loadScriptOnce } from "../utils/loadScriptOnce";

const SCRIPT_URL = "/static/squash-engine.iife.js";
const CSS_URL = "/static/squash-engine-player-growth.css";

function ensureStylesheet() {
  if (document.querySelector(`link[href="${CSS_URL}"]`)) return;
  const link = document.createElement("link");
  link.rel = "stylesheet";
  link.href = CSS_URL;
  document.head.appendChild(link);
}

export default function SquashEnginePlayerGrowthPage() {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const apiRef = useRef<{ unmount?: () => void } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const mountWidget = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      ensureStylesheet();
      await loadScriptOnce(SCRIPT_URL);
      const container = containerRef.current;
      if (!container) {
        throw new Error("Container not ready");
      }
      const api = (window as typeof window & {
        SquashEngine?: {
          mountPlayerGrowth?: (element: HTMLElement) => { unmount?: () => void };
        };
      }).SquashEngine?.mountPlayerGrowth?.(container);
      apiRef.current = api ?? null;
      setLoading(false);
    } catch (err) {
      console.error("Failed to mount SquashEngine widget", err);
      setError(err instanceof Error ? err.message : "Failed to load widget");
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    mountWidget();
    return () => {
      // Ensure embed is torn down when leaving the page
      apiRef.current?.unmount?.();
      apiRef.current = null;
    };
  }, [mountWidget]);

  return (
    <section className="card">
      <h1>SquashEngine · Player Growth</h1>
      <p style={{ marginBottom: 16, color: "#64748b" }}>
        Přehled růstu hráčů využívající SquashEngine vizualizace.
      </p>
      {loading ? (
        <div className="loader" role="status" aria-live="polite">
          <div className="spinner" />
          <span>Načítám widget…</span>
        </div>
      ) : null}
      {error ? (
        <div role="alert">
          <p>Nepodařilo se načíst SquashEngine widget. ({error})</p>
          <button type="button" className="retry-button" onClick={mountWidget}>
            Zkusit znovu
          </button>
        </div>
      ) : null}
      <div className="se-root" style={{ marginTop: 16 }}>
        <div id="se-player-growth" ref={containerRef} style={{ minHeight: 640 }} />
      </div>
    </section>
  );
}
