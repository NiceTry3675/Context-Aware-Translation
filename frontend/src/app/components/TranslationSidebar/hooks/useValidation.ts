'use client';

import { useState } from 'react';
import { useAuth } from '@clerk/nextjs';
import { triggerValidation } from '../../../utils/api';

interface UseValidationProps {
  jobId: string;
  onRefresh?: () => void;
}

export function useValidation({ jobId, onRefresh }: UseValidationProps) {
  const [validationDialogOpen, setValidationDialogOpen] = useState(false);
  const [quickValidation, setQuickValidation] = useState(false);
  const [validationSampleRate, setValidationSampleRate] = useState(100);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const { getToken } = useAuth();

  const handleTriggerValidation = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const token = await getToken();
      await triggerValidation(jobId, token || undefined, quickValidation, validationSampleRate / 100);
      setValidationDialogOpen(false);
      onRefresh?.();
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : '검증 시작 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  return {
    validationDialogOpen,
    setValidationDialogOpen,
    quickValidation,
    setQuickValidation,
    validationSampleRate,
    setValidationSampleRate,
    loading,
    error,
    handleTriggerValidation,
  };
}