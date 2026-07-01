import React from 'react';
import Plot from 'react-plotly.js';

// DashboardCharts — renders all Plotly charts returned by the pipeline.
// Forecast charts (those carrying forecast_meta) span full width and
// show a prediction table beside the chart.
export default function DashboardCharts({ charts }) {
  if (!charts || charts.length === 0) {
    return (
      <div className="card empty-state">
        <div className="empty-state-icon">📈</div>
        <p style={{ color: '#6b7280', marginTop: 8 }}>
          Charts will appear here once the pipeline runs.
        </p>
      </div>
    );
  }

  return (
    <div className="chart-grid">
      {charts.map((chart, i) => {
        const isForecast = !!chart.forecast_meta;
        const meta       = chart.forecast_meta || {};
        const isSales    = meta.is_sales;
        const dir        = meta.trend_direction;    // 'Upward' | 'Downward'
        const badge      = chart.badge;             // '📈 Upward Trend' etc.

        return (
          <div
            className={`chart-card ${isForecast ? 'forecast-card' : ''}`}
            key={i}
            style={isForecast ? { gridColumn: '1 / -1' } : {}}
          >
            {/* ── Forecast header badges ── */}
            {isForecast && (
              <div className="forecast-header">
                <div className="forecast-badge">
                  {isSales ? '💰 Sales Forecast' : '🔮 Future Trend Forecast'}
                </div>
                {badge && (
                  <div className={`trend-badge ${dir === 'Upward' ? 'trend-up' : 'trend-down'}`}>
                    {badge}
                  </div>
                )}
              </div>
            )}

            <h4>{chart.title || `Chart ${i + 1}`}</h4>

            {/* ── Layout: chart + optional table ── */}
            <div className={isForecast ? 'forecast-layout' : 'standard-layout'}>

              {/* Chart */}
              <div style={{ flex: 2, minWidth: 300 }}>
                <Plot
                  data={chart.data}
                  layout={{
                    autosize: true,
                    margin: { l: 60, r: 20, t: 20, b: 80 },
                    paper_bgcolor: 'transparent',
                    plot_bgcolor: '#f8faff',
                    font: { family: 'inherit', color: '#1f2937', size: 12 },
                    ...(chart.layout || {}),
                  }}
                  config={{ displayModeBar: false, responsive: true }}
                  useResizeHandler
                  style={{ width: '100%', height: isForecast ? 360 : 300 }}
                />
              </div>

              {/* Prediction table — only for forecast charts */}
              {isForecast && meta.predictions && meta.predictions.length > 0 && (
                <div className="forecast-table-container" style={{ flex: 1, minWidth: 280 }}>

                  {/* Summary stats */}
                  <div className="forecast-stats">
                    <div className="forecast-stat">
                      <span className="stat-label">Last Actual</span>
                      <span className="stat-value">
                        {typeof meta.last_historical_val === 'number'
                          ? meta.last_historical_val.toLocaleString(undefined, { maximumFractionDigits: 2 })
                          : meta.last_historical_val}
                      </span>
                      <span className="stat-sub">{meta.last_historical_period}</span>
                    </div>
                    <div className="forecast-stat">
                      <span className="stat-label">Next Period</span>
                      <span className={`stat-value ${dir === 'Upward' ? 'val-up' : 'val-down'}`}>
                        {typeof meta.predictions[0]?.value === 'number'
                          ? meta.predictions[0].value.toLocaleString(undefined, { maximumFractionDigits: 2 })
                          : meta.predictions[0]?.value}
                      </span>
                      <span className="stat-sub">{meta.predictions[0]?.period}</span>
                    </div>
                  </div>

                  <h5 className="table-heading">📊 6-Period Projection</h5>

                  <table className="forecast-table">
                    <thead>
                      <tr>
                        <th>Period</th>
                        <th>Forecast</th>
                        <th>90% Range</th>
                      </tr>
                    </thead>
                    <tbody>
                      {meta.predictions.map((p, idx) => (
                        <tr key={idx}>
                          <td className="period-cell">{p.period}</td>
                          <td className="value-cell">
                            {typeof p.value === 'number'
                              ? p.value.toLocaleString(undefined, { maximumFractionDigits: 2 })
                              : p.value}
                          </td>
                          <td className="range-cell">
                            {typeof p.lower === 'number' ? p.lower.toLocaleString(undefined, { maximumFractionDigits: 1 }) : p.lower}
                            {' – '}
                            {typeof p.upper === 'number' ? p.upper.toLocaleString(undefined, { maximumFractionDigits: 1 }) : p.upper}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>

                  <p className="forecast-footnote">
                    Linear regression · 90% CI · {meta.sales_col}
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