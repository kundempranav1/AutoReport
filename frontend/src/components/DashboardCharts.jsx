import React from 'react';
import Plot from 'react-plotly.js';

// DashboardCharts — renders a Plotly chart per entry in `charts`.
// Each chart from the backend comes pre-shaped as a Plotly figure
// ({ data, layout }), so we just hand it straight to react-plotly.js.
export default function DashboardCharts({ charts }) {
  if (!charts || charts.length === 0) {
    return (
      <div className="card empty-state">
        <div className="empty-state-icon">📈</div>
        Charts will appear here once the pipeline runs.
      </div>
    );
  }

  return (
    <div className="chart-grid">
      {charts.map((chart, i) => (
        <div className="chart-card" key={i}>
          <h4>{chart.title || `Chart ${i + 1}`}</h4>
          <Plot
            data={chart.data}
            layout={{
              autosize: true,
              margin: { l: 40, r: 20, t: 10, b: 40 },
              paper_bgcolor: '#ffffff',
              plot_bgcolor: '#ffffff',
              font: { family: 'inherit', color: '#1f2937', size: 12 },
              ...(chart.layout || {}),
            }}
            config={{ displayModeBar: false, responsive: true }}
            useResizeHandler
            style={{ width: '100%', height: 320 }}
          />
        </div>
      ))}
    </div>
  );
}