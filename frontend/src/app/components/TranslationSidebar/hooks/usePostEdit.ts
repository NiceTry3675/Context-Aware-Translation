'use client';

import { useState } from 'react';
import { useAuth } from '@clerk/nextjs';
import { triggerPostEdit } from '../../../utils/api';

interface UsePostEditProps {
  jobId: string;
  onRefresh?: () => void;
  selectedIssues: {
    [segmentIndex: number]: {
      [issueType: string]: boolean[]
    }
  };
}

export function usePostEdit({ jobId, onRefresh, selectedIssues }: UsePostEditProps) {
  const [postEditDialogOpen, setPostEditDialogOpen] = useState(false);
  const [selectedIssueTypes, setSelectedIssueTypes] = useState({
    critical_issues: true,
    missing_content: true,
    added_content: true,
    name_inconsistencies: true,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const { getToken } = useAuth();

  const handleTriggerPostEdit = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const token = await getToken();
      await triggerPostEdit(jobId, token || undefined, selectedIssueTypes, selectedIssues);
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
    selectedIssueTypes,
    setSelectedIssueTypes,
    loading,
    error,
    handleTriggerPostEdit,
  };
}