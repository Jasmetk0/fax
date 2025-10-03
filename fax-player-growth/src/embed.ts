import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./styles.css";

declare global {
  interface Window {
    SquashEngine?: {
      mountPlayerGrowth: (container: string | HTMLElement) => { unmount: () => void };
    };
  }
}

function mount(container: string | HTMLElement) {
  const el = typeof container === "string" ? document.querySelector(container)! : container;
  const root = createRoot(el);
  root.render(React.createElement(App));
  return { unmount: () => root.unmount() };
}

window.SquashEngine = { mountPlayerGrowth: mount };
