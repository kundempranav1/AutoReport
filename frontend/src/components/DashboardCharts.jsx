import React from 'react';
import Plot from 'react-plotly.js';

// DashboardCharts — renders a Plotly chart per entry in `charts`.
// If a chart contains `forecast_meta`, it also renders a styled tabular prediction list.
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
      {charts.map((chart, i) => {
        const isForecast = !!chart.forecast_meta;
        
        return (
          <div 
            className={`chart-card ${isForecast ? 'forecast-card' : ''}`} 
            key={i}
            style={isForecast ? { gridColumn: '1 / -1' } : {}}
          >
            <h4>{chart.title || `Chart ${i + 1}`}</h4>
            
            <div className={isForecast ? 'forecast-layout' : 'standard-layout'}>
              <div className="chart-plot-container" style={{ flex: 2, minWidth: '300px' }}>
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

              {isForecast && (
                <div className="forecast-table-container" style={{ flex: 1, minWidth: '260px', padding: '12px' }}>
                  <h5 style={{ marginBottom: '10px', fontSize: '13px', color: '#4b5563' }}>
                    📊 Projected Future Estimates
                  </h5>
                  <table className="forecast-table">
                    <thead>
                      <tr>
                        <th>Period</th>
                        <th>Projected</th>
                        <th>Range (90% CI)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {chart.forecast_meta.predictions.map((p, idx) => (
                        <tr key={idx}>
                          <td className="period-cell"><strong>{p.period}</strong></td>
                          <td className="value-cell">{p.value.toLocaleString()}</td>
                          <td className="range-cell">{p.lower.toLocaleString()} – {p.upper.toLocaleString()}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <p style={{ fontSize: '11px', color: '#6b7280', marginTop: '10px', fontStyle: 'italic' }}>
                    *Confidence intervals generated using linear trend regression and historical residual margins.
                  </p>
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}