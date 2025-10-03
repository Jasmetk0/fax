import type { CurveInsights } from "../types";

export type HeaderStatsProps = {
  insights: CurveInsights;
};

const StatTile = ({ label, value }: { label: string; value: string }) => (
  <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
    <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
    <p className="mt-2 text-2xl font-semibold text-slate-800">{value}</p>
  </div>
);

export function HeaderStats({ insights }: HeaderStatsProps) {
  return (
    <section className="grid gap-4 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-7">
      <StatTile label="Peak OVR" value={insights.peakOvr.toFixed(2)} />
      <StatTile label="Peak age" value={`${insights.peakAge.toFixed(1)} yrs`} />
      <StatTile label="Peak window" value={`${insights.peakWindowMonths} months`} />
      <StatTile label="Age @ 95% peak" value={`${insights.ageAt95.toFixed(1)} yrs`} />
      <StatTile label="Age @ 90% peak" value={`${insights.ageAt90.toFixed(1)} yrs`} />
      <StatTile
        label="Prime velocity"
        value={`${insights.primeSlope >= 0 ? "+" : ""}${insights.primeSlope.toFixed(2)} OVR/yr`}
      />
      <StatTile label="Decline velocity" value={`${insights.declineSlope.toFixed(2)} OVR/yr`} />
    </section>
  );
}
