export function formatINR(paise: number | undefined | null): string {
  if (paise === undefined || paise === null || isNaN(paise)) {
    return '₹0.00';
  }
  const rupees = paise / 100;
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(rupees);
}

export function formatINRShort(paise: number | undefined | null): string {
  if (paise === undefined || paise === null || isNaN(paise)) {
    return '₹0';
  }
  const rupees = paise / 100;
  if (rupees >= 10000000) {
    return `₹${(rupees / 10000000).toFixed(2)} Cr`;
  }
  if (rupees >= 100000) {
    return `₹${(rupees / 100000).toFixed(2)} L`;
  }
  if (rupees >= 1000) {
    return `₹${(rupees / 1000).toFixed(1)}k`;
  }
  return `₹${rupees.toFixed(0)}`;
}

export function formatDate(isoString: string | undefined | null): string {
  if (!isoString) return '—';
  try {
    const date = new Date(isoString);
    return new Intl.DateTimeFormat('en-IN', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: true,
    }).format(date);
  } catch {
    return isoString;
  }
}

export function formatTimeAgo(isoString: string | undefined | null): string {
  if (!isoString) return '—';
  try {
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffSec / 60);
    const diffHour = Math.floor(diffMin / 60);
    const diffDay = Math.floor(diffHour / 24);

    if (diffDay > 0) return `${diffDay}d ago`;
    if (diffHour > 0) return `${diffHour}h ago`;
    if (diffMin > 0) return `${diffMin}m ago`;
    return 'just now';
  } catch {
    return isoString;
  }
}

export interface BadgeStyle {
  label: string;
  bg: string;
  color: string;
  border: string;
  dotColor: string;
}

export function getRecoverabilityBadge(tier: string | null | undefined): BadgeStyle {
  switch (tier?.toUpperCase()) {
    case 'HIGH':
      return {
        label: 'HIGH RECOVERABILITY',
        bg: 'rgba(16, 185, 129, 0.12)',
        color: '#10B981',
        border: 'rgba(16, 185, 129, 0.3)',
        dotColor: '#10B981',
      };
    case 'MEDIUM':
      return {
        label: 'MEDIUM RECOVERABILITY',
        bg: 'rgba(245, 158, 11, 0.12)',
        color: '#F59E0B',
        border: 'rgba(245, 158, 11, 0.3)',
        dotColor: '#F59E0B',
      };
    case 'LOW':
      return {
        label: 'LOW RECOVERABILITY',
        bg: 'rgba(239, 68, 68, 0.12)',
        color: '#EF4444',
        border: 'rgba(239, 68, 68, 0.3)',
        dotColor: '#EF4444',
      };
    default:
      return {
        label: 'UNASSESSED',
        bg: 'rgba(148, 163, 184, 0.12)',
        color: '#94A3B8',
        border: 'rgba(148, 163, 184, 0.3)',
        dotColor: '#94A3B8',
      };
  }
}

export function getDecisionBadge(decision: string | null | undefined): BadgeStyle {
  switch (decision?.toUpperCase()) {
    case 'APPROVED':
      return {
        label: 'APPROVED',
        bg: 'rgba(6, 182, 212, 0.15)',
        color: '#22D3EE',
        border: 'rgba(6, 182, 212, 0.35)',
        dotColor: '#06B6D4',
      };
    case 'HUMAN_REVIEW':
      return {
        label: 'HUMAN REVIEW',
        bg: 'rgba(245, 158, 11, 0.15)',
        color: '#FBBF24',
        border: 'rgba(245, 158, 11, 0.35)',
        dotColor: '#F59E0B',
      };
    case 'BLOCKED':
      return {
        label: 'BLOCKED',
        bg: 'rgba(244, 63, 94, 0.15)',
        color: '#FB7185',
        border: 'rgba(244, 63, 94, 0.35)',
        dotColor: '#F43F5E',
      };
    default:
      return {
        label: decision || 'PENDING',
        bg: 'rgba(148, 163, 184, 0.15)',
        color: '#CBD5E1',
        border: 'rgba(148, 163, 184, 0.3)',
        dotColor: '#94A3B8',
      };
  }
}

export function getStatusBadge(status: string | null | undefined): BadgeStyle {
  switch (status?.toUpperCase()) {
    case 'RECOVERED':
      return {
        label: 'RECOVERED',
        bg: 'rgba(16, 185, 129, 0.18)',
        color: '#34D399',
        border: 'rgba(16, 185, 129, 0.4)',
        dotColor: '#10B981',
      };
    case 'PROCESSING':
      return {
        label: 'PROCESSING',
        bg: 'rgba(59, 130, 246, 0.18)',
        color: '#60A5FA',
        border: 'rgba(59, 130, 246, 0.4)',
        dotColor: '#3B82F6',
      };
    case 'STOPPED':
      return {
        label: 'STOPPED',
        bg: 'rgba(100, 116, 139, 0.25)',
        color: '#94A3B8',
        border: 'rgba(100, 116, 139, 0.4)',
        dotColor: '#64748B',
      };
    case 'FAILED':
      return {
        label: 'FAILED',
        bg: 'rgba(244, 63, 94, 0.18)',
        color: '#FB7185',
        border: 'rgba(244, 63, 94, 0.4)',
        dotColor: '#F43F5E',
      };
    case 'PENDING':
    default:
      return {
        label: 'PENDING',
        bg: 'rgba(245, 158, 11, 0.15)',
        color: '#FBBF24',
        border: 'rgba(245, 158, 11, 0.35)',
        dotColor: '#F59E0B',
      };
  }
}

export function getErrorCodeDescription(code: string | null | undefined): { title: string; desc: string; category: string } {
  switch (code?.toUpperCase()) {
    case 'NETWORK_ERROR':
      return {
        title: 'Network Timeout / Socket Error',
        desc: 'Transient connection glitch between issuer switch and gateway.',
        category: 'TRANSIENT',
      };
    case 'BANK_ERROR':
      return {
        title: 'Issuer Bank Gateway Error',
        desc: 'Downstream bank downtime or gateway internal server error.',
        category: 'TRANSIENT',
      };
    case 'INSUFFICIENT_FUNDS':
      return {
        title: 'Insufficient Balance',
        desc: 'Customer account had inadequate balance at checkout time.',
        category: 'CUSTOMER_ACTIONABLE',
      };
    case 'CARD_DECLINED':
      return {
        title: 'Card Issuer Declined',
        desc: 'Declined by customer bank due to limits or international block.',
        category: 'CUSTOMER_ACTIONABLE',
      };
    case 'EXPIRED_CARD':
      return {
        title: 'Card Validity Expired',
        desc: 'Payment method expiration date has elapsed.',
        category: 'CUSTOMER_ACTIONABLE',
      };
    case 'AUTHENTICATION_FAILED':
      return {
        title: '3DS / OTP Auth Failed',
        desc: 'Security challenge failed or OTP expired. Marked non-recoverable.',
        category: 'NON_RECOVERABLE',
      };
    case 'UNKNOWN_ERROR':
    default:
      return {
        title: code || 'Unclassified Error',
        desc: 'Unclassified failure code requiring human inspection.',
        category: 'UNCERTAIN',
      };
  }
}
