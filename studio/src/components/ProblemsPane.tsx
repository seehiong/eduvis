import React, { useState } from "react";

interface ProblemsPaneProps {
  warnings: string[];
}

export const ProblemsPane: React.FC<ProblemsPaneProps> = ({ warnings }) => {
  const [isOpen, setIsOpen] = useState(false);

  if (warnings.length === 0) {
    return (
      <div style={{
        position: "fixed",
        bottom: 0,
        left: "80px", // align with sidebar
        right: 0,
        background: "var(--bg-panel)",
        borderTop: "1px solid var(--border-color)",
        padding: "8px 16px",
        display: "flex",
        alignItems: "center",
        zIndex: 50,
      }}>
        <div style={{ display: "flex", gap: "8px", alignItems: "center", color: "var(--success)", fontSize: "0.85rem" }}>
          <svg stroke="currentColor" fill="none" strokeWidth="2" viewBox="0 0 24 24" height="1em" width="1em">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
            <polyline points="22 4 12 14.01 9 11.01"></polyline>
          </svg>
          No Pedagogical Diagnostics
        </div>
      </div>
    );
  }

  return (
    <div style={{
      position: "fixed",
      bottom: 0,
      left: "80px",
      right: 0,
      background: "var(--bg-panel)",
      borderTop: "1px solid var(--border-color)",
      zIndex: 50,
      display: "flex",
      flexDirection: "column",
    }}>
      {/* Header / Toggle bar */}
      <div 
        onClick={() => setIsOpen(!isOpen)}
        style={{
          padding: "8px 16px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          cursor: "pointer",
          borderBottom: isOpen ? "1px solid var(--border-color)" : "none",
        }}
      >
        <div style={{ display: "flex", gap: "8px", alignItems: "center", color: "var(--warning)", fontSize: "0.85rem" }}>
          <svg stroke="currentColor" fill="none" strokeWidth="2" viewBox="0 0 24 24" height="1em" width="1em">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
            <line x1="12" y1="9" x2="12" y2="13"></line>
            <line x1="12" y1="17" x2="12.01" y2="17"></line>
          </svg>
          {warnings.length} Pedagogical Diagnostic{warnings.length > 1 ? "s" : ""}
        </div>
        <div>
          <svg 
            stroke="currentColor" 
            fill="none" 
            strokeWidth="2" 
            viewBox="0 0 24 24" 
            height="1em" 
            width="1em"
            style={{ transform: isOpen ? "rotate(180deg)" : "rotate(0deg)", transition: "transform 0.2s" }}
          >
            <polyline points="6 9 12 15 18 9"></polyline>
          </svg>
        </div>
      </div>

      {/* Expanded Content */}
      {isOpen && (
        <div style={{ maxHeight: "250px", overflowY: "auto", padding: "8px 0" }}>
          <ul style={{ margin: 0, padding: 0, listStyle: "none" }}>
            {warnings.map((warning, idx) => {
              const isError = warning.toLowerCase().includes("error");
              return (
                <li key={idx} style={{ 
                  padding: "6px 16px", 
                  fontSize: "0.8rem", 
                  color: "var(--text)",
                  borderBottom: "1px solid rgba(255,255,255,0.05)",
                  display: "flex",
                  gap: "8px",
                  alignItems: "flex-start"
                }}>
                  <span style={{ color: isError ? "var(--error)" : "var(--warning)", marginTop: "2px" }}>
                    <svg stroke="currentColor" fill="none" strokeWidth="2" viewBox="0 0 24 24" height="1em" width="1em">
                      <circle cx="12" cy="12" r="10"></circle>
                      <line x1="12" y1="8" x2="12" y2="12"></line>
                      <line x1="12" y1="16" x2="12.01" y2="16"></line>
                    </svg>
                  </span>
                  <span style={{ lineHeight: "1.4", fontFamily: "monospace" }}>{warning}</span>
                </li>
              )
            })}
          </ul>
        </div>
      )}
    </div>
  );
};
