import React, { useCallback, useEffect, useState } from 'react';
import {
  AnalyticsModal,
  PolicyRulesModal,
  SettingsModal,
} from './components/AuxiliaryModals';
import { CandidatesTable } from './components/CandidatesTable';
import { CaseDetailModal } from './components/CaseDetailModal';
import { ExecutionModal } from './components/ExecutionModal';
import { Header } from './components/Header';
import { MetricCards } from './components/MetricCards';
import { Sidebar } from './components/Sidebar';
import { ToastContainer } from './components/Toast';
import type { ToastMessage } from './components/Toast';
import { recoveryApi } from './services/api';
import type {
  CandidateItem,
  RecoveryCaseDetail,
  RecoveryExecutionResponse,
  RecoveryOverview,
} from './types';
import './App.css';

export function App() {
  const [overview, setOverview] = useState<RecoveryOverview | null>(null);
  const [candidates, setCandidates] = useState<CandidateItem[]>([]);
  const [selectedCase, setSelectedCase] = useState<RecoveryCaseDetail | null>(null);
  const [executionResult, setExecutionResult] = useState<RecoveryExecutionResponse | null>(null);

  const [isOverviewLoading, setIsOverviewLoading] = useState(false);
  const [isCandidatesLoading, setIsCandidatesLoading] = useState(false);
  const [isCaseLoading, setIsCaseLoading] = useState(false);
  const [isExecuting, setIsExecuting] = useState(false);

  const [activeTab, setActiveTab] = useState<string>('operations');
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const addToast = (type: 'success' | 'error' | 'info', title: string, message?: string) => {
    const id = `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    setToasts((prev) => [...prev, { id, type, title, message }]);
  };

  const removeToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  const fetchDashboardData = useCallback(async (showToastOnSuccess = false) => {
    setIsOverviewLoading(true);
    setIsCandidatesLoading(true);

    try {
      const [overviewData, candidatesData] = await Promise.all([
        recoveryApi.getOverview(),
        recoveryApi.getCandidates(),
      ]);

      setOverview(overviewData);
      setCandidates(candidatesData);
      setLastUpdated(new Date());

      if (showToastOnSuccess) {
        addToast('success', 'Data Synchronized', 'Telemetry refreshed from PostgreSQL.');
      }
    } catch (err: any) {
      const errorMsg = err?.message || 'Failed to connect to RecoverAI backend.';
      addToast('error', 'Sync Failed', errorMsg);
    } finally {
      setIsOverviewLoading(false);
      setIsCandidatesLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDashboardData();
  }, [fetchDashboardData]);

  const handleSelectCandidate = async (caseId: string) => {
    setIsCaseLoading(true);
    try {
      const caseDetail = await recoveryApi.getCaseDetail(caseId);
      setSelectedCase(caseDetail);
    } catch (err: any) {
      addToast('error', 'Error Loading Case', err?.message || 'Case details could not be retrieved.');
    } finally {
      setIsCaseLoading(false);
    }
  };

  const handleRefreshCase = async (caseId: string) => {
    setIsCaseLoading(true);
    try {
      const updatedCase = await recoveryApi.getCaseDetail(caseId);
      setSelectedCase(updatedCase);
      addToast('info', 'Case Refreshed', 'Latest telemetry retrieved.');
    } catch (err: any) {
      addToast('error', 'Refresh Failed', err?.message || 'Failed to refresh case.');
    } finally {
      setIsCaseLoading(false);
    }
  };

  const handleExecuteRecovery = async (caseId: string) => {
    if (isExecuting) return;
    setIsExecuting(true);

    try {
      const response = await recoveryApi.executeRecovery(caseId);
      setExecutionResult(response);
      addToast(
        'success',
        'Autonomous Recovery Dispatched',
        `Attempt #${response.attempt_number} dispatched via ${response.channel}.`
      );

      // Refresh overview and candidates in background
      await fetchDashboardData();

      // If the case detail modal is open, refresh its state
      if (selectedCase && selectedCase.id === caseId) {
        try {
          const refreshed = await recoveryApi.getCaseDetail(caseId);
          setSelectedCase(refreshed);
        } catch {
          // Fallback manual status update
          setSelectedCase((prev) => (prev ? { ...prev, status: 'RECOVERED' } : null));
        }
      }
    } catch (err: any) {
      const errorDetail = err?.detail || err?.message || 'Execution failed';
      addToast('error', 'Execution Blocked', errorDetail);
    } finally {
      setIsExecuting(false);
    }
  };

  const handleQuickExecute = (caseId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    handleExecuteRecovery(caseId);
  };

  return (
    <div className="app-layout">
      {/* Sidebar Navigation */}
      <Sidebar activeTab={activeTab} onTabChange={setActiveTab} />

      {/* Main Dashboard Area */}
      <main className="main-content">
        <Header
          lastUpdated={lastUpdated}
          isLoading={isOverviewLoading || isCandidatesLoading}
          onRefresh={() => fetchDashboardData(true)}
        />

        {/* KPI Metrics */}
        <MetricCards overview={overview} isLoading={isOverviewLoading} />

        {/* Recovery Candidates Data Table */}
        <CandidatesTable
          candidates={candidates}
          isLoading={isCandidatesLoading}
          onSelectCandidate={handleSelectCandidate}
          onQuickExecute={handleQuickExecute}
        />
      </main>

      {/* Modals */}
      {selectedCase && (
        <CaseDetailModal
          caseDetail={selectedCase}
          isLoading={isCaseLoading}
          isExecuting={isExecuting}
          onClose={() => setSelectedCase(null)}
          onExecute={handleExecuteRecovery}
          onRefreshCase={handleRefreshCase}
        />
      )}

      {executionResult && (
        <ExecutionModal
          result={executionResult}
          onClose={() => setExecutionResult(null)}
          onViewCaseDetails={(caseId) => {
            setExecutionResult(null);
            handleSelectCandidate(caseId);
          }}
        />
      )}

      {activeTab === 'policy' && <PolicyRulesModal onClose={() => setActiveTab('operations')} />}
      {activeTab === 'analytics' && <AnalyticsModal onClose={() => setActiveTab('operations')} />}
      {activeTab === 'settings' && <SettingsModal onClose={() => setActiveTab('operations')} />}

      {/* Global Toast Notifications */}
      <ToastContainer toasts={toasts} onDismiss={removeToast} />
    </div>
  );
}

export default App;
