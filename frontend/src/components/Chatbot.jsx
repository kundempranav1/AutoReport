import React, { useEffect, useRef, useState } from 'react';

// Chatbot — conversation surface for asking dataset-specific questions.
// Disabled until a file is uploaded AND the pipeline has finished (the
// chatbot agent is the last one in the chain).
export default function Chatbot({ fileMeta, enabled }) {
  const [messages, setMessages] = useState([]); // {role, text, error?}
  const [input, setInput] = useState('');
  const [asking, setAsking] = useState(false);
  const scrollRef = useRef(null);

  // Auto-scroll to bottom on new messages.
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, asking]);

  async function ask() {
    const text = input.trim();
    if (!text || !enabled || asking) return;
    setInput('');

    const userMsg = { role: 'user', text };
    setMessages((prev) => [...prev, userMsg]);
    setAsking(true);

    try {
      const { askChatbot } = await import('../api/client');
      const res = await askChatbot(fileMeta.file_id, text);
      setMessages((prev) => [...prev, { role: 'assistant', text: res.answer }]);
    } catch (e) {
      const msg =
        e?.response?.data?.error ||
        e.message ||
        'Chatbot is unavailable. Please verify your OpenAI API key.';
      setMessages((prev) => [...prev, { role: 'assistant', text: msg, error: true }]);
    } finally {
      setAsking(false);
    }
  }

  function onKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      ask();
    }
  }

  return (
    <section className="section" id="chatbot">
      <div className="chatbot-card">
        <div
          ref={scrollRef}
          className="chat-window"
          style={{ maxHeight: 360 }}
        >
          {messages.length === 0 && (
            <div className="chat-empty">
              💬 Ask anything about your dataset — averages, totals, missing
              values, top categories, etc.
              <div style={{ marginTop: 8, fontSize: 12 }}>
                Example: “What is the average sales?” or “Total rows?”
              </div>
            </div>
          )}

          {messages.map((m, i) => (
            <div key={i} className={`chat-bubble ${m.error ? 'error' : m.role}`}>
              {m.text}
            </div>
          ))}

          {asking && (
            <div className="chat-bubble assistant" style={{ opacity: 0.7 }}>
              Thinking…
            </div>
          )}
        </div>

        <div className="chat-input-row">
          <input
            type="text"
            placeholder={
              enabled
                ? 'Ask a question about your dataset…'
                : 'Upload a dataset and run the pipeline to enable the chatbot.'
            }
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKey}
            disabled={!enabled || asking}
          />
          <button
            className="btn btn-primary"
            onClick={ask}
            disabled={!enabled || asking || !input.trim()}
          >
            Send
          </button>
        </div>
      </div>
    </section>
  );
}