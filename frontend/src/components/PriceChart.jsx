import { useMemo, useState } from "react";

const WIDTH = 720;
const HEIGHT = 260;
const PAD = { top: 16, right: 16, bottom: 28, left: 56 };

function formatDate(iso) {
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", { day: "2-digit", month: "short" });
}

export default function PriceChart({ prices }) {
  const [hoverIdx, setHoverIdx] = useState(null);

  const { points, yTicks, minY, maxY } = useMemo(() => {
    if (!prices || prices.length === 0) {
      return { points: [], yTicks: [], minY: 0, maxY: 0 };
    }
    const closes = prices.map((p) => p.close);
    const minY = Math.min(...closes);
    const maxY = Math.max(...closes);
    const span = maxY - minY || 1;
    const innerW = WIDTH - PAD.left - PAD.right;
    const innerH = HEIGHT - PAD.top - PAD.bottom;

    const points = prices.map((p, i) => {
      const x = PAD.left + (i / Math.max(prices.length - 1, 1)) * innerW;
      const y = PAD.top + innerH - ((p.close - minY) / span) * innerH;
      return { x, y, ...p };
    });

    const yTicks = [0, 0.25, 0.5, 0.75, 1].map((t) => ({
      value: minY + t * span,
      y: PAD.top + innerH - t * innerH,
    }));

    return { points, yTicks, minY, maxY };
  }, [prices]);

  if (!prices || prices.length === 0) {
    return <p className="empty-note">No price history for this ticker.</p>;
  }

  const linePath = points
    .map((p, i) => `${i === 0 ? "M" : "L"}${p.x.toFixed(2)},${p.y.toFixed(2)}`)
    .join(" ");

  const hovered = hoverIdx !== null ? points[hoverIdx] : null;

  function handleMove(e) {
    const svg = e.currentTarget;
    const rect = svg.getBoundingClientRect();
    const scaleX = WIDTH / rect.width;
    const mouseX = (e.clientX - rect.left) * scaleX;
    let closest = 0;
    let closestDist = Infinity;
    points.forEach((p, i) => {
      const d = Math.abs(p.x - mouseX);
      if (d < closestDist) {
        closestDist = d;
        closest = i;
      }
    });
    setHoverIdx(closest);
  }

  return (
    <div className="price-chart">
      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        role="img"
        aria-label="Price history chart"
        onMouseMove={handleMove}
        onMouseLeave={() => setHoverIdx(null)}
      >
        {yTicks.map((t, i) => (
          <g key={i}>
            <line
              x1={PAD.left}
              x2={WIDTH - PAD.right}
              y1={t.y}
              y2={t.y}
              stroke="var(--gridline)"
              strokeWidth="1"
            />
            <text x={PAD.left - 8} y={t.y + 4} textAnchor="end" className="chart-tick tabular">
              {t.value.toFixed(0)}
            </text>
          </g>
        ))}

        <line
          x1={PAD.left}
          x2={WIDTH - PAD.right}
          y1={HEIGHT - PAD.bottom}
          y2={HEIGHT - PAD.bottom}
          stroke="var(--baseline)"
          strokeWidth="1"
        />

        <path d={linePath} fill="none" stroke="var(--series-blue)" strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />

        {hovered && (
          <>
            <line
              x1={hovered.x}
              x2={hovered.x}
              y1={PAD.top}
              y2={HEIGHT - PAD.bottom}
              stroke="var(--text-muted)"
              strokeWidth="1"
              strokeDasharray="3 3"
            />
            <circle cx={hovered.x} cy={hovered.y} r="4" fill="var(--surface-1)" stroke="var(--series-blue)" strokeWidth="2" />
          </>
        )}
      </svg>

      {hovered && (
        <div
          className="chart-tooltip"
          style={{ left: `${(hovered.x / WIDTH) * 100}%` }}
        >
          <div className="chart-tooltip__date">{formatDate(hovered.date)}</div>
          <div className="chart-tooltip__value tabular">${hovered.close.toFixed(2)}</div>
        </div>
      )}

      <div className="price-chart__range">
        <span>{formatDate(prices[0].date)}</span>
        <span>{formatDate(prices[prices.length - 1].date)}</span>
      </div>
    </div>
  );
}
