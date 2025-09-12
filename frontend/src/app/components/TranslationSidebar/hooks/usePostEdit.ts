'use client';

import { useState } from 'react';
import { useAuth } from '@clerk/nextjs';
import { getCachedClerkToken } from '../../../utils/authToken';
import { triggerPostEdit } from '../../../utils/api';

interface UsePostEditProps {
  jobId: string;
  onRefresh?: () => void;
  selectedCases?: Record<number, boolean[]>;
  modifiedCases?: Record<number, Array<{ reason?: string; recommend_korean_sentence?: string }>>;
  apiProvider?: 'gemini' | 'openrouter';
  defaultModelName?: string;
}

export function usePostEdit({ jobId, onRefresh, selectedCases, modifiedCases, apiProvider, defaultModelName }: UsePostEditProps) {
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
      await triggerPostEdit(jobId, token || undefined, body);
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
