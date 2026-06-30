import React from 'react';

// Top navigation bar — kept simple, single brand block + section anchors.
export default function Navbar() {
  return (
    <header className="navbar">
      <div className="navbar-inner">
        <div className="brand">
          <div className="brand-logo">AR</div>
          <span>AutoReport AI</span>
        </div>
        <nav className="nav-links">
          <a href="#upload">Upload</a>
          <a href="#status">Processing</a>
          <a href="#dashboard">Dashboard</a>
          <a href="#chatbot">Chatbot</a>
        </nav>
      </div>
    </header>
  );
}