import { beforeEach, describe, expect, it, vi } from "vitest";
import { mountPlayerGrowth } from "../src/embed";

describe("mountPlayerGrowth options", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    window.history.replaceState({}, "", "/");
    document.body.innerHTML = "";
  });

  it("syncs provided options into the URL before mounting", () => {
    const container = document.createElement("div");
    document.body.append(container);

    const { unmount } = mountPlayerGrowth(container, {
      showFanChart: true,
      showCohort: false,
      params: { potential: 92, peakAge: 27.25 },
    });

    unmount();

    const url = new URL(window.location.href);
    expect(url.searchParams.get("fan")).toBe("1");
    expect(url.searchParams.get("cohort")).toBe("0");
    expect(Number(url.searchParams.get("potential"))).toBeCloseTo(92, 3);
    expect(Number(url.searchParams.get("peakAge"))).toBeCloseTo(27.3, 1);
  });
});
