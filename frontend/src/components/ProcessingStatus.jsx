import React from 'react';

// The ordered list of the 6 agents that run during a process call.
// `currentIndex` is -1 before processing starts, N while agent N runs, and
// `agents.length` after the chain has finished.
const AGENT_LABELS = [
  { key: 'clean',   label: 'Data Cleaning Agent',         desc: 'Filling missing values, dropping duplicates' },
  { key: 'analysis', label: 'Analysis Agent',            desc: 'Statistical summary, correlations, types' },
  { key: 'kpi',     label: 'KPI Generation Agent',       desc: 'Top-level metrics' },
  { key: 'dash',    label: 'Dashboard Generation Agent', desc: 'Bar, Line, Pie, Histogram charts' },
  { key: 'report',  label: 'Report Generation Agent',    desc: 'Professional PDF report' },
  { key: 'chat',    label: 'Chatbot for Dataset Q&A',    desc: 'LangChain + OpenAI assistant' },
];

export default function ProcessingStatus({ currentIndex, error }) {
  return (
    <section className="section" id="status">
      <div className="card">
        <h3 className="card-title">
          <span className="icon">⚙️</span> Processing Pipeline
        </h3>

        <div className="status-list">
          {AGENT_LABELS.map((agent, i) => {
            const state =
              error && i === currentIndex
                ? 'error'
                : i < currentIndex
                ? 'done'
                : i === currentIndex
                ? 'active'
                : 'pending';

            return (
              <div key={agent.key} className={`status-item ${state}`}>
                <span className="status-dot" />
                <span className="status-label">{agent.label}</span>
                <span className="status-meta">{agent.desc}</span>
              </div>
            );
          })}
        </div>

        {error && (
          <div className="alert error" style={{ marginTop: 14 }}>
            ⚠️ {error}
          </div>
        )}
      </div>
    </section>
  );
}