import { useEffect, useMemo, useRef, useState } from "react";
import { HeaderStats } from "./components/HeaderStats";
import { ParameterSliders } from "./components/ParameterSliders";
import { CurveStudio } from "./components/CurveStudio";
import { ZonesLegend } from "./components/ZonesLegend";
import {
  AGE_RANGE,
  COHORT_PRESETS,
  CSV_FILENAME,
  DEFAULT_PARAMS,
  DEFAULT_STATE,
  PNG_FILENAME,
  SLIDER_CONFIGS,
  STYLE_PRESETS,
} from "./constants";
import { idealCurve, slopeBetween, type CurveParams, type Point } from "./lib/curve";
import { exportChartPng, exportCurveCsv } from "./lib/export";
import { buildFanChart } from "./lib/fanChart";
import { enforceGuardrails } from "./lib/guardrails";
import { parseUrlState, syncUrlState } from "./lib/urlState";
import type { GuardrailNotice, StylePresetKey, UrlState } from "./types";

const cloneParams = (params: CurveParams): CurveParams => ({ ...params });

const findPreset = (key: StylePresetKey) => STYLE_PRESETS.find((preset) => preset.key === key);

const calculateInsights = (line: Point[], params: CurveParams) => {
  if (line.length === 0) {
    return {
      peakOvr: 0,
      peakAge: 0,
      peakWindowMonths: 0,
      ageAt95: 0,
      ageAt90: 0,
      primeSlope: 0,
      declineSlope: 0,
    };
  }
  const peak = line.reduce((best, point) => (point.ovr > best.ovr ? point : best), line[0]);
  const ninetyFive = peak.ovr * 0.95;
  const ninety = peak.ovr * 0.9;

  let ageAt95 = peak.age;
  let ageAt90 = peak.age;
  for (const point of line) {
    if (point.ovr >= ninetyFive) {
      ageAt95 = point.age;
      break;
    }
  }
  for (const point of line) {
    if (point.ovr >= ninety) {
      ageAt90 = point.age;
      break;
    }
  }

  const threshold = peak.ovr - 1.5;
  let first = peak.age;
  let last = peak.age;
  for (const point of line) {
    if (point.ovr >= threshold) {
      first = point.age;
      break;
    }
  }
  for (let index = line.length - 1; index >= 0; index -= 1) {
    if (line[index].ovr >= threshold) {
      last = line[index].age;
      break;
    }
  }
  const spanYears = Math.max(0, last - first) + AGE_RANGE.step;
  const peakWindowMonths = Math.round(spanYears * 12);

  return {
    peakOvr: peak.ovr,
    peakAge: peak.age,
    peakWindowMonths,
    ageAt95,
    ageAt90,
    primeSlope: slopeBetween(16, 22, params),
    declineSlope: slopeBetween(33, 36, params),
  };
};

const makeCohortCurves = () =>
  Object.entries(COHORT_PRESETS).map(([key, presetParams]) => ({
    key: key as StylePresetKey,
    label: key,
    points: idealCurve(presetParams),
  }));

const roundParamForUrl = (value: number, key: keyof CurveParams) => {
  const slider = SLIDER_CONFIGS.find((item) => item.key === key);
  if (!slider) return value;
  const decimals = slider.step >= 1 ? 0 : slider.step >= 0.1 ? 1 : 3;
  return Number(value.toFixed(decimals));
};

const buildUrlState = (params: CurveParams, showFan: boolean, showCohort: boolean, preset: StylePresetKey): UrlState => ({
  params: {
    potential: roundParamForUrl(params.potential, "potential"),
    floor: roundParamForUrl(params.floor, "floor"),
    peakAge: roundParamForUrl(params.peakAge, "peakAge"),
    k: roundParamForUrl(params.k, "k"),
    peakRetention: roundParamForUrl(params.peakRetention, "peakRetention"),
    d1: roundParamForUrl(params.d1, "d1"),
    d2: roundParamForUrl(params.d2, "d2"),
    d3: roundParamForUrl(params.d3, "d3"),
  },
  showFanChart: showFan,
  showCohort,
  preset,
});

export default function App() {
  const [params, setParams] = useState<CurveParams>(cloneParams(DEFAULT_PARAMS));
  const [selectedPreset, setSelectedPreset] = useState<StylePresetKey>(DEFAULT_STATE.preset);
  const [showFanChart, setShowFanChart] = useState(DEFAULT_STATE.showFanChart);
  const [showCohort, setShowCohort] = useState(DEFAULT_STATE.showCohort);
  const [guardrailNotices, setGuardrailNotices] = useState<GuardrailNotice[]>([]);
  const [dirty, setDirty] = useState(false);
  const chartRef = useRef<HTMLDivElement>(null);
  const hydratedRef = useRef(false);

  useEffect(() => {
    const parsed = parseUrlState(window.location.search, DEFAULT_STATE);
    setParams(parsed.state.params);
    setShowFanChart(parsed.state.showFanChart);
    setShowCohort(parsed.state.showCohort);
    setSelectedPreset(parsed.state.preset);
    setGuardrailNotices(parsed.notices);
    setDirty(false);
    hydratedRef.current = true;
  }, []);

  useEffect(() => {
    if (!hydratedRef.current) return;
    const nextState = buildUrlState(params, showFanChart, showCohort, selectedPreset);
    syncUrlState(nextState);
  }, [params, showFanChart, showCohort, selectedPreset]);

  const curvePoints = useMemo(() => idealCurve(params, AGE_RANGE.min, AGE_RANGE.max, AGE_RANGE.step), [params]);

  const fanPoints = useMemo(() => (showFanChart ? buildFanChart(params) : null), [params, showFanChart]);

  const linePoints: Point[] = useMemo(() => {
    if (showFanChart && fanPoints) {
      return fanPoints.map((point) => ({ age: point.age, ovr: point.median }));
    }
    return curvePoints;
  }, [curvePoints, fanPoints, showFanChart]);

  const chartData = useMemo(() => {
    if (showFanChart && fanPoints) {
      return fanPoints.map((point) => ({
        age: point.age,
        ovr: point.median,
        median: point.median,
        band90Low: point.q05,
        band90Span: point.q95 - point.q05,
        band50Low: point.q25,
        band50Span: point.q75 - point.q25,
      }));
    }
    return curvePoints.map((point) => ({ age: point.age, ovr: point.ovr }));
  }, [curvePoints, fanPoints, showFanChart]);

  const insights = useMemo(() => calculateInsights(linePoints, params), [linePoints, params]);

  const cohorts = useMemo(() => makeCohortCurves(), []);

  const handleParamChange = (key: keyof CurveParams, value: number) => {
    setDirty(true);
    setParams((previous) => {
      const draft = { ...previous, [key]: value } as CurveParams;
      const { params: guarded, notices } = enforceGuardrails(draft);
      setGuardrailNotices(notices);
      return guarded;
    });
  };

  const handlePresetChange = (presetKey: StylePresetKey) => {
    if (dirty) {
      const confirmApply = window.confirm("Přepnutím presetu přepíšeš ruční úpravy. Pokračovat?");
      if (!confirmApply) return;
    }
    const preset = findPreset(presetKey);
    if (!preset) return;
    const { params: guarded, notices } = enforceGuardrails(cloneParams(preset.params));
    setParams(guarded);
    setSelectedPreset(presetKey);
    setGuardrailNotices(notices);
    setDirty(false);
  };

  const handleExportCsv = () => {
    exportCurveCsv(linePoints, CSV_FILENAME);
  };

  const handleExportPng = async () => {
    const svg = chartRef.current?.querySelector("svg");
    if (!(svg instanceof SVGSVGElement)) {
      window.alert("SVG grafu není připravené pro export.");
      return;
    }
    try {
      await exportChartPng(svg, PNG_FILENAME);
    } catch (error) {
      window.alert((error as Error).message);
    }
  };

  const noticeTexts = guardrailNotices.map((notice) => notice.message);

  return (
    <main className="mx-auto max-w-7xl space-y-10 p-6">
      <header className="space-y-4">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">fax-player-growth</h1>
          <p className="text-slate-600">
            Deterministická simulace ideální kariérní křivky squashového hráče. Žádný šum, jen talent, práce a fyzika času.
          </p>
        </div>
        <HeaderStats insights={insights} />
        {noticeTexts.length > 0 && (
          <div className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-800">
            {noticeTexts.map((message) => (
              <p key={message}>• {message}</p>
            ))}
          </div>
        )}
      </header>

      <section className="grid gap-10 lg:grid-cols-[2fr_1fr]">
        <div className="space-y-4">
          <CurveStudio
            data={chartData}
            linePoints={linePoints}
            params={params}
            showFanChart={showFanChart}
            showCohort={showCohort}
            cohortCurves={cohorts}
            insights={insights}
            chartRef={chartRef}
          />
          <div className="flex flex-wrap items-center justify-between gap-4">
            <ZonesLegend />
            <div className="flex gap-3">
              <button
                type="button"
                onClick={handleExportCsv}
                className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow hover:border-slate-400"
              >
                Export CSV
              </button>
              <button
                type="button"
                onClick={handleExportPng}
                className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white shadow hover:bg-slate-700"
              >
                Export PNG
              </button>
            </div>
          </div>
        </div>
        <aside>
          <ParameterSliders
            params={params}
            onParamChange={handleParamChange}
            selectedPreset={selectedPreset}
            onPresetChange={handlePresetChange}
            showFanChart={showFanChart}
            onToggleFanChart={setShowFanChart}
            showCohort={showCohort}
            onToggleCohort={setShowCohort}
          />
        </aside>
      </section>
    </main>
  );
}
