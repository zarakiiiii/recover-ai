import React, { useState } from 'react';
import type { RecoveryExecutionResponse } from '../types';
import {
  CheckCircleIcon,
  CheckIcon,
  CloseIcon,
  CopyIcon,
  ExternalLinkIcon,
  MessageSquareIcon,
  SmartphoneIcon,
  SparklesIcon,
  ZapIcon,
} from './Icons';

interface ExecutionModalProps {
  result: RecoveryExecutionResponse | null;
  onClose: () => void;
  onViewCaseDetails: (caseId: string) => void;
}

export const ExecutionModal: React.FC<ExecutionModalProps> = ({
  result,
  onClose,
  onViewCaseDetails,
}) => {
  const [copied, setCopied] = useState(false);

  if (!result) return null;

  const handleCopyLink = () => {
    navigator.clipboard.writeText(result.payment_link);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card modal-execution" onClick={(e) => e.stopPropagation()}>
        {/* Top Header */}
        <div className="modal-header header-success">
          <div className="success-icon-badge">
            <CheckCircleIcon size={26} color="#10B981" />
          </div>
          <div>
            <h3 className="modal-title">Recovery Successfully Executed!</h3>
            <p className="modal-subtitle">
              Autonomous payment link created &amp; customer notification dispatched.
            </p>
          </div>
          <button className="modal-close-btn" onClick={onClose}>
            <CloseIcon size={20} />
          </button>
        </div>

        {/* Modal Body */}
        <div className="modal-body">
          {/* Key Execution Badges */}
          <div className="execution-badges-row">
            <div className="exec-badge-item">
              <span className="badge-meta-label">ATTEMPT NUMBER</span>
              <span className="badge-meta-val">#{result.attempt_number}</span>
            </div>
            <div className="exec-badge-item">
              <span className="badge-meta-label">CHANNEL</span>
              <span className="badge-meta-val channel-val">
                <SmartphoneIcon size={14} />
                {result.channel}
              </span>
            </div>
            <div className="exec-badge-item">
              <span className="badge-meta-label">STATUS</span>
              <span className="badge-meta-val status-val">
                <span className="live-dot dot-emerald" />
                {result.status}
              </span>
            </div>
            <div className="exec-badge-item">
              <span className="badge-meta-label">ACTION</span>
              <span className="badge-meta-val">{result.action}</span>
            </div>
          </div>

          {/* Generated Payment Link Box */}
          <div className="payment-link-box">
            <div className="link-box-header">
              <span className="link-label">
                <ZapIcon size={14} color="#06B6D4" />
                GENERATED SECURE PAYMENT LINK
              </span>
              <span className="link-tag">Mock Gateway</span>
            </div>
            <div className="link-input-group">
              <input
                type="text"
                readOnly
                value={result.payment_link}
                className="payment-link-input"
              />
              <button
                className={`btn-copy ${copied ? 'copied' : ''}`}
                onClick={handleCopyLink}
                title="Copy payment link to clipboard"
              >
                {copied ? (
                  <>
                    <CheckIcon size={15} color="#10B981" />
                    <span>Copied!</span>
                  </>
                ) : (
                  <>
                    <CopyIcon size={15} />
                    <span>Copy</span>
                  </>
                )}
              </button>
              <a
                href={result.payment_link}
                target="_blank"
                rel="noreferrer"
                className="btn-visit"
                title="Open payment link in new tab"
              >
                <ExternalLinkIcon size={15} />
              </a>
            </div>
          </div>

          {/* Customer Message Dispatched */}
          <div className="customer-message-card">
            <div className="message-header">
              <div className="msg-title-wrap">
                <MessageSquareIcon size={15} color="#06B6D4" />
                <span>CUSTOMER NOTIFICATION SENT</span>
              </div>
              <span className="msg-channel-tag">{result.channel} Preview</span>
            </div>
            <div className="chat-bubble">
              <p className="chat-text">{result.message}</p>
              <span className="chat-timestamp">Just now • Delivered</span>
            </div>
          </div>

          {/* Audit Notification */}
          <div className="audit-notice">
            <SparklesIcon size={16} color="#06B6D4" />
            <span>
              Audit events <strong>RECOVERY_EXECUTION_STARTED</strong> and{' '}
              <strong>RECOVERY_EXECUTION_COMPLETED</strong> committed to PostgreSQL.
            </span>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="modal-footer">
          <button
            className="btn-secondary"
            onClick={() => {
              onClose();
              onViewCaseDetails(result.recovery_case_id);
            }}
          >
            View Case &amp; Audit Trail
          </button>
          <button className="btn-primary" onClick={onClose}>
            Done
          </button>
        </div>
      </div>
    </div>
  );
};
