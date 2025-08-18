'use client';

import { useState } from 'react';
import { useAuth } from '@clerk/nextjs';
import { getCachedClerkToken } from '../../../utils/authToken';
import { triggerPostEdit } from '../../../utils/api';

interface UsePostEditProps {
  jobId: string;
  onRefresh?: () => void;
  selectedCases?: Record<number, boolean[]>;
  modelName?: string;
}

export function usePostEdit({ jobId, onRefresh, selectedCases, modelName }: UsePostEditProps) {
  const [postEditDialogOpen, setPostEditDialogOpen] = useState(false);
  // Structured-only: issue types removed
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const { getToken } = useAuth();

  const handleTriggerPostEdit = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const token = await getCachedClerkToken(getToken);
      await triggerPostEdit(jobId, token || undefined, selectedCases || {}, modelName);
      setPostEditDialogOpen(false);
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
    loading,
    error,
    handleTriggerPostEdit,
  };
}
