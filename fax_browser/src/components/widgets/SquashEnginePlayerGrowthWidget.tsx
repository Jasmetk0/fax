import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { loadScriptOnce } from "../../utils/loadScriptOnce";

const SCRIPT_URL = "/static/squash-engine.iife.js";
const CSS_URL = "/static/squash-engine-player-growth.css";

function ensureStylesheet() {
  if (document.querySelector(`link[href="${CSS_URL}"]`)) return;
  const link = document.createElement("link");
  link.rel = "stylesheet";
  link.href = CSS_URL;
  document.head.appendChild(link);
}

export default function SquashEnginePlayerGrowthWidget() {
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
      if (!container) throw new Error("Container not ready");
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
      // Clean up widget when component unmounts
      apiRef.current?.unmount?.();
      apiRef.current = null;
    };
  }, [mountWidget]);

  return (
    <div className="card">
      <div className="widget-header">
        <div>
          <h2 style={{ margin: 0 }}>SquashEngine: Player Growth</h2>
          <p style={{ margin: "4px 0 0", color: "#64748b", fontSize: 14 }}>
            Zobrazte růst a vývoj hráčů přímo z dashboardu.
          </p>
        </div>
      </div>
      <div className="widget-body">
        {loading ? (
          <div className="loader" role="status" aria-live="polite">
            <div className="spinner" />
            <span>Načítám widget…</span>
          </div>
        ) : null}
        {error ? (
          <div role="alert">
            <p>Nepodařilo se načíst mini widget. ({error})</p>
            <button type="button" className="retry-button" onClick={mountWidget}>
              Zkusit znovu
            </button>
          </div>
        ) : null}
        <div className="se-root" style={{ height: 360, overflow: "hidden" }}>
          <div id="se-player-growth-widget" ref={containerRef} style={{ minHeight: 320 }} />
        </div>
      </div>
      <div className="widget-footer">
        <Link to="/squash-engine/player-growth">Open full page →</Link>
      </div>
    </div>
  );
}
