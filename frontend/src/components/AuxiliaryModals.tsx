import React from 'react';
import {
  ActivityIcon,
  CloseIcon,
  ShieldIcon,
  SlidersIcon,
} from './Icons';

interface ModalProps {
  onClose: () => void;
}

export const PolicyRulesModal: React.FC<ModalProps> = ({ onClose }) => {
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card modal-auxiliary" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="title-with-icon">
            <ShieldIcon size={20} color="#06B6D4" />
            <div>
              <h3 className="modal-title">Deterministic Policy Guardrails</h3>
              <p className="modal-subtitle">
                Explicit mathematical rules governing autonomous payment recovery decisions.
              </p>
            </div>
          </div>
          <button className="modal-close-btn" onClick={onClose}>
            <CloseIcon size={20} />
          </button>
        </div>

        <div className="modal-body">
          <div className="rules-list">
            <div className="rule-item rule-approved">
              <div className="rule-badge-wrap">
                <span className="badge-pill badge-approved">APPROVED</span>
                <span className="rule-id">Rule #1</span>
              </div>
              <div className="rule-details">
                <h4 className="rule-name">High Recoverability &amp; Standard Value</h4>
                <p className="rule-desc">
                  Risk score ≥ 70, failure category is TRANSIENT or CUSTOMER_ACTIONABLE, and payment amount is ≤ ₹25,000. Authorized for automated payment link dispatch.
                </p>
              </div>
            </div>

            <div className="rule-item rule-warning">
              <div className="rule-badge-wrap">
                <span className="badge-pill badge-warning">HUMAN REVIEW</span>
                <span className="rule-id">Rule #2</span>
              </div>
              <div className="rule-details">
                <h4 className="rule-name">High Value Transaction Protection</h4>
                <p className="rule-desc">
                  Failed payments exceeding ₹25,000 require manual authorization from an operator to prevent unverified high-value links.
                </p>
              </div>
            </div>

            <div className="rule-item rule-danger">
              <div className="rule-badge-wrap">
                <span className="badge-pill badge-danger">BLOCKED</span>
                <span className="rule-id">Rule #3</span>
              </div>
              <div className="rule-details">
                <h4 className="rule-name">Non-Recoverable Security &amp; Auth Failures</h4>
                <p className="rule-desc">
                  Failures due to AUTHENTICATION_FAILED (3DS/OTP failures) or fraud risk are strictly blocked from automated retries.
                </p>
              </div>
            </div>

            <div className="rule-item rule-neutral">
              <div className="rule-badge-wrap">
                <span className="badge-pill badge-stopped">STOPPED</span>
                <span className="rule-id">Rule #4</span>
              </div>
              <div className="rule-details">
                <h4 className="rule-name">Maximum Retry Enforcement</h4>
                <p className="rule-desc">
                  Any case reaching 3 previous recovery attempts without successful customer settlement is permanently closed.
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className="modal-footer">
          <button className="btn-primary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export const AnalyticsModal: React.FC<ModalProps> = ({ onClose }) => {
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card modal-auxiliary" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="title-with-icon">
            <ActivityIcon size={20} color="#10B981" />
            <div>
              <h3 className="modal-title">Recovery Analytics &amp; Yield</h3>
              <p className="modal-subtitle">
                Performance indicators and recovery conversion metrics.
              </p>
            </div>
          </div>
          <button className="modal-close-btn" onClick={onClose}>
            <CloseIcon size={20} />
          </button>
        </div>

        <div className="modal-body">
          <div className="analytics-grid">
            <div className="stat-card">
              <span className="stat-label">EXPECTED RECOVERY YIELD</span>
              <div className="stat-value text-emerald">~68.4%</div>
              <span className="stat-note">Based on 50 synthetic test cohorts</span>
            </div>
            <div className="stat-card">
              <span className="stat-label">AVG TIME TO RECOVERY</span>
              <div className="stat-value text-cyan">4.2 min</div>
              <span className="stat-note">Via WhatsApp instant link</span>
            </div>
            <div className="stat-card">
              <span className="stat-label">POLICY SAFETY PASS-RATE</span>
              <div className="stat-value text-emerald">100%</div>
              <span className="stat-note">0 unauthorized dispatches</span>
            </div>
          </div>

          <div className="channel-distribution-card">
            <h4 className="dist-title">Channel Utilization Breakdown</h4>
            <div className="dist-bars">
              <div className="dist-row">
                <span className="dist-label">WhatsApp (Preferred)</span>
                <div className="dist-track">
                  <div className="dist-fill fill-emerald" style={{ width: '74%' }} />
                </div>
                <span className="dist-pct">74%</span>
              </div>
              <div className="dist-row">
                <span className="dist-label">Email Fallback</span>
                <div className="dist-track">
                  <div className="dist-fill fill-cyan" style={{ width: '22%' }} />
                </div>
                <span className="dist-pct">22%</span>
              </div>
              <div className="dist-row">
                <span className="dist-label">SMS Notification</span>
                <div className="dist-track">
                  <div className="dist-fill fill-amber" style={{ width: '4%' }} />
                </div>
                <span className="dist-pct">4%</span>
              </div>
            </div>
          </div>
        </div>

        <div className="modal-footer">
          <button className="btn-primary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export const SettingsModal: React.FC<ModalProps> = ({ onClose }) => {
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card modal-auxiliary" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="title-with-icon">
            <SlidersIcon size={20} color="#06B6D4" />
            <div>
              <h3 className="modal-title">Engine Configuration</h3>
              <p className="modal-subtitle">
                System parameters, environment flags, and AI provider status.
              </p>
            </div>
          </div>
          <button className="modal-close-btn" onClick={onClose}>
            <CloseIcon size={20} />
          </button>
        </div>

        <div className="modal-body">
          <div className="config-list">
            <div className="config-item">
              <span className="config-key">AI LLM Provider</span>
              <span className="config-val badge-tag">Mock LLM (Deterministic Safe)</span>
            </div>
            <div className="config-item">
              <span className="config-key">Autonomous Execution Threshold</span>
              <span className="config-val font-mono">₹25,000.00</span>
            </div>
            <div className="config-item">
              <span className="config-key">Max Recovery Retry Count</span>
              <span className="config-val font-mono">3 Attempts</span>
            </div>
            <div className="config-item">
              <span className="config-key">Database Store</span>
              <span className="config-val">PostgreSQL (SQLAlchemy Engine)</span>
            </div>
            <div className="config-item">
              <span className="config-key">Payment Gateway Adapter</span>
              <span className="config-val">Mock Razorpay Link Generator</span>
            </div>
          </div>
        </div>

        <div className="modal-footer">
          <button className="btn-primary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
