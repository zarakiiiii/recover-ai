import React from 'react';
import {
  ActivityIcon,
  DatabaseIcon,
  ShieldIcon,
  SlidersIcon,
  SparklesIcon,
  ZapIcon,
} from './Icons';

interface SidebarProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ activeTab, onTabChange }) => {
  return (
    <aside className="app-sidebar">
      <div className="sidebar-brand">
        <div className="brand-logo-glow">
          <div className="brand-icon-box">
            <ZapIcon size={22} color="#06B6D4" />
          </div>
        </div>
        <div className="brand-text">
          <h1 className="brand-title">
            Recover<span className="text-cyan">AI</span>
          </h1>
          <span className="brand-badge">AUTONOMOUS OPS</span>
        </div>
      </div>

      <nav className="sidebar-nav">
        <div className="nav-section-label">OPERATIONS</div>
        <button
          className={`nav-item ${activeTab === 'operations' ? 'active' : ''}`}
          onClick={() => onTabChange('operations')}
        >
          <ZapIcon size={18} className="nav-icon" />
          <span className="nav-label">Recovery Operations</span>
          <span className="nav-live-dot" title="Live System Active" />
        </button>

        <button
          className={`nav-item ${activeTab === 'policy' ? 'active' : ''}`}
          onClick={() => onTabChange('policy')}
        >
          <ShieldIcon size={18} className="nav-icon" />
          <span className="nav-label">Policy Guardrails</span>
          <span className="nav-pill-badge">Deterministic</span>
        </button>

        <button
          className={`nav-item ${activeTab === 'analytics' ? 'active' : ''}`}
          onClick={() => onTabChange('analytics')}
        >
          <ActivityIcon size={18} className="nav-icon" />
          <span className="nav-label">Recovery Analytics</span>
        </button>

        <div className="nav-section-label">CONFIGURATION</div>
        <button
          className={`nav-item ${activeTab === 'settings' ? 'active' : ''}`}
          onClick={() => onTabChange('settings')}
        >
          <SlidersIcon size={18} className="nav-icon" />
          <span className="nav-label">Engine Config</span>
        </button>
      </nav>

      <div className="sidebar-footer">
        <div className="system-status-card">
          <div className="status-header">
            <div className="status-pulse-dot" />
            <span className="status-title">SYSTEM ONLINE</span>
          </div>
          <div className="status-details">
            <div className="status-row">
              <DatabaseIcon size={13} color="#94A3B8" />
              <span>PostgreSQL Connected</span>
            </div>
            <div className="status-row">
              <SparklesIcon size={13} color="#94A3B8" />
              <span>Mock LLM + Guardrails</span>
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
};
