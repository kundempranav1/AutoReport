// API client — wraps Axios calls to the Flask backend.
import axios from 'axios';

// Base URL falls back to relative path when served behind the same host.
const API_BASE_URL =
  process.env.REACT_APP_API_URL || 'http://localhost:5000';

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000, // dataset processing can take a while
});

// --- Upload dataset (CSV/Excel) -------------------------------------------
export async function uploadDataset(file) {
  const form = new FormData();
  form.append('file', file);
  const res = await client.post('/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data; // { file_id, filename }
}

// --- Run the full agent pipeline via SSE stream ----------------------------
// `callbacks`: { onProgress(agentIndex, done), onResult(data), onError(msg) }
export function processDataset(fileId, callbacks = {}) {
  const { onProgress, onResult, onError } = callbacks;

  return new Promise((resolve, reject) => {
    fetch(`${API_BASE_URL}/process`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ file_id: fileId }),
    }).then((response) => {
      if (!response.ok) {
        response.json().then((d) => {
          const msg = d?.error || 'Processing failed.';
          if (onError) onError(msg);
          reject(new Error(msg));
        }).catch(() => reject(new Error('Processing failed.')));
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      function read() {
        reader.read().then(({ done, value }) => {
          if (done) { resolve(); return; }

          buffer += decoder.decode(value, { stream: true });
          // SSE messages are separated by double newlines.
          const parts = buffer.split('\n\n');
          buffer = parts.pop(); // keep incomplete tail

          for (const part of parts) {
            const eventMatch = part.match(/^event:\s*(\S+)/m);
            const dataMatch  = part.match(/^data:\s*(.+)/m);
            if (!dataMatch) continue;

            const eventName = eventMatch ? eventMatch[1] : 'message';
            let payload;
            try { payload = JSON.parse(dataMatch[1]); } catch { continue; }

            if (eventName === 'progress' && onProgress) {
              onProgress(payload.agent, !!payload.done);
            } else if (eventName === 'result') {
              if (onResult) onResult(payload);
              resolve(payload);
            } else if (eventName === 'error') {
              const msg = payload?.error || 'Processing failed.';
              if (onError) onError(msg);
              reject(new Error(msg));
            }
          }
          read();
        }).catch((err) => {
          if (onError) onError(err.message);
          reject(err);
        });
      }
      read();
    }).catch((err) => {
      if (onError) onError(err.message);
      reject(err);
    });
  });
}

// --- Fetch cached dashboard for an uploaded file ---------------------------
export async function getDashboard(fileId) {
  const res = await client.get('/dashboard', { params: { file_id: fileId } });
  return res.data;
}

// --- Get PDF report metadata / URL -----------------------------------------
export async function getReport(fileId) {
  const res = await client.get('/report', { params: { file_id: fileId } });
  return res.data;
}

// --- Ask the chatbot a question about the dataset --------------------------
export async function askChatbot(fileId, question) {
  const res = await client.post('/chat', { file_id: fileId, question });
  return res.data; // { answer }
}
