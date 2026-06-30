import React, { useRef, useState } from 'react';

// UploadSection — handles file picking, drag-and-drop, and upload.
// Emits `onUploaded(fileInfo)` once the file has reached the backend.
export default function UploadSection({ onUploaded, disabled }) {
  const inputRef = useRef(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [fileMeta, setFileMeta] = useState(null);

  const acceptTypes = ['.csv', '.xlsx', '.xls'];

  function validateFile(file) {
    if (!file) return 'Please select a file.';
    const name = file.name.toLowerCase();
    if (!acceptTypes.some((ext) => name.endsWith(ext))) {
      return 'Unsupported file. Only CSV or Excel files are allowed.';
    }
    return null;
  }

  async function upload(file) {
    const err = validateFile(file);
    if (err) {
      setError(err);
      return;
    }
    setError('');
    setUploading(true);
    try {
      // Lazy import to keep the component snappy.
      const { uploadDataset } = await import('../api/client');
      const result = await uploadDataset(file);
      const meta = { ...result, originalName: file.name, size: file.size };
      setFileMeta(meta);
      onUploaded(meta);
    } catch (e) {
      const msg =
        e?.response?.data?.error || e.message || 'Upload failed.';
      setError(msg);
    } finally {
      setUploading(false);
    }
  }

  function onFileChange(e) {
    const file = e.target.files?.[0];
    if (file) upload(file);
  }

  function onDrop(e) {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) upload(file);
  }

  return (
    <section className="section" id="upload">
      <div className="card">
        <h3 className="card-title">
          <span className="icon">📤</span> Upload Dataset
        </h3>

        <div
          className={`upload-area ${dragging ? 'dragging' : ''}`}
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          onClick={() => inputRef.current?.click()}
          role="button"
          tabIndex={0}
        >
          <div style={{ fontSize: 32 }}>📁</div>
          <p>
            <strong>Click to choose</strong> or drag &amp; drop your CSV / Excel file here
          </p>
          <p style={{ fontSize: 12 }}>Accepted formats: .csv, .xlsx, .xls</p>

          <input
            ref={inputRef}
            type="file"
            accept={acceptTypes.join(',')}
            className="upload-input"
            onChange={onFileChange}
            disabled={uploading || disabled}
          />

          {fileMeta && (
            <span className="file-pill">
              ✅ {fileMeta.originalName} uploaded
            </span>
          )}
        </div>

        {uploading && <div className="alert info">Uploading dataset…</div>}
        {error && <div className="alert error">{error}</div>}
      </div>
    </section>
  );
}