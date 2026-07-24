const LEVEL_META = {
  scazut: { label: "Low", color: "var(--status-good)" },
  mediu: { label: "Medium", color: "var(--status-warning)" },
  ridicat: { label: "High", color: "var(--status-critical)" },
};

export default function RiskBadge({ level, value }) {
  if (!level) {
    return <span className="risk-badge risk-badge--unknown">—</span>;
  }
  const meta = LEVEL_META[level] || { label: level, color: "var(--text-muted)" };
  return (
    <span className="risk-badge" style={{ "--badge-color": meta.color }}>
      <span className="risk-badge__dot" aria-hidden="true" />
      {meta.label}
      {typeof value === "number" && (
        <span className="risk-badge__value tabular"> · {value.toFixed(1)}</span>
      )}
    </span>
  );
}
