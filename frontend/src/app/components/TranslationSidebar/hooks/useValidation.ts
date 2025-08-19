'use client';

import { useState } from 'react';
import { useAuth } from '@clerk/nextjs';
import { getCachedClerkToken } from '../../../utils/authToken';
import { triggerValidation } from '../../../utils/api';

interface UseValidationProps {
  jobId: string;
  onRefresh?: () => void;
  apiProvider?: 'gemini' | 'openrouter';
  defaultModelName?: string;
}

export function useValidation({ jobId, onRefresh, apiProvider, defaultModelName }: UseValidationProps) {
  const [validationDialogOpen, setValidationDialogOpen] = useState(false);
  const [quickValidation, setQuickValidation] = useState(false);
  const [validationSampleRate, setValidationSampleRate] = useState(100);
  const [modelName, setModelName] = useState<string>(defaultModelName || '');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const { getToken } = useAuth();

  const handleTriggerValidation = async () => {
    console.log('Starting validation for job:', jobId);
    console.log('Quick validation:', quickValidation);
    console.log('Validation sample rate:', validationSampleRate);
    
    setLoading(true);
    setError(null);
    
    try {
      const token = await getCachedClerkToken(getToken);
      console.log('Got token:', !!token);
      
      const body = {
        quick_validation: quickValidation,
        validation_sample_rate: validationSampleRate / 100,
        model_name: modelName || defaultModelName,
      };
      await triggerValidation(jobId, token || undefined, body);
      console.log('Validation triggered successfully');
      
      setValidationDialogOpen(false);
      // Lightweight UI kick: public single-job refresh (no JWT)
      onRefresh?.();
      setError(null);
    } catch (err) {
      console.error('Validation error:', err);
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
    modelName,
    setModelName,
    apiProvider,
    loading,
    error,
    handleTriggerValidation,
  };
}
