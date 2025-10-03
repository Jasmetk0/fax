export function ZonesLegend() {
  const items = [
    { label: "Development", className: "bg-development text-slate-800" },
    { label: "Peak window", className: "bg-peak text-slate-800" },
    { label: "Decline 28–32", className: "bg-decline1 text-slate-800" },
    { label: "Decline 33–36", className: "bg-decline2 text-slate-800" },
    { label: "Decline 37+", className: "bg-decline3 text-white" },
  ];
  return (
    <div className="flex flex-wrap gap-3 text-sm">
      {items.map((item) => (
        <span key={item.label} className={`flex items-center gap-2 rounded-full px-3 py-1 ${item.className}`}>
          <span className="h-2 w-2 rounded-full bg-white/80" />
          {item.label}
        </span>
      ))}
    </div>
  );
}
