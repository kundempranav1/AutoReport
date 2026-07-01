import React, { useEffect, useState } from 'react';

import Navbar from './components/Navbar';
import UploadSection from './components/UploadSection';
import ProcessControls from './components/ProcessControls';
import ProcessingStatus from './components/ProcessingStatus';
import KpiCards from './components/KpiCards';
import DashboardCharts from './components/DashboardCharts';
import ReportDownload from './components/ReportDownload';
import Chatbot from './components/Chatbot';

import { processDataset } from './api/client';

// Top-level orchestrator. Owns the shared state — uploaded file metadata,
// processing status, and the most recent pipeline result.
export default function App() {
  const [fileMeta, setFileMeta] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentAgent, setCurrentAgent] = useState(-1); // -1 = idle
  const [error, setError] = useState('');
  const [result, setResult] = useState(null); // full pipeline result

  // When a result lands, reset the active agent pointer to "all done".
  useEffect(() => {
    if (result && !isProcessing) {
      setCurrentAgent(6);
    }
  }, [result, isProcessing]);

  async function onProcess() {
    if (!fileMeta) return;
    setError('');
    setResult(null);
    setIsProcessing(true);
    setCurrentAgent(0);

    try {
      await processDataset(fileMeta.file_id, {
        onProgress: (agentIndex, done) => {
          // Advance to the next agent when the current one starts,
          // or mark current as done. The UI treats index == currentAgent
          // as "active" and index < currentAgent as "done".
          setCurrentAgent(done ? agentIndex + 1 : agentIndex);
        },
        onResult: (data) => {
          setResult(data);
        },
        onError: (msg) => {
          setError(msg);
        },
      });
    } catch (e) {
      // onError already handled above; guard against unhandled rejections.
      if (!error) {
        const msg = e?.message || 'Processing failed.';
        setError(msg);
      }
    } finally {
      setIsProcessing(false);
      setCurrentAgent(6); // mark all done
    }
  }

  return (
    <div className="app-shell">
      <Navbar />

      <main className="main-container">
        <section className="hero">
          <h1>
            <span className="accent">AutoReport AI</span> – Autonomous
            Dashboard Generation Agent
          </h1>
          <p>
            Upload a CSV or Excel dataset and let our six AI agents clean,
            analyze, generate KPIs, build charts, produce a PDF report and
            answer your questions — automatically.
          </p>
        </section>

        <UploadSection onUploaded={setFileMeta} disabled={isProcessing} />

        <ProcessControls
          fileMeta={fileMeta}
          isProcessing={isProcessing}
          onProcess={onProcess}
        />

        <ProcessingStatus
          currentIndex={isProcessing ? currentAgent : result ? 6 : -1}
          error={error}
        />

        {error && (
          <div className="alert error" style={{ marginBottom: 24 }}>
            ⚠️ {error}
          </div>
        )}

        <section className="section" id="dashboard">
          <div className="card" style={{ marginBottom: 18 }}>
            <h3 className="card-title">
              <span className="icon">📊</span> Key Performance Indicators
            </h3>
          </div>
          <KpiCards kpis={result?.kpis} />
        </section>

        {result && (
          <>
            {/* Filter charts to display in separate dashboard sections */}
            {(() => {
              const allCharts = result.charts || [];
              const standardCharts = allCharts.filter(c => !c.forecast_meta);
              const forecastCharts = allCharts.filter(c => !!c.forecast_meta);

              return (
                <>
                  {standardCharts.length > 0 && (
                    <section className="section">
                      <div className="card" style={{ marginBottom: 18 }}>
                        <h3 className="card-title">
                          <span className="icon">📊</span> Historical Analytics & Visualisations
                        </h3>
                      </div>
                      <DashboardCharts charts={standardCharts} />
                    </section>
                  )}

                  {forecastCharts.length > 0 && (
                    <section className="section" id="forecasting">
                      <div className="card" style={{ marginBottom: 18 }}>
                        <h3 className="card-title">
                          <span className="icon">🔮</span> Future Trend Forecasting Dashboard
                        </h3>
                      </div>
                      <DashboardCharts charts={forecastCharts} />
                    </section>
                  )}
                </>
              );
            })()}
          </>
        )}

        <ReportDownload
          reportUrl={result?.report_url}
          filename={result?.report_filename}
        />

        <div style={{ height: 18 }} />

        <Chatbot fileMeta={fileMeta} enabled={!!result && !error} />
      </main>

      <footer className="footer">
        Built with React · Flask · LangChain · OpenAI — AutoReport AI © {new Date().getFullYear()}
      </footer>
    </div>
  );
}