import React from "react";

interface LoadingScreenProps {
  stage: string;
  detail: string;
}

export const LoadingScreen: React.FC<LoadingScreenProps> = ({ stage, detail }) => {
  return (
    <div className="loading-screen-container">
      {/* Background ambient glowing blobs */}
      <div className="blob blob-purple"></div>
      <div className="blob blob-cyan"></div>
      <div className="blob blob-orange"></div>

      {/* Glassmorphic Loader Panel */}
      <div className="glass-loader-panel">
        <div className="logo-container">
          <span className="logo-text">EduVis</span>
          <span className="logo-subtext">Studio</span>
        </div>

        {/* Pulsing loading ring */}
        <div className="pulse-loader"></div>

        <h3 className="loading-stage">{stage}</h3>
        <p className="loading-detail">{detail}</p>

        {/* Frosted Progress bar indicator */}
        <div className="progress-bar-container">
          <div className="progress-bar-fill"></div>
        </div>
      </div>
    </div>
  );
};
