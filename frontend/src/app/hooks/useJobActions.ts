import { useCallback, useState } from 'react';
import { components } from '../../types/api';
import { useAuth, useClerk } from '@clerk/nextjs';
import { getCachedClerkToken } from '../utils/authToken';
import { triggerIllustrationGeneration, generateCharacterBases, selectCharacterBase } from '../utils/api';
import type { ApiProvider } from './useApiKey';

interface UseJobActionsOptions {
  apiUrl: string;
  apiKey?: string;
  apiProvider?: ApiProvider;
  vertexProjectId?: string;
  vertexLocation?: string;
  onError?: (error: string) => void;
  onSuccess?: () => void;
}

export function useJobActions({ apiUrl, apiKey, apiProvider, vertexProjectId, vertexLocation, onError, onSuccess }: UseJobActionsOptions) {
  const { getToken, isSignedIn } = useAuth();
  const { openSignIn } = useClerk();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleDownload = useCallback(async (url: string, filename: string) => {
    if (!isSignedIn) {
      openSignIn({ redirectUrl: '/' });
      return;
    }
    
    try {
      const token = await getCachedClerkToken(getToken);
      if (!token) {
        onError?.("다운로드에 필요한 인증 토큰을 가져올 수 없습니다.");
        return;
      }
      
      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Failed to download file from ${url}`);
      }

      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(downloadUrl);
      
      onSuccess?.();
    } catch (err) {
      onError?.(err instanceof Error ? err.message : "An unknown error occurred during download.");
    }
  }, [isSignedIn, getToken, openSignIn, onError, onSuccess]);


  const buildCredentialPayload = useCallback((overrideKey?: string) => {
    const keyToUse = overrideKey ?? apiKey;
    if (!keyToUse) {
      return {};
    }
    const payload: Record<string, unknown> = {
      api_key: keyToUse,
    };
    if (apiProvider) {
      payload.api_provider = apiProvider;
      if (apiProvider === 'vertex') {
        if (vertexProjectId) {
          payload.vertex_project_id = vertexProjectId;
        }
        if (vertexLocation) {
          payload.vertex_location = vertexLocation;
        }
        payload.vertex_service_account = keyToUse;
      }
    }
    return payload;
  }, [apiKey, apiProvider, vertexProjectId, vertexLocation]);


  const handleTriggerValidation = useCallback(async (
    jobId: number,
    body: components['schemas']['ValidationRequest']
  ) => {
    setLoading(true);
    setError(null);
    try {
      const token = await getCachedClerkToken(getToken);
      const response = await fetch(`${apiUrl}/api/v1/validate/${jobId}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        // Add credential payload inline to ensure backend uses user-provided key
        body: JSON.stringify({ ...(body as any), ...buildCredentialPayload() }),
      });
      
      if (response.ok) {
        onSuccess?.();
      } else {
        const errorData = await response.json();
        const errorMessage = errorData.detail || 'Failed to start validation';
        setError(errorMessage);
        onError?.(errorMessage);
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'An unknown error occurred';
      console.error('Error triggering validation:', error);
      setError(errorMessage);
      onError?.(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [apiUrl, buildCredentialPayload, getToken, onError, onSuccess]);

  const handleTriggerPostEdit = useCallback(async (
    jobId: number,
    body: components['schemas']['PostEditRequest']
  ) => {
    setLoading(true);
    setError(null);
    try {
      const token = await getCachedClerkToken(getToken);
      const response = await fetch(`${apiUrl}/api/v1/post-edit/${jobId}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        // Pass credential payload so post-edit does not rely on server env
        body: JSON.stringify({ ...(body as any), ...buildCredentialPayload() }),
      });
      
      if (response.ok) {
        onSuccess?.();
      } else {
        const errorData = await response.json();
        const errorMessage = errorData.detail || 'Failed to start post-editing';
        setError(errorMessage);
        onError?.(errorMessage);
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'An unknown error occurred';
      console.error('Error triggering post-edit:', error);
      setError(errorMessage);
      onError?.(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [apiUrl, buildCredentialPayload, getToken, onError, onSuccess]);

  const handleDownloadValidationReport = useCallback(async (jobId: number) => {
    await handleDownload(
      `${apiUrl}/api/v1/validation/${jobId}/status`,
      `validation_report_job_${jobId}.json`
    );
  }, [apiUrl, handleDownload]);

  const handleDownloadPostEditLog = useCallback(async (jobId: number) => {
    await handleDownload(
      `${apiUrl}/api/v1/post-edit/${jobId}/status`,
      `post_edit_log_job_${jobId}.json`
    );
  }, [apiUrl, handleDownload]);

  const handleDownloadPdf = useCallback(async (
    jobId: number,
    includeSource: boolean = true,
    includeIllustrations: boolean = true,
    pageSize: string = "A4"
  ) => {
    const params = new URLSearchParams({
      include_source: includeSource.toString(),
      include_illustrations: includeIllustrations.toString(),
      page_size: pageSize
    });
    
    await handleDownload(
      `${apiUrl}/api/v1/jobs/${jobId}/pdf?${params.toString()}`,
      `translation_job_${jobId}.pdf`
    );
  }, [apiUrl, handleDownload]);

  const handleTriggerIllustration = useCallback(async (
    jobId: number,
    overrideApiKey?: string,
    config?: {
      style?: string;
      style_hints?: string;
      min_segment_length?: number;
      skip_dialogue_heavy?: boolean;
      cache_enabled?: boolean;
    },
    maxIllustrations?: number
  ) => {
    setLoading(true);
    setError(null);
    try {
      const token = await getCachedClerkToken(getToken);
      await triggerIllustrationGeneration(
        jobId.toString(),
        buildCredentialPayload(overrideApiKey),
        token || undefined,
        config,
        maxIllustrations
      );
      onSuccess?.();
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'An unknown error occurred';
      console.error('Error triggering illustration generation:', error);
      setError(errorMessage);
      onError?.(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [buildCredentialPayload, getToken, onError, onSuccess]);

  return {
    handleDownload,
    handleTriggerValidation,
    handleTriggerPostEdit,
    handleTriggerIllustration,
    async handleGenerateCharacterBases(jobId: number, overrideApiKey: string, profile: any) {
      setLoading(true);
      setError(null);
      try {
        const token = await getCachedClerkToken(getToken);
        await generateCharacterBases(
          jobId.toString(),
          buildCredentialPayload(overrideApiKey),
          token || undefined,
          profile
        );
        onSuccess?.();
      } catch (error) {
        const msg = error instanceof Error ? error.message : 'An unknown error occurred';
        setError(msg);
        onError?.(msg);
      } finally {
        setLoading(false);
      }
    },
    async handleSelectCharacterBase(jobId: number, selectedIndex: number) {
      setLoading(true);
      setError(null);
      try {
        const token = await getCachedClerkToken(getToken);
        await selectCharacterBase(jobId.toString(), token || undefined, selectedIndex);
        onSuccess?.();
      } catch (error) {
        const msg = error instanceof Error ? error.message : 'An unknown error occurred';
        setError(msg);
        onError?.(msg);
      } finally {
        setLoading(false);
      }
    },
    handleDownloadValidationReport,
    handleDownloadPostEditLog,
    handleDownloadPdf,
    loading,
    error,
  };
}
