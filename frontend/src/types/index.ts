export type PolicyDecision = 'APPROVED' | 'HUMAN_REVIEW' | 'BLOCKED';
export type PolicyAction = 'PAYMENT_LINK' | 'NONE';
export type RecoverabilityTier = 'HIGH' | 'MEDIUM' | 'LOW';
export type RecoveryCaseStatus = 'PENDING' | 'PROCESSING' | 'RECOVERED' | 'FAILED' | 'STOPPED';
export type RecoveryChannel = 'WHATSAPP' | 'SMS' | 'EMAIL' | 'NONE';

export interface RecoveryOverview {
  total_failed_payments: number;
  total_revenue_at_risk_in_paise: number;
  approved_cases: number;
  human_review_cases: number;
  blocked_cases: number;
  stopped_cases: number;
  total_recovery_attempts: number;
}

export interface CandidateItem {
  recovery_case_id: string;
  payment_id: string;
  customer_name: string;
  amount_in_paise: number;
  currency: string;
  error_code: string | null;
  risk_score: number | null;
  recoverability: RecoverabilityTier | null;
  policy_decision: PolicyDecision;
  policy_reason: string | null;
  allowed_action: PolicyAction;
}

export interface CustomerDetail {
  id: string;
  name: string;
  email: string;
  phone: string | null;
  created_at: string;
}

export interface PaymentDetail {
  id: string;
  amount_in_paise: number;
  currency: string;
  status: string;
  gateway: string | null;
  gateway_payment_id: string | null;
  error_code: string | null;
  error_description: string | null;
  created_at: string;
}

export interface RecoveryAttemptDetail {
  id: string;
  attempt_number: number;
  action: string;
  status: string;
  channel: string | null;
  details: Record<string, any> | null;
  created_at: string;
}

export interface AuditEventDetail {
  id: string;
  event_type: string;
  from_state: string | null;
  to_state: string | null;
  actor: string | null;
  payload: Record<string, any> | null;
  created_at: string;
}

export interface RecoveryCaseDetail {
  id: string;
  status: RecoveryCaseStatus;
  policy_decision: PolicyDecision | null;
  policy_reason: string | null;
  created_at: string;
  updated_at: string;
  payment: PaymentDetail;
  customer: CustomerDetail;
  recovery_attempts: RecoveryAttemptDetail[];
  audit_events: AuditEventDetail[];
}

export interface RecoveryExecutionResponse {
  recovery_case_id: string;
  attempt_id: string;
  attempt_number: number;
  status: string;
  action: string;
  channel: string;
  payment_link: string;
  message: string;
}

export type CandidateTabFilter = 'ALL_CANDIDATES' | 'APPROVED' | 'HIGH_RECOVERABILITY' | 'ALL_CASES';
