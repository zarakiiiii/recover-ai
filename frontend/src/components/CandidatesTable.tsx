import React, { useState } from 'react';
import type { CandidateItem } from '../types';
import {
  formatINR,
  getDecisionBadge,
  getErrorCodeDescription,
  getRecoverabilityBadge,
} from '../utils/formatters';
import {
  ChevronRightIcon,
  FilterIcon,
  SearchIcon,
  ZapIcon,
} from './Icons';

interface CandidatesTableProps {
  candidates: CandidateItem[];
  isLoading: boolean;
  onSelectCandidate: (caseId: string) => void;
  onQuickExecute: (caseId: string, e: React.MouseEvent) => void;
}

export const CandidatesTable: React.FC<CandidatesTableProps> = ({
  candidates,
  isLoading,
  onSelectCandidate,
  onQuickExecute,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [activeTab, setActiveTab] = useState<'ALL' | 'HIGH_RECOVERABILITY' | 'LOW_AMOUNT'>('ALL');

  const filteredCandidates = candidates.filter((c) => {
    // Search match
    const searchLower = searchTerm.toLowerCase();
    const matchesSearch =
      !searchTerm ||
      c.customer_name.toLowerCase().includes(searchLower) ||
      c.payment_id.toLowerCase().includes(searchLower) ||
      (c.error_code && c.error_code.toLowerCase().includes(searchLower)) ||
      c.recovery_case_id.toLowerCase().includes(searchLower);

    if (!matchesSearch) return false;

    // Tab filter
    if (activeTab === 'HIGH_RECOVERABILITY') {
      return c.recoverability === 'HIGH' || (c.risk_score !== null && c.risk_score >= 80);
    }
    if (activeTab === 'LOW_AMOUNT') {
      return c.amount_in_paise <= 1000000; // <= ₹10,000
    }

    return true;
  });

  return (
    <section className="candidates-section">
      <div className="section-header">
        <div className="section-title-wrap">
          <div className="section-icon">
            <ZapIcon size={18} color="#06B6D4" />
          </div>
          <div>
            <h2 className="section-title">Autonomous Recovery Candidates</h2>
            <p className="section-desc">
              Approved failed payments meeting risk &amp; policy guardrails ready for automated customer payment links.
            </p>
          </div>
        </div>

        <div className="table-controls">
          <div className="tab-filters">
            <button
              className={`tab-btn ${activeTab === 'ALL' ? 'active' : ''}`}
              onClick={() => setActiveTab('ALL')}
            >
              All Approved ({candidates.length})
            </button>
            <button
              className={`tab-btn ${activeTab === 'HIGH_RECOVERABILITY' ? 'active' : ''}`}
              onClick={() => setActiveTab('HIGH_RECOVERABILITY')}
            >
              High Recoverability (Score ≥ 80)
            </button>
            <button
              className={`tab-btn ${activeTab === 'LOW_AMOUNT' ? 'active' : ''}`}
              onClick={() => setActiveTab('LOW_AMOUNT')}
            >
              Micro-Recoveries (≤ ₹10k)
            </button>
          </div>

          <div className="search-box">
            <SearchIcon size={16} color="#64748B" />
            <input
              type="text"
              placeholder="Search by customer, payment ID, error..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="search-input"
            />
            {searchTerm && (
              <button className="search-clear" onClick={() => setSearchTerm('')}>
                ×
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="table-wrapper">
        <table className="candidates-table">
          <thead>
            <tr>
              <th>CUSTOMER</th>
              <th>AMOUNT</th>
              <th>FAILURE REASON</th>
              <th>RISK SCORE</th>
              <th>RECOVERABILITY</th>
              <th>POLICY DECISION</th>
              <th className="th-action">ACTION</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && candidates.length === 0 ? (
              Array.from({ length: 6 }).map((_, idx) => (
                <tr key={idx} className="skeleton-row">
                  <td colSpan={7}>
                    <div className="skeleton-line" />
                  </td>
                </tr>
              ))
            ) : filteredCandidates.length === 0 ? (
              <tr>
                <td colSpan={7} className="empty-table-cell">
                  <div className="empty-state">
                    <FilterIcon size={32} color="#64748B" />
                    <h3>No candidates found</h3>
                    <p>
                      {searchTerm
                        ? `No recovery candidates match "${searchTerm}".`
                        : 'There are currently no approved recovery candidates.'}
                    </p>
                    {searchTerm && (
                      <button className="btn-secondary btn-sm" onClick={() => setSearchTerm('')}>
                        Clear Search
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ) : (
              filteredCandidates.map((candidate) => {
                const recBadge = getRecoverabilityBadge(candidate.recoverability);
                const decisionBadge = getDecisionBadge(candidate.policy_decision);
                const errorInfo = getErrorCodeDescription(candidate.error_code);
                const score = candidate.risk_score ?? 85;
                const scoreColor =
                  score >= 80 ? '#10B981' : score >= 50 ? '#F59E0B' : '#EF4444';

                return (
                  <tr
                    key={candidate.recovery_case_id}
                    className="candidate-row"
                    onClick={() => onSelectCandidate(candidate.recovery_case_id)}
                  >
                    {/* Customer */}
                    <td className="td-customer">
                      <div className="customer-cell">
                        <div className="customer-avatar">
                          {candidate.customer_name.charAt(0).toUpperCase()}
                        </div>
                        <div className="customer-meta">
                          <span className="customer-name">{candidate.customer_name}</span>
                          <span className="customer-id" title={candidate.payment_id}>
                            PayID: {candidate.payment_id.slice(0, 8)}...
                          </span>
                        </div>
                      </div>
                    </td>

                    {/* Amount */}
                    <td className="td-amount">
                      <div className="amount-cell">
                        <span className="amount-main">{formatINR(candidate.amount_in_paise)}</span>
                        <span className="amount-currency">{candidate.currency}</span>
                      </div>
                    </td>

                    {/* Failure Reason */}
                    <td className="td-failure">
                      <div className="failure-cell">
                        <span className="failure-badge" title={errorInfo.desc}>
                          {candidate.error_code || 'NETWORK_ERROR'}
                        </span>
                        <span className="failure-title">{errorInfo.title}</span>
                      </div>
                    </td>

                    {/* Risk Score */}
                    <td className="td-risk">
                      <div className="risk-cell">
                        <div className="risk-score-wrap">
                          <span className="risk-number" style={{ color: scoreColor }}>
                            {score}
                          </span>
                          <span className="risk-max">/100</span>
                        </div>
                        <div className="risk-bar-track">
                          <div
                            className="risk-bar-fill"
                            style={{
                              width: `${Math.min(Math.max(score, 5), 100)}%`,
                              backgroundColor: scoreColor,
                            }}
                          />
                        </div>
                      </div>
                    </td>

                    {/* Recoverability */}
                    <td className="td-recoverability">
                      <span
                        className="badge-pill"
                        style={{
                          backgroundColor: recBadge.bg,
                          color: recBadge.color,
                          borderColor: recBadge.border,
                        }}
                      >
                        <span className="badge-dot" style={{ backgroundColor: recBadge.dotColor }} />
                        {candidate.recoverability || 'HIGH'}
                      </span>
                    </td>

                    {/* Policy Decision */}
                    <td className="td-decision">
                      <span
                        className="badge-pill"
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
                        {candidate.policy_decision}
                      </span>
                    </td>

                    {/* Action */}
                    <td className="td-action" onClick={(e) => e.stopPropagation()}>
                      <div className="action-button-group">
                        <button
                          className="btn-execute-quick"
                          onClick={(e) => onQuickExecute(candidate.recovery_case_id, e)}
                          title="Execute autonomous payment link generation and dispatch"
                        >
                          <ZapIcon size={14} color="#FFFFFF" />
                          <span>Execute</span>
                        </button>
                        <button
                          className="btn-inspect-row"
                          onClick={() => onSelectCandidate(candidate.recovery_case_id)}
                          title="View Case Details & Audit Trail"
                        >
                          <ChevronRightIcon size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
};
