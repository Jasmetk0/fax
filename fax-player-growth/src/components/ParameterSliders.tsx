import { SLIDER_CONFIGS, STYLE_PRESETS } from "../constants";
import type { CurveParams } from "../lib/curve";
import type { ParameterKey, StylePresetKey } from "../types";

export type ParameterSlidersProps = {
  params: CurveParams;
  onParamChange: (key: ParameterKey, value: number) => void;
  selectedPreset: StylePresetKey;
  onPresetChange: (preset: StylePresetKey) => void;
  showFanChart: boolean;
  onToggleFanChart: (value: boolean) => void;
  showCohort: boolean;
  onToggleCohort: (value: boolean) => void;
};

const formatValue = (key: ParameterKey, value: number): string => {
  const config = SLIDER_CONFIGS.find((item) => item.key === key);
  if (!config) return value.toFixed(2);
  if (config.format) return config.format(value);
  const decimals = config.step >= 1 ? 0 : config.step >= 0.1 ? 1 : 2;
  return value.toFixed(decimals);
};

export function ParameterSliders({
  params,
  onParamChange,
  selectedPreset,
  onPresetChange,
  showFanChart,
  onToggleFanChart,
  showCohort,
  onToggleCohort,
}: ParameterSlidersProps) {
  return (
    <section className="space-y-8">
      <div>
        <h2 className="text-lg font-semibold text-slate-800">Style preset</h2>
        <p className="mt-1 text-sm text-slate-600">
          Vyber referenční profil. Přepnutí jen předvyplní posuvníky – své úpravy vždy potvrď.
        </p>
        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          {STYLE_PRESETS.map((preset) => (
            <label
              key={preset.key}
              className={`rounded-lg border p-3 transition hover:border-slate-400 ${
                selectedPreset === preset.key ? "border-slate-700 bg-white shadow" : "border-slate-200 bg-slate-100"
              }`}
            >
              <div className="flex items-center gap-2">
                <input
                  type="radio"
                  name="style"
                  value={preset.key}
                  checked={selectedPreset === preset.key}
                  onChange={() => onPresetChange(preset.key)}
                  className="h-4 w-4 border-slate-400 text-slate-700 focus:ring-slate-500"
                />
                <span className="font-medium text-slate-800">{preset.label}</span>
              </div>
              <p className="mt-2 text-sm text-slate-600">{preset.description}</p>
            </label>
          ))}
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {SLIDER_CONFIGS.map((config) => (
          <label key={config.key} className="flex flex-col gap-2 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex items-start justify-between">
              <div>
                <span className="font-medium text-slate-800">{config.label}</span>
                <span className="ml-2 text-xs text-slate-500">{formatValue(config.key, params[config.key])}</span>
              </div>
              <span className="tooltip text-xs" title={config.tooltip}>
                ⓘ
              </span>
            </div>
            <input
              type="range"
              min={config.min}
              max={config.max}
              step={config.step}
              value={params[config.key]}
              onChange={(event) => onParamChange(config.key, Number(event.target.value))}
            />
            <div className="flex justify-between text-xs text-slate-500">
              <span>{formatValue(config.key, config.min)}</span>
              <span>{formatValue(config.key, config.max)}</span>
            </div>
          </label>
        ))}
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <label className="flex items-start gap-3 rounded-lg border border-slate-200 bg-white p-4">
          <input
            type="checkbox"
            checked={showFanChart}
            onChange={(event) => onToggleFanChart(event.target.checked)}
            className="mt-1 h-4 w-4 rounded border-slate-400 text-slate-700 focus:ring-slate-500"
          />
          <div>
            <span className="font-medium text-slate-800">Show uncertainty from ranges</span>
            <p className="text-sm text-slate-600">
              Zobraz 50% a 90% fan chart spočítaný deterministicky z rozsahů potenciálu, peaku a strmosti.
            </p>
          </div>
        </label>
        <label className="flex items-start gap-3 rounded-lg border border-slate-200 bg-white p-4">
          <input
            type="checkbox"
            checked={showCohort}
            onChange={(event) => onToggleCohort(event.target.checked)}
            className="mt-1 h-4 w-4 rounded border-slate-400 text-slate-700 focus:ring-slate-500"
          />
          <div>
            <span className="font-medium text-slate-800">Show cohort</span>
            <p className="text-sm text-slate-600">
              Porovnej se s referenčními profily Shotmaker, Retriever a Hybrid. Slouží jen jako kontext.
            </p>
          </div>
        </label>
      </div>
    </section>
  );
}
