'use client';

import { useState } from 'react';
import { useAuth } from '@clerk/nextjs';
import { getCachedClerkToken } from '../../../utils/authToken';
import { triggerPostEdit } from '../../../utils/api';
import type { ApiProvider } from '../../../hooks/useApiKey';

interface UsePostEditProps {
  jobId: string;
  onRefresh?: () => void;
  selectedCases?: Record<number, boolean[]>;
  modifiedCases?: Record<number, Array<{ reason?: string; recommend_korean_sentence?: string }>>;
  apiProvider?: ApiProvider;
  apiKey?: string;
  providerConfig?: string;
  defaultModelName?: string;
}

export function usePostEdit({ jobId, onRefresh, selectedCases, modifiedCases, apiProvider, apiKey, providerConfig, defaultModelName }: UsePostEditProps) {
  const [postEditDialogOpen, setPostEditDialogOpen] = useState(false);
  // Structured-only: issue types removed
  const [modelName, setModelName] = useState<string>(defaultModelName || '');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const { getToken } = useAuth();

  const handleTriggerPostEdit = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const token = await getCachedClerkToken(getToken);
      const body = {
        selected_cases: selectedCases || {},
        modified_cases: modifiedCases || {},
        model_name: modelName || defaultModelName,
        default_select_all: true,
      } as any;
      if ((apiProvider || 'gemini') !== 'vertex' && !apiKey) {
        setError('포스트 에디팅을 실행하려면 API 키가 필요합니다.');
        setLoading(false);
        return;
      }
      if ((apiProvider || 'gemini') === 'vertex' && (!providerConfig || !providerConfig.trim())) {
        setError('Vertex 서비스 계정 JSON이 필요합니다.');
        setLoading(false);
        return;
      }
      await triggerPostEdit({
        jobId,
        token: token || undefined,
        body,
        apiProvider: apiProvider || 'gemini',
        apiKey: apiProvider === 'vertex' ? '' : apiKey,
        providerConfig: apiProvider === 'vertex' ? providerConfig : undefined,
      });
      setPostEditDialogOpen(false);
      // Lightweight UI kick: public single-job refresh (no JWT)
      onRefresh?.();
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : '포스트 에디팅 시작 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  return {
    postEditDialogOpen,
    setPostEditDialogOpen,
    // no issue-types in structured flow
    modelName,
    setModelName,
    apiProvider,
    loading,
    error,
    handleTriggerPostEdit,
  };
}
