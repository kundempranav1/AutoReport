import React from 'react';

// ProcessControls — the single button that kicks off the entire agent chain.
export default function ProcessControls({
  fileMeta,
  isProcessing,
  onProcess,
}) {
  const ready = !!fileMeta && !isProcessing;

  return (
    <div className="action-row" style={{ marginTop: 0 }}>
      <button
        className="btn btn-primary"
        onClick={onProcess}
        disabled={!ready}
      >
        {isProcessing ? '⏳ Processing…' : '🚀 Run AI Agents'}
      </button>
      {!fileMeta && (
        <span style={{ color: 'var(--muted)', fontSize: 13, alignSelf: 'center' }}>
          Upload a dataset first to enable processing.
        </span>
      )}
    </div>
  );
}