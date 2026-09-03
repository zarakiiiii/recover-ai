import type {
  CandidateItem,
  RecoveryCaseDetail,
  RecoveryExecutionResponse,
  RecoveryOverview,
} from '../types';

const BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/+$/, '');

class ApiError extends Error {
  status: number;
  detail?: string;

  constructor(message: string, status: number, detail?: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${BASE_URL}${endpoint}`;
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  };

  try {
    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      let errorMessage = `HTTP Error ${response.status}: ${response.statusText}`;
      let detail: string | undefined;

      try {
        const errorData = await response.json();
        if (errorData && errorData.detail) {
          detail = typeof errorData.detail === 'string' ? errorData.detail : JSON.stringify(errorData.detail);
          if (detail) {
            errorMessage = detail;
          }
        }
      } catch {
        // Response was not JSON
      }

      throw new ApiError(errorMessage, response.status, detail);
    }

    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    const message = error instanceof Error ? error.message : 'Unknown network error';
    throw new ApiError(`Failed to connect to backend (${BASE_URL}): ${message}`, 0);
  }
}

export const recoveryApi = {
  /**
   * Fetch aggregate recovery metrics from PostgreSQL.
   */
  getOverview: (): Promise<RecoveryOverview> => {
    return request<RecoveryOverview>('/api/recovery/overview');
  },

  /**
   * Fetch list of recovery candidates currently eligible for automated recovery.
   */
  getCandidates: (): Promise<CandidateItem[]> => {
    return request<CandidateItem[]>('/api/recovery/candidates');
  },

  /**
   * Fetch full details of a specific recovery case.
   */
  getCaseDetail: (caseId: string): Promise<RecoveryCaseDetail> => {
    return request<RecoveryCaseDetail>(`/api/recovery/cases/${caseId}`);
  },

  /**
   * Execute automated recovery for an approved case.
   */
  executeRecovery: (caseId: string): Promise<RecoveryExecutionResponse> => {
    return request<RecoveryExecutionResponse>(`/api/recovery/cases/${caseId}/execute`, {
      method: 'POST',
    });
  },
};
