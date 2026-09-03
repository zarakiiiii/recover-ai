import React, { useState } from 'react';
import type { RecoveryCaseDetail } from '../types';
import {
  formatDate,
  formatINR,
  formatTimeAgo,
  getDecisionBadge,
  getErrorCodeDescription,
  getRecoverabilityBadge,
  getStatusBadge,
} from '../utils/formatters';
import {
  AlertTriangleIcon,
  CheckCircleIcon,
  CheckIcon,
  ClockIcon,
  CloseIcon,
  CopyIcon,
  CreditCardIcon,
  DatabaseIcon,
  ExternalLinkIcon,
  HistoryIcon,
  MailIcon,
  MessageSquareIcon,
  RefreshCwIcon,
  ShieldIcon,
  SmartphoneIcon,
  SparklesIcon,
  UserIcon,
  XCircleIcon,
  ZapIcon,
} from './Icons';

interface CaseDetailModalProps {
  caseDetail: RecoveryCaseDetail | null;
  isLoading: boolean;
  isExecuting: boolean;
  onClose: () => void;
  onExecute: (caseId: string) => void;
  onRefreshCase: (caseId: string) => void;
}

export const CaseDetailModal: React.FC<CaseDetailModalProps> = ({
  caseDetail,
  isLoading,
  isExecuting,
  onClose,
  onExecute,
  onRefreshCase,
}) => {
  const [copiedId, setCopiedId] = useState(false);
  const [selectedPayloadIndex, setSelectedPayloadIndex] = useState<number | null>(null);

  if (!caseDetail && !isLoading) return null;

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(true);
    setTimeout(() => setCopiedId(false), 2000);
  };

  // Find risk assessment payload from audit events
  let riskScore: number | null = null;
  let recoverability: string | null = null;

  if (caseDetail) {
    for (const evt of caseDetail.audit_events) {
      if (evt.payload && (evt.payload.risk_score !== undefined || evt.payload.recoverability)) {
        riskScore = evt.payload.risk_score ?? null;
        recoverability = evt.payload.recoverability ?? null;
        break;
      }
    }
  }

  const statusBadge = caseDetail ? getStatusBadge(caseDetail.status) : getStatusBadge('PENDING');
  const decisionBadge = caseDetail
    ? getDecisionBadge(caseDetail.policy_decision)
    : getDecisionBadge('APPROVED');
  const recBadge = getRecoverabilityBadge(recoverability || 'HIGH');
  const errorInfo = caseDetail ? getErrorCodeDescription(caseDetail.payment.error_code) : null;

  const isApproved = caseDetail?.policy_decision === 'APPROVED';
  const isHumanReview = caseDetail?.policy_decision === 'HUMAN_REVIEW';
  const isBlocked = caseDetail?.policy_decision === 'BLOCKED';
  const isStopped = caseDetail?.status === 'STOPPED';
  const isRecovered = caseDetail?.status === 'RECOVERED';
  const canExecute = isApproved && !isRecovered && !isStopped && (caseDetail?.recovery_attempts.length || 0) < 3;

  // AI Recommendation simulation matching backend RecoveryAgent logic
  const customerPhone = caseDetail?.customer.phone;
  const recommendedChannel = isApproved ? (customerPhone ? 'WHATSAPP' : 'EMAIL') : 'NONE';
  const simulatedMessage = isApproved && caseDetail
    ? `Hi ${caseDetail.customer.name}, we noticed your recent payment of ${formatINR(
        caseDetail.payment.amount_in_paise
      )} could not be completed due to a temporary banking network issue. You can easily complete your payment here: {{payment_link}}. Please let us know if you need any help!`
    : null;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card modal-case-detail" onClick={(e) => e.stopPropagation()}>
        {/* Modal Header */}
        <div className="modal-header header-detail">
          <div className="case-header-main">
            <div className="case-title-row">
              <span className="case-type-tag">RECOVERY CASE</span>
              <h2 className="case-id" title={caseDetail?.id}>
                {caseDetail ? caseDetail.id : 'Loading case details...'}
              </h2>
              {caseDetail && (
                <button
                  className="btn-copy-id"
                  onClick={() => handleCopy(caseDetail.id)}
                  title="Copy Case UUID"
                >
                  {copiedId ? <CheckIcon size={14} color="#10B981" /> : <CopyIcon size={14} />}
                </button>
              )}
            </div>
            <div className="case-sub-meta">
              <ClockIcon size={14} color="#94A3B8" />
              <span>Created {formatDate(caseDetail?.created_at)}</span>
              <span className="meta-sep">•</span>
              <span>Updated {formatTimeAgo(caseDetail?.updated_at)}</span>
            </div>
          </div>

          <div className="case-header-actions">
            {caseDetail && (
              <span
                className="badge-pill badge-status"
                style={{
                  backgroundColor: statusBadge.bg,
                  color: statusBadge.color,
                  borderColor: statusBadge.border,
                }}
              >
                <span className="badge-dot" style={{ backgroundColor: statusBadge.dotColor }} />
                STATUS: {caseDetail.status}
              </span>
            )}
            {caseDetail && (
              <button
                className="btn-icon-refresh"
                onClick={() => onRefreshCase(caseDetail.id)}
                disabled={isLoading}
                title="Refresh case data"
              >
                <RefreshCwIcon size={16} spinning={isLoading} />
              </button>
            )}
            <button className="modal-close-btn" onClick={onClose} title="Close">
              <CloseIcon size={20} />
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div className="modal-body case-detail-body">
          {isLoading && !caseDetail ? (
            <div className="case-loading-state">
              <RefreshCwIcon size={32} spinning={true} color="#06B6D4" />
              <p>Fetching full recovery case telemetry from database...</p>
            </div>
          ) : caseDetail ? (
            <>
              {/* TOP DOSSIER GRID: Customer & Payment */}
              <div className="dossier-grid">
                {/* Customer Dossier */}
                <div className="dossier-card">
                  <div className="dossier-card-title">
                    <UserIcon size={16} color="#06B6D4" />
                    <span>CUSTOMER PROFILE</span>
                  </div>
                  <div className="dossier-fields">
                    <div className="dossier-row">
                      <span className="dossier-label">Name</span>
                      <span className="dossier-val font-semibold">{caseDetail.customer.name}</span>
                    </div>
                    <div className="dossier-row">
                      <span className="dossier-label">Email</span>
                      <span className="dossier-val font-mono">{caseDetail.customer.email}</span>
                    </div>
                    <div className="dossier-row">
                      <span className="dossier-label">Phone</span>
                      <span className="dossier-val font-mono">
                        {caseDetail.customer.phone || 'Not provided'}
                      </span>
                    </div>
                    <div className="dossier-row">
                      <span className="dossier-label">Customer ID</span>
                      <span className="dossier-val font-mono text-muted">
                        {caseDetail.customer.id.slice(0, 12)}...
                      </span>
                    </div>
                  </div>
                </div>

                {/* Payment Dossier */}
                <div className="dossier-card">
                  <div className="dossier-card-title">
                    <CreditCardIcon size={16} color="#F43F5E" />
                    <span>FAILED PAYMENT RECORD</span>
                  </div>
                  <div className="dossier-fields">
                    <div className="dossier-row">
                      <span className="dossier-label">Amount at Risk</span>
                      <span className="dossier-val amount-highlight">
                        {formatINR(caseDetail.payment.amount_in_paise)}
                      </span>
                    </div>
                    <div className="dossier-row">
                      <span className="dossier-label">Payment ID</span>
                      <span className="dossier-val font-mono text-muted">
                        {caseDetail.payment.id.slice(0, 12)}...
                      </span>
                    </div>
                    <div className="dossier-row">
                      <span className="dossier-label">Gateway / Error</span>
                      <span className="dossier-val">
                        <span className="failure-code-tag">
                          {caseDetail.payment.error_code || 'NETWORK_ERROR'}
                        </span>
                      </span>
                    </div>
                    <div className="dossier-row">
                      <span className="dossier-label">Description</span>
                      <span className="dossier-val error-desc">
                        {caseDetail.payment.error_description ||
                          errorInfo?.desc ||
                          'Failure recorded by gateway'}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* RISK & POLICY ENGINE DECISION SECTION */}
              <div className="engine-decision-card">
                <div className="engine-header">
                  <div className="engine-title-wrap">
                    <ShieldIcon size={18} color="#06B6D4" />
                    <span>DETERMINISTIC RISK &amp; POLICY AUTHORIZATION</span>
                  </div>
                  <span className="engine-badge">Policy Engine v1</span>
                </div>

                <div className="decision-banner-box">
                  <div className="decision-banner-left">
                    <div className="decision-status-pill-wrap">
                      <span
                        className="decision-status-large"
                        style={{
                          backgroundColor: decisionBadge.bg,
                          color: decisionBadge.color,
                          borderColor: decisionBadge.border,
                        }}
                      >
                        <span
                          className="badge-dot"
                          style={{ backgroundColor: decisionBadge.dotColor }}
                        />
                        {caseDetail.policy_decision}
                      </span>
                      <span
                        className="badge-pill"
                        style={{
                          backgroundColor: recBadge.bg,
                          color: recBadge.color,
                          borderColor: recBadge.border,
                        }}
                      >
                        {recBadge.label}
                      </span>
                    </div>

                    <div className="policy-reason-text">
                      <strong>Policy Assessment:</strong>{' '}
                      {caseDetail.policy_reason ||
                        (isApproved
                          ? 'Payment failure is high recoverability and amount is within autonomous threshold (<= ₹25,000).'
                          : isHumanReview
                          ? 'Case exceeds autonomous value threshold or has unclassified error code. Hold for manual review.'
                          : 'Non-recoverable security/authentication failure. Automated attempts blocked.')}
                    </div>
                  </div>

                  <div className="risk-score-display">
                    <div className="risk-score-circle">
                      <span className="risk-score-num">{riskScore ?? 85}</span>
                      <span className="risk-score-denom">/ 100</span>
                    </div>
                    <span className="risk-score-caption">Risk Assessment Score</span>
                  </div>
                </div>
              </div>

              {/* AI RECOVERY AGENT RECOMMENDATION */}
              <div className="ai-recommendation-card">
                <div className="ai-header">
                  <div className="ai-title-wrap">
                    <SparklesIcon size={18} color="#06B6D4" />
                    <span className="ai-title">AI RECOVERY RECOMMENDATION</span>
                  </div>
                  <div className="ai-guardrail-tag">
                    <ShieldIcon size={13} color="#10B981" />
                    <span>Strict Guardrails Enforced</span>
                  </div>
                </div>

                <div className="ai-content-grid">
                  <div className="ai-meta-col">
                    <div className="ai-meta-item">
                      <span className="ai-meta-label">RECOMMENDED CHANNEL</span>
                      <span className="ai-meta-val channel-badge">
                        {recommendedChannel === 'WHATSAPP' ? (
                          <SmartphoneIcon size={14} color="#10B981" />
                        ) : recommendedChannel === 'EMAIL' ? (
                          <MailIcon size={14} color="#06B6D4" />
                        ) : (
                          <XCircleIcon size={14} color="#94A3B8" />
                        )}
                        {recommendedChannel}
                      </span>
                    </div>

                    <div className="ai-meta-item">
                      <span className="ai-meta-label">RECOMMENDED ACTION</span>
                      <span className="ai-meta-val action-badge">
                        <ZapIcon size={14} color="#06B6D4" />
                        {isApproved ? 'PAYMENT_LINK' : 'NONE'}
                      </span>
                    </div>

                    <div className="ai-meta-item">
                      <span className="ai-meta-label">AI CONFIDENCE</span>
                      <span className="ai-meta-val confidence-val">
                        <span className="live-dot dot-cyan" />
                        {isApproved ? '95%' : isHumanReview ? '90%' : '100%'}
                      </span>
                    </div>

                    <div className="ai-meta-item">
                      <span className="ai-meta-label">HUMAN REVIEW REQUIRED</span>
                      <span
                        className={`ai-meta-val review-flag ${
                          isHumanReview ? 'flag-yes' : 'flag-no'
                        }`}
                      >
                        {isHumanReview ? 'YES' : 'NO'}
                      </span>
                    </div>
                  </div>

                  <div className="ai-message-col">
                    <span className="msg-preview-label">
                      <MessageSquareIcon size={14} />
                      AI DISPATCH MESSAGE PREVIEW
                    </span>
                    {simulatedMessage ? (
                      <div className="chat-preview-box">
                        <div className="chat-bubble">
                          <p className="chat-text">{simulatedMessage}</p>
                          <div className="chat-footer">
                            <span className="chat-time">Auto-generated • Ready</span>
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="no-message-box">
                        <AlertTriangleIcon size={20} color="#F59E0B" />
                        <p>
                          {isBlocked
                            ? 'No customer message generated: Policy Engine blocked automated recovery for non-recoverable error.'
                            : isHumanReview
                            ? 'Customer message withheld: Case requires manual operator review before message dispatch.'
                            : isStopped
                            ? 'No message: Maximum recovery attempt limit reached.'
                            : 'No active AI recommendation.'}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* EXECUTION ACTION PANEL */}
              <div className="execution-action-panel">
                {canExecute ? (
                  <div className="exec-ready-banner">
                    <div className="exec-info">
                      <div className="exec-title">
                        <ZapIcon size={18} color="#06B6D4" />
                        <span>Ready for Autonomous Execution</span>
                      </div>
                      <p className="exec-desc">
                        Clicking execute will trigger the Recovery Agent to generate a secure Razorpay mock payment link, dispatch the customer notification via {recommendedChannel}, and log the transaction to the immutable audit trail.
                      </p>
                    </div>
                    <button
                      className="btn-execute-large"
                      onClick={() => onExecute(caseDetail.id)}
                      disabled={isExecuting}
                    >
                      {isExecuting ? (
                        <>
                          <RefreshCwIcon size={18} spinning={true} />
                          <span>Executing Recovery...</span>
                        </>
                      ) : (
                        <>
                          <ZapIcon size={18} color="#FFFFFF" />
                          <span>Execute Recovery Now</span>
                        </>
                      )}
                    </button>
                  </div>
                ) : isRecovered ? (
                  <div className="exec-status-banner banner-success">
                    <CheckCircleIcon size={22} color="#10B981" />
                    <div>
                      <h4 className="banner-title">Recovery Already Executed &amp; Resolved</h4>
                      <p className="banner-desc">
                        This recovery case was executed. Check previous attempts and audit trail below for the dispatched payment link.
                      </p>
                    </div>
                  </div>
                ) : isHumanReview ? (
                  <div className="exec-status-banner banner-warning">
                    <AlertTriangleIcon size={22} color="#F59E0B" />
                    <div>
                      <h4 className="banner-title">Human Review Required (Execution Restricted)</h4>
                      <p className="banner-desc">
                        Automated recovery execution is held by Policy Engine guardrail (high transaction value or unclassified failure code). Operator review is required.
                      </p>
                    </div>
                  </div>
                ) : isBlocked ? (
                  <div className="exec-status-banner banner-danger">
                    <XCircleIcon size={22} color="#EF4444" />
                    <div>
                      <h4 className="banner-title">Recovery Blocked by Policy Engine</h4>
                      <p className="banner-desc">
                        {caseDetail.policy_reason ||
                          'Non-recoverable failure type (AUTHENTICATION_FAILED / Fraud risk). Automated execution is disabled.'}
                      </p>
                    </div>
                  </div>
                ) : isStopped ? (
                  <div className="exec-status-banner banner-neutral">
                    <HistoryIcon size={22} color="#94A3B8" />
                    <div>
                      <h4 className="banner-title">Recovery Stopped (Max Attempts Exceeded)</h4>
                      <p className="banner-desc">
                        3 previous recovery attempts were dispatched without customer completion. Automated execution is permanently stopped.
                      </p>
                    </div>
                  </div>
                ) : null}
              </div>

              {/* PREVIOUS RECOVERY ATTEMPTS */}
              <div className="case-section-card">
                <div className="section-card-header">
                  <div className="title-with-icon">
                    <HistoryIcon size={16} color="#06B6D4" />
                    <span>RECOVERY ATTEMPTS HISTORY ({caseDetail.recovery_attempts.length})</span>
                  </div>
                </div>

                {caseDetail.recovery_attempts.length === 0 ? (
                  <div className="empty-attempts">
                    <p>No recovery attempts have been dispatched yet for this case.</p>
                  </div>
                ) : (
                  <div className="attempts-list">
                    {caseDetail.recovery_attempts.map((attempt) => (
                      <div key={attempt.id} className="attempt-item-card">
                        <div className="attempt-header">
                          <div className="attempt-title-wrap">
                            <span className="attempt-number-badge">
                              Attempt #{attempt.attempt_number}
                            </span>
                            <span className="attempt-channel">
                              Channel: {attempt.channel || 'WHATSAPP'}
                            </span>
                          </div>
                          <div className="attempt-meta">
                            <span
                              className={`attempt-status status-${attempt.status.toLowerCase()}`}
                            >
                              <span className="live-dot dot-emerald" />
                              {attempt.status}
                            </span>
                            <span className="attempt-date">{formatDate(attempt.created_at)}</span>
                          </div>
                        </div>

                        {attempt.details && (
                          <div className="attempt-details-body">
                            {attempt.details.payment_link_url && (
                              <div className="attempt-link-row">
                                <span className="label">Payment Link:</span>
                                <a
                                  href={attempt.details.payment_link_url}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="link-url"
                                >
                                  {attempt.details.payment_link_url}
                                  <ExternalLinkIcon size={12} />
                                </a>
                              </div>
                            )}
                            {attempt.details.message_sent && (
                              <div className="attempt-msg-row">
                                <span className="label">Dispatched Message:</span>
                                <p className="msg-quote">"{attempt.details.message_sent}"</p>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* IMMUTABLE AUDIT TRAIL */}
              <div className="case-section-card">
                <div className="section-card-header">
                  <div className="title-with-icon">
                    <DatabaseIcon size={16} color="#10B981" />
                    <span>IMMUTABLE AUDIT TRAIL ({caseDetail.audit_events.length} EVENTS)</span>
                  </div>
                  <span className="audit-sub-tag">PostgreSQL Append-Only Log</span>
                </div>

                <div className="audit-timeline">
                  {caseDetail.audit_events.map((event, idx) => {
                    const isSelected = selectedPayloadIndex === idx;
                    return (
                      <div key={event.id} className="audit-timeline-item">
                        <div className="timeline-marker">
                          <div className="marker-dot" />
                          {idx < caseDetail.audit_events.length - 1 && (
                            <div className="marker-line" />
                          )}
                        </div>

                        <div className="timeline-content">
                          <div className="timeline-event-header">
                            <span className="event-type-badge">{event.event_type}</span>
                            <span className="event-actor">Actor: {event.actor || 'SYSTEM'}</span>
                            {event.from_state && event.to_state && (
                              <span className="event-state-transition">
                                {event.from_state} → {event.to_state}
                              </span>
                            )}
                            <span className="event-time">{formatDate(event.created_at)}</span>
                          </div>

                          {event.payload && Object.keys(event.payload).length > 0 && (
                            <div className="timeline-payload-wrap">
                              <button
                                className="btn-toggle-payload"
                                onClick={() =>
                                  setSelectedPayloadIndex(isSelected ? null : idx)
                                }
                              >
                                {isSelected ? 'Hide Payload' : 'Inspect JSON Payload'}
                              </button>
                              {isSelected && (
                                <pre className="payload-json-view">
                                  {JSON.stringify(event.payload, null, 2)}
                                </pre>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </>
          ) : null}
        </div>

        {/* Modal Footer */}
        <div className="modal-footer">
          <button className="btn-secondary" onClick={onClose}>
            Close
          </button>
          {canExecute && (
            <button
              className="btn-primary"
              onClick={() => caseDetail && onExecute(caseDetail.id)}
              disabled={isExecuting}
            >
              {isExecuting ? 'Executing...' : '⚡ Execute Recovery'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
