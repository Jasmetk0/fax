import type React from "react";
import {
  Area,
  CartesianGrid,
  Line,
  LineChart,
  ReferenceArea,
  ReferenceDot,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { AGE_RANGE, COHORT_COLORS, REFERENCE_AGES, ZONES } from "../constants";
import type { CurveParams, Point } from "../lib/curve";
import type { ChartPoint, CurveInsights, StylePresetKey } from "../types";

export type CurveStudioProps = {
  data: ChartPoint[];
  linePoints: Point[];
  params: CurveParams;
  showFanChart: boolean;
  showCohort: boolean;
  cohortCurves: { key: StylePresetKey; label: string; points: Point[] }[];
  insights: CurveInsights;
  chartRef: React.RefObject<HTMLDivElement>;
};

const zoneFill = {
  development: "#dcfce7",
  peak: "#5eead4",
  decline1: "#fecaca",
  decline2: "#fca5a5",
  decline3: "#f87171",
} as const;

const valueAtAge = (points: Point[], age: number): number => {
  if (points.length === 0) return 0;
  const clampedAge = Math.max(points[0].age, Math.min(points[points.length - 1].age, age));
  for (let index = 0; index < points.length - 1; index += 1) {
    const left = points[index];
    const right = points[index + 1];
    if (clampedAge >= left.age && clampedAge <= right.age) {
      const span = right.age - left.age;
      const ratio = span === 0 ? 0 : (clampedAge - left.age) / span;
      return left.ovr + ratio * (right.ovr - left.ovr);
    }
  }
  return points[points.length - 1].ovr;
};

const formatSlopeLabel = (value: number, prefix: string) =>
  `${prefix}${value >= 0 ? "+" : ""}${value.toFixed(2)} OVR/yr`;

export function CurveStudio({
  data,
  linePoints,
  params,
  showFanChart,
  showCohort,
  cohortCurves,
  insights,
  chartRef,
}: CurveStudioProps) {
  const developmentEnd = Math.min(22, params.peakAge - Math.max(params.peakRetention / 2, 0.25));
  const peakStart = params.peakAge - params.peakRetention / 2;
  const peakEnd = params.peakAge + params.peakRetention / 2;

  const primeStart = 16;
  const primeEnd = 22;
  const declineStart = 33;
  const declineEnd = 36;

  const primeLine = {
    x1: primeStart,
    x2: primeEnd,
    y1: valueAtAge(linePoints, primeStart),
    y2: valueAtAge(linePoints, primeEnd),
  };

  const declineLine = {
    x1: declineStart,
    x2: declineEnd,
    y1: valueAtAge(linePoints, declineStart),
    y2: valueAtAge(linePoints, declineEnd),
  };

  const peakPoint = linePoints.reduce((best, current) => (current.ovr > best.ovr ? current : best), linePoints[0]);
  const age95Value = valueAtAge(linePoints, insights.ageAt95);
  const age90Value = valueAtAge(linePoints, insights.ageAt90);

  return (
    <div ref={chartRef} className="relative h-[520px] w-full rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 20, right: 32, left: 16, bottom: 20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#cbd5f5" />
          <XAxis
            dataKey="age"
            type="number"
            domain={[AGE_RANGE.min, AGE_RANGE.max]}
            tickFormatter={(value) => value.toFixed(0)}
            label={{ value: "Age", position: "insideBottomRight", offset: -10 }}
          />
          <YAxis
            domain={[20, 100]}
            tickFormatter={(value) => value.toFixed(0)}
            label={{ value: "OVR", angle: -90, position: "insideLeft", offset: 10 }}
          />
          <Tooltip
            formatter={(value: number) => `${value.toFixed(2)} OVR`}
            labelFormatter={(label) => `Age ${Number(label).toFixed(2)}`}
          />

          {developmentEnd > AGE_RANGE.min && (
            <ReferenceArea
              x1={AGE_RANGE.min}
              x2={developmentEnd}
              y1={20}
              y2={100}
              fill={zoneFill.development}
              fillOpacity={0.35}
              strokeOpacity={0}
            />
          )}

          {peakEnd > peakStart && (
            <ReferenceArea
              x1={peakStart}
              x2={peakEnd}
              y1={20}
              y2={100}
              fill={zoneFill.peak}
              fillOpacity={0.35}
              strokeOpacity={0}
            />
          )}

          {ZONES.decline.map((zone, index) => (
            <ReferenceArea
              key={zone.color}
              x1={zone.start}
              x2={zone.end}
              y1={20}
              y2={100}
              fill={zoneFill[zone.color as keyof typeof zoneFill]}
              fillOpacity={0.2 + index * 0.1}
              strokeOpacity={0}
            />
          ))}

          {showFanChart && (
            <>
              <Area
                type="monotone"
                dataKey="band90Low"
                stackId="range90"
                stroke="none"
                fill="none"
                isAnimationActive={false}
              />
              <Area
                type="monotone"
                dataKey="band90Span"
                stackId="range90"
                stroke="none"
                fill="#0ea5e9"
                fillOpacity={0.15}
                isAnimationActive={false}
              />
              <Area
                type="monotone"
                dataKey="band50Low"
                stackId="range50"
                stroke="none"
                fill="none"
                isAnimationActive={false}
              />
              <Area
                type="monotone"
                dataKey="band50Span"
                stackId="range50"
                stroke="none"
                fill="#14b8a6"
                fillOpacity={0.25}
                isAnimationActive={false}
              />
              <Line type="monotone" dataKey="median" stroke="#0f172a" strokeWidth={2} dot={false} isAnimationActive={false} />
            </>
          )}

          {!showFanChart && <Line type="monotone" dataKey="ovr" stroke="#0f172a" strokeWidth={2} dot={false} />}

          {showCohort &&
            cohortCurves.map((cohort) => (
              <Line
                key={cohort.key}
                type="monotone"
                data={cohort.points}
                dataKey="ovr"
                stroke={COHORT_COLORS[cohort.key]}
                strokeDasharray="4 4"
                strokeWidth={1}
                dot={false}
                opacity={0.6}
                isAnimationActive={false}
              />
            ))}

          {REFERENCE_AGES.map((age) => (
            <ReferenceLine key={age} x={age} stroke="#94a3b8" strokeDasharray="4 4" ifOverflow="extendDomain" />
          ))}

          <ReferenceDot
            x={peakPoint.age}
            y={peakPoint.ovr}
            r={5}
            fill="#0f172a"
            stroke="white"
            strokeWidth={2}
            label={{ value: "Peak OVR", position: "top", fill: "#0f172a", fontSize: 12 }}
          />

          <ReferenceDot
            x={insights.ageAt95}
            y={age95Value}
            r={4}
            fill="#0284c7"
            stroke="white"
            strokeWidth={2}
            label={{ value: "Age @ 95%", position: "top", fill: "#0284c7", fontSize: 12 }}
          />

          <ReferenceDot
            x={insights.ageAt90}
            y={age90Value}
            r={4}
            fill="#0d9488"
            stroke="white"
            strokeWidth={2}
            label={{ value: "Age @ 90%", position: "top", fill: "#0d9488", fontSize: 12 }}
          />

          <ReferenceLine
            x1={primeLine.x1}
            y1={primeLine.y1}
            x2={primeLine.x2}
            y2={primeLine.y2}
            stroke="#16a34a"
            strokeWidth={2}
            label={{ value: formatSlopeLabel(insights.primeSlope, "+"), position: "insideTop", fill: "#15803d" }}
          />

          <ReferenceLine
            x1={declineLine.x1}
            y1={declineLine.y1}
            x2={declineLine.x2}
            y2={declineLine.y2}
            stroke="#ef4444"
            strokeWidth={2}
            label={{ value: formatSlopeLabel(insights.declineSlope, ""), position: "insideBottom", fill: "#b91c1c" }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
