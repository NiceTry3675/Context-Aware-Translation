import { useCallback, useState } from 'react';
import { components } from '../../types/api';
import { useAuth, useClerk } from '@clerk/nextjs';
import { getCachedClerkToken } from '../utils/authToken';

interface UseJobActionsOptions {
  apiUrl: string;
  onError?: (error: string) => void;
  onSuccess?: () => void;
}

export function useJobActions({ apiUrl, onError, onSuccess }: UseJobActionsOptions) {
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

  

  const handleTriggerValidation = useCallback(async (
    jobId: number,
    body: components['schemas']['ValidationRequest']
  ) => {
    setLoading(true);
    setError(null);
    try {
      const token = await getCachedClerkToken(getToken);
      const response = await fetch(`${apiUrl}/api/v1/jobs/${jobId}/validation`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
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
  }, [apiUrl, getToken, onError, onSuccess]);

  const handleTriggerPostEdit = useCallback(async (
    jobId: number,
    body: components['schemas']['PostEditRequest']
  ) => {
    setLoading(true);
    setError(null);
    try {
      const token = await getCachedClerkToken(getToken);
      const response = await fetch(`${apiUrl}/api/v1/jobs/${jobId}/post-edit`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
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
  }, [apiUrl, getToken, onError, onSuccess]);

  const handleDownloadValidationReport = useCallback(async (jobId: number) => {
    await handleDownload(
      `${apiUrl}/api/v1/jobs/${jobId}/validation-report`,
      `validation_report_job_${jobId}.json`
    );
  }, [apiUrl, handleDownload]);

  const handleDownloadPostEditLog = useCallback(async (jobId: number) => {
    await handleDownload(
      `${apiUrl}/api/v1/jobs/${jobId}/post-edit-log`,
      `post_edit_log_job_${jobId}.json`
    );
  }, [apiUrl, handleDownload]);

  return {
    handleDownload,
    handleTriggerValidation,
    handleTriggerPostEdit,
    handleDownloadValidationReport,
    handleDownloadPostEditLog,
    loading,
    error,
  };
}