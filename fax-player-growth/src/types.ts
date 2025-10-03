import type { CurveParams, Point } from "./lib/curve";

export type ParameterKey = keyof CurveParams;

export type SliderConfig = {
  key: ParameterKey;
  label: string;
  min: number;
  max: number;
  step: number;
  tooltip: string;
  format?: (value: number) => string;
};

export type StylePresetKey = "hybrid" | "shotmaker" | "retriever";

export type StylePreset = {
  key: StylePresetKey;
  label: string;
  description: string;
  params: CurveParams;
};

export type GuardrailNotice = {
  field: ParameterKey | "decline";
  message: string;
};

export type ChartPoint = Point & {
  median?: number;
  q05?: number;
  q25?: number;
  q75?: number;
  q95?: number;
  band50Low?: number;
  band50Span?: number;
  band90Low?: number;
  band90Span?: number;
};

export type CurveInsights = {
  peakOvr: number;
  peakAge: number;
  peakWindowMonths: number;
  ageAt95: number;
  ageAt90: number;
  primeSlope: number;
  declineSlope: number;
};

export type UrlState = {
  params: CurveParams;
  showFanChart: boolean;
  showCohort: boolean;
  preset: StylePresetKey;
};
