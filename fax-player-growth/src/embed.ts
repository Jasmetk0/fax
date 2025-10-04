import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { DEFAULT_STATE } from "./constants";
import { enforceGuardrails } from "./lib/guardrails";
import { serializeUrlState } from "./lib/urlState";
import type { CurveParams } from "./types";
import "./styles.css";

export type MountOptions = {
  showFanChart?: boolean;
  showCohort?: boolean;
  params?: Partial<CurveParams>;
  readOnly?: boolean;
};

type MountReturn = { unmount: () => void };

declare global {
  interface Window {
    SquashEngine?: {
      mountPlayerGrowth: (
        element: string | HTMLElement,
        options?: MountOptions,
      ) => MountReturn;
    };
  }
}

function resolveElement(element: string | HTMLElement): HTMLElement {
  if (typeof element === "string") {
    const el = document.querySelector<HTMLElement>(element);
    if (!el) {
      throw new Error(`Container not found for selector: ${element}`);
    }
    return el;
  }
  return element;
}

function applyOptions(options?: MountOptions) {
  if (!options) return;

  const nextState = {
    ...DEFAULT_STATE,
    params: { ...DEFAULT_STATE.params },
  };

  if (typeof options.showFanChart === "boolean") {
    nextState.showFanChart = options.showFanChart;
  }

  if (typeof options.showCohort === "boolean") {
    nextState.showCohort = options.showCohort;
  }

  if (options.params) {
    const { params } = enforceGuardrails({
      ...DEFAULT_STATE.params,
      ...options.params,
    });
    nextState.params = params;
  }

  const qs = serializeUrlState(nextState);
  const url = new URL(window.location.href);
  url.search = qs ? (qs.startsWith("?") ? qs.slice(1) : qs) : "";
  const nextUrl = `${url.pathname}${url.search}${url.hash}`;
  window.history.replaceState(null, document.title, nextUrl);
}

export function mountPlayerGrowth(element: HTMLElement, options?: MountOptions): MountReturn;
export function mountPlayerGrowth(element: string, options?: MountOptions): MountReturn;
export function mountPlayerGrowth(
  element: string | HTMLElement,
  options?: MountOptions,
): MountReturn {
  applyOptions(options);
  const el = resolveElement(element);
  const root = createRoot(el);
  root.render(React.createElement(App));
  return { unmount: () => root.unmount() };
}

window.SquashEngine = { mountPlayerGrowth };
