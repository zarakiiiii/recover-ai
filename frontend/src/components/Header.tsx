import React from 'react';
import { RefreshCwIcon, ShieldIcon } from './Icons';

interface HeaderProps {
  lastUpdated: Date | null;
  isLoading: boolean;
  onRefresh: () => void;
}

export const Header: React.FC<HeaderProps> = ({ lastUpdated, isLoading, onRefresh }) => {
  const formatSyncTime = (date: Date | null) => {
    if (!date) return 'Syncing...';
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  return (
    <header className="dashboard-header">
      <div className="header-left">
        <div className="header-title-row">
          <h1 className="header-title">Recovery Operations</h1>
          <span className="live-pill">
            <span className="live-dot" />
            LIVE OPS
          </span>
        </div>
        <p className="header-subtitle">
          Real-time failed payment recovery: evaluating deterministic risk scoring, strict policy authorizations, and AI-guided customer recovery.
        </p>
      </div>

      <div className="header-right">
        <div className="sync-meta">
          <span className="sync-label">Last synced</span>
          <span className="sync-time">{formatSyncTime(lastUpdated)}</span>
        </div>

        <button
          className="btn-refresh"
          onClick={onRefresh}
          disabled={isLoading}
          title="Refresh real-time data from PostgreSQL"
        >
          <RefreshCwIcon size={16} spinning={isLoading} />
          <span>{isLoading ? 'Refreshing...' : 'Refresh'}</span>
        </button>

        <div className="guardrail-indicator" title="Deterministic Guardrails Active">
          <ShieldIcon size={16} color="#10B981" />
          <span>Guardrails Enforced</span>
        </div>
      </div>
    </header>
  );
};
