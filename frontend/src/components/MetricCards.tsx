import React from 'react';
import type { RecoveryOverview } from '../types';
import { formatINR } from '../utils/formatters';
import {
  ActivityIcon,
  AlertTriangleIcon,
  CheckCircleIcon,
  CreditCardIcon,
  ShieldIcon,
  ZapIcon,
} from './Icons';

interface MetricCardsProps {
  overview: RecoveryOverview | null;
  isLoading: boolean;
}

export const MetricCards: React.FC<MetricCardsProps> = ({ overview, isLoading }) => {
  if (isLoading && !overview) {
    return (
      <div className="metric-cards-grid">
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <div key={i} className="metric-card skeleton-card">
            <div className="skeleton-line skeleton-title" />
            <div className="skeleton-line skeleton-value" />
            <div className="skeleton-line skeleton-sub" />
          </div>
        ))}
      </div>
    );
  }

  const revenueAtRisk = overview ? formatINR(overview.total_revenue_at_risk_in_paise) : '₹0.00';
  const failedCount = overview ? overview.total_failed_payments : 0;
  const approvedCount = overview ? overview.approved_cases : 0;
  const reviewCount = overview ? overview.human_review_cases : 0;
  const blockedCount = overview ? overview.blocked_cases : 0;
  const stoppedCount = overview ? overview.stopped_cases : 0;
  const attemptsCount = overview ? overview.total_recovery_attempts : 0;

  return (
    <div className="metric-cards-grid">
      {/* 1. Revenue at Risk */}
      <div className="metric-card card-revenue-at-risk">
        <div className="card-top">
          <span className="card-title">REVENUE AT RISK</span>
          <div className="card-icon-wrap icon-rose">
            <CreditCardIcon size={18} color="#F43F5E" />
          </div>
        </div>
        <div className="card-main">
          <div className="card-value value-highlight-rose">{revenueAtRisk}</div>
          <div className="card-subtext">
            <span className="sub-tag rose-tag">Urgent</span>
            <span>across {failedCount} failed payments</span>
          </div>
        </div>
        <div className="card-glow-bg glow-rose" />
      </div>

      {/* 2. Failed Payments */}
      <div className="metric-card card-failed-payments">
        <div className="card-top">
          <span className="card-title">FAILED PAYMENTS</span>
          <div className="card-icon-wrap icon-amber">
            <AlertTriangleIcon size={18} color="#F59E0B" />
          </div>
        </div>
        <div className="card-main">
          <div className="card-value">{failedCount}</div>
          <div className="card-subtext">
            <span>Requiring risk analysis</span>
          </div>
        </div>
        <div className="card-glow-bg glow-amber" />
      </div>

      {/* 3. Auto-Recovery Approved */}
      <div className="metric-card card-approved">
        <div className="card-top">
          <span className="card-title">AUTO-RECOVERY APPROVED</span>
          <div className="card-icon-wrap icon-cyan">
            <ZapIcon size={18} color="#06B6D4" />
          </div>
        </div>
        <div className="card-main">
          <div className="card-value value-highlight-cyan">{approvedCount}</div>
          <div className="card-subtext">
            <span className="sub-tag cyan-tag">Autonomous</span>
            <span>Authorized for payment links</span>
          </div>
        </div>
        <div className="card-glow-bg glow-cyan" />
      </div>

      {/* 4. Human Review Required */}
      <div className="metric-card card-human-review">
        <div className="card-top">
          <span className="card-title">HUMAN REVIEW</span>
          <div className="card-icon-wrap icon-amber">
            <ShieldIcon size={18} color="#F59E0B" />
          </div>
        </div>
        <div className="card-main">
          <div className="card-value value-highlight-amber">{reviewCount}</div>
          <div className="card-subtext">
            <span className="sub-tag amber-tag">&gt; ₹25k / Uncertain</span>
            <span>Policy guardrail holds</span>
          </div>
        </div>
        <div className="card-glow-bg glow-amber" />
      </div>

      {/* 5. Blocked & Stopped */}
      <div className="metric-card card-blocked">
        <div className="card-top">
          <span className="card-title">BLOCKED & STOPPED</span>
          <div className="card-icon-wrap icon-slate">
            <CheckCircleIcon size={18} color="#94A3B8" />
          </div>
        </div>
        <div className="card-main">
          <div className="card-value">{blockedCount + stoppedCount}</div>
          <div className="card-subtext">
            <span>{blockedCount} Auth/Fraud • {stoppedCount} Max Retries</span>
          </div>
        </div>
        <div className="card-glow-bg glow-slate" />
      </div>

      {/* 6. Recovery Attempts */}
      <div className="metric-card card-attempts">
        <div className="card-top">
          <span className="card-title">RECOVERY ATTEMPTS</span>
          <div className="card-icon-wrap icon-emerald">
            <ActivityIcon size={18} color="#10B981" />
          </div>
        </div>
        <div className="card-main">
          <div className="card-value value-highlight-emerald">{attemptsCount}</div>
          <div className="card-subtext">
            <span className="sub-tag emerald-tag">Executed</span>
            <span>Dispatched to customers</span>
          </div>
        </div>
        <div className="card-glow-bg glow-emerald" />
      </div>
    </div>
  );
};
