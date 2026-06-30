import React from 'react';

// KPI cards grid. Falls back gracefully when the backend hasn't returned
// data yet (e.g. before processing has been triggered).
export default function KpiCards({ kpis }) {
  if (!kpis || Object.keys(kpis).length === 0) {
    return (
      <div className="card empty-state">
        <div className="empty-state-icon">📊</div>
        KPIs will appear here once the pipeline runs.
      </div>
    );
  }

  const entries = Object.entries(kpis);

  return (
    <div className="kpi-grid">
      {entries.map(([label, value], i) => (
        <div
          key={label}
          className={`kpi-card ${i === 0 ? 'accent' : ''}`}
        >
          <div className="kpi-label">{label}</div>
          <div className="kpi-value">{formatValue(value)}</div>
        </div>
      ))}
    </div>
  );
}

// Tiny formatter — keeps long floats readable.
function formatValue(v) {
  if (v === null || v === undefined) return '—';
  if (typeof v === 'number') {
    if (Number.isInteger(v)) return v.toLocaleString();
    const abs = Math.abs(v);
    if (abs >= 1000) return v.toLocaleString(undefined, { maximumFractionDigits: 2 });
    return Number(v.toFixed(3)).toString();
  }
  return String(v);
}