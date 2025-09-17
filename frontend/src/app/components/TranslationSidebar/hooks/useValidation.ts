'use client';

import { useState } from 'react';
import { useAuth } from '@clerk/nextjs';
import { getCachedClerkToken } from '../../../utils/authToken';
import { triggerValidation, type CredentialPayload } from '../../../utils/api';
import type { ApiProvider } from '../../../hooks/useApiKey';

interface UseValidationProps {
  jobId: string;
  onRefresh?: () => void;
  apiProvider?: ApiProvider;
  apiKey?: string;
  vertexProjectId?: string;
  vertexLocation?: string;
  defaultModelName?: string;
}

export function useValidation({ jobId, onRefresh, apiProvider, apiKey, vertexProjectId, vertexLocation, defaultModelName }: UseValidationProps) {
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
      const credentials: CredentialPayload | undefined = apiKey
        ? {
            api_key: apiKey,
            api_provider: apiProvider,
            ...(apiProvider === 'vertex'
              ? {
                  vertex_project_id: vertexProjectId,
                  vertex_location: vertexLocation,
                  vertex_service_account: apiKey,
                }
              : {}),
          }
        : undefined;

      await triggerValidation(jobId, token || undefined, body, credentials);
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
