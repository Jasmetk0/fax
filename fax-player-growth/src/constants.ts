import type { Point } from "./lib/curve";
import type { CurveParams, SliderConfig, StylePreset, StylePresetKey, UrlState } from "./types";

export const AGE_RANGE = { min: 10, max: 40, step: 0.25 } as const;

export const PARAM_BOUNDS: Record<keyof CurveParams, { min: number; max: number; step: number }> = {
  potential: { min: 85, max: 99, step: 0.1 },
  floor: { min: 30, max: 50, step: 0.1 },
  peakAge: { min: 23, max: 32, step: 0.1 },
  k: { min: 0.3, max: 0.6, step: 0.01 },
  peakRetention: { min: 0.5, max: 2.5, step: 0.1 },
  d1: { min: 0.02, max: 0.04, step: 0.001 },
  d2: { min: 0.04, max: 0.07, step: 0.001 },
  d3: { min: 0.07, max: 0.12, step: 0.001 },
};

export const DEFAULT_PARAMS: CurveParams = {
  potential: 94,
  floor: 38,
  peakAge: 27.5,
  k: 0.41,
  peakRetention: 1,
  d1: 0.03,
  d2: 0.055,
  d3: 0.09,
};

export const DEFAULT_STATE: UrlState = {
  params: { ...DEFAULT_PARAMS },
  showFanChart: false,
  showCohort: false,
  preset: "hybrid",
};

const percent = (value: number) => `${(value * 100).toFixed(1)} %`;

export const SLIDER_CONFIGS: SliderConfig[] = [
  {
    key: "potential",
    label: "Potential (ceiling)",
    min: PARAM_BOUNDS.potential.min,
    max: PARAM_BOUNDS.potential.max,
    step: PARAM_BOUNDS.potential.step,
    tooltip:
      "Maximální OVR, pokud jde všechno podle plánu. Každý bod navíc znamená tvrdší strop pro pečlivě zvládnutou kariéru.",
  },
  {
    key: "floor",
    label: "Early floor (14–16)",
    min: PARAM_BOUNDS.floor.min,
    max: PARAM_BOUNDS.floor.max,
    step: PARAM_BOUNDS.floor.step,
    tooltip:
      "Výkonnostní základ v rané adolescenci. Vyšší floor znamená, že talent rychleji stoupá, ale stále musí dorůst do svého potenciálu.",
  },
  {
    key: "peakAge",
    label: "Peak age",
    min: PARAM_BOUNDS.peakAge.min,
    max: PARAM_BOUNDS.peakAge.max,
    step: PARAM_BOUNDS.peakAge.step,
    tooltip:
      "Kdy nastane absolutní vrchol. Nižší věk vyhovuje explozivním typům, vyšší věk metodickým grinderům.",
    format: (value) => value.toFixed(1),
  },
  {
    key: "k",
    label: "Rise steepness (k)",
    min: PARAM_BOUNDS.k.min,
    max: PARAM_BOUNDS.k.max,
    step: PARAM_BOUNDS.k.step,
    tooltip:
      "Jak rychle se křivka blíží k vrcholu. Nižší k vede k plynulejšímu růstu, vyšší znamená ostrý skok během pár let.",
    format: (value) => value.toFixed(2),
  },
  {
    key: "peakRetention",
    label: "Peak retention (roky)",
    min: PARAM_BOUNDS.peakRetention.min,
    max: PARAM_BOUNDS.peakRetention.max,
    step: PARAM_BOUNDS.peakRetention.step,
    tooltip:
      "Šířka okna, ve kterém se držíš téměř na maximu. Kratší plateau je náchylné na výkyvy, delší plateau odměňuje trpělivost.",
    format: (value) => value.toFixed(1),
  },
  {
    key: "d1",
    label: "Decline d1 (28–32)",
    min: PARAM_BOUNDS.d1.min,
    max: PARAM_BOUNDS.d1.max,
    step: PARAM_BOUNDS.d1.step,
    tooltip:
      "Tempo úbytku OVR v první fázi poklesu. Každé procento navíc zvyšuje riziko rychlého vyhasnutí.",
    format: percent,
  },
  {
    key: "d2",
    label: "Decline d2 (33–36)",
    min: PARAM_BOUNDS.d2.min,
    max: PARAM_BOUNDS.d2.max,
    step: PARAM_BOUNDS.d2.step,
    tooltip:
      "Jak prudce padáš po třicítce. Strmější pokles znamená, že prime okno je třeba vytěžit bez prodlev.",
    format: percent,
  },
  {
    key: "d3",
    label: "Decline d3 (37+)",
    min: PARAM_BOUNDS.d3.min,
    max: PARAM_BOUNDS.d3.max,
    step: PARAM_BOUNDS.d3.step,
    tooltip:
      "Poslední akt kariéry. Vyšší číslo = rychlý odchod, nižší číslo = delší dohasínání s rozumnou úrovní hry.",
    format: percent,
  },
];

export const STYLE_PRESETS: StylePreset[] = [
  {
    key: "hybrid",
    label: "Hybrid",
    description:
      "Vyvážená křivka s hladkým nástupem, středně dlouhým peakem a realistickým poklesem. Základní referenční profil.",
    params: DEFAULT_PARAMS,
  },
  {
    key: "shotmaker",
    label: "Shotmaker",
    description:
      "Brzké rozsvícení talentu s vysokým stropem a kratším prime. Ideální pro agresivní hráče závislé na rychlém rozhodování.",
    params: {
      potential: 96,
      floor: 44,
      peakAge: 24,
      k: 0.56,
      peakRetention: 0.7,
      d1: 0.038,
      d2: 0.065,
      d3: 0.11,
    },
  },
  {
    key: "retriever",
    label: "Retriever",
    description:
      "Pozvolná evoluce s pozdějším vrcholem a širokým plateau. Hodí se pro kondiční styly, které vyžadují roky ladění.",
    params: {
      potential: 95,
      floor: 35,
      peakAge: 31,
      k: 0.33,
      peakRetention: 2,
      d1: 0.023,
      d2: 0.048,
      d3: 0.085,
    },
  },
];

export const FAN_SAMPLES = {
  potential: 7,
  peakAge: 7,
  k: 5,
} as const;

export const FAN_RANGES = {
  potential: [PARAM_BOUNDS.potential.min, PARAM_BOUNDS.potential.max] as const,
  peakAge: [PARAM_BOUNDS.peakAge.min, PARAM_BOUNDS.peakAge.max] as const,
  k: [PARAM_BOUNDS.k.min, PARAM_BOUNDS.k.max] as const,
};

export const COHORT_PRESETS: Record<StylePresetKey, CurveParams> = STYLE_PRESETS.reduce(
  (acc, preset) => ({ ...acc, [preset.key]: preset.params }),
  {} as Record<StylePresetKey, CurveParams>,
);

export const REFERENCE_AGES = [18, 22, 26, 30, 34];

export const ZONES = {
  development: {
    color: "development",
  },
  peak: {
    color: "peak",
  },
  decline: [
    { color: "decline1", start: 28, end: 32 },
    { color: "decline2", start: 32, end: 36 },
    { color: "decline3", start: 36, end: AGE_RANGE.max },
  ],
} as const;

export const MIN_OVR = 20;
export const MAX_OVR = 100;

export const CSV_FILENAME = "fax-player-growth.csv";
export const PNG_FILENAME = "fax-player-growth.png";

export const COHORT_COLORS: Record<StylePresetKey, string> = {
  hybrid: "#64748b",
  shotmaker: "#94a3b8",
  retriever: "#cbd5f5",
};

export const EMPTY_POINT: Point = { age: AGE_RANGE.min, ovr: 20 };
