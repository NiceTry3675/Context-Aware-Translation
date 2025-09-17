'use client';

import React, { useState, useEffect } from 'react';
import { useAuth } from '@clerk/nextjs';
import { getCachedClerkToken } from '../../utils/authToken';
import {
  Box,
  IconButton,
  Tooltip,
  CircularProgress,
  Stack,
} from '@mui/material';
import {
  CheckCircle as ValidateIcon,
  Edit as EditIcon,
  Error as ErrorIcon,
} from '@mui/icons-material';
import { Job } from '../../types/ui';
import ValidationDialog from '../TranslationSidebar/ValidationDialog';
import PostEditDialog from '../TranslationSidebar/PostEditDialog';
import { useJobActions } from '../../hooks/useJobActions';
import { fetchValidationReport, ValidationReport, fetchJobTasks } from '../../utils/api';
import RefreshIcon from '@mui/icons-material/Refresh';
import type { ApiProvider } from '../../hooks/useApiKey';

interface JobRowActionsProps {
  job: Job;
  onRefresh: (jobId: number) => void | Promise<void>;
  compact?: boolean;
  apiProvider?: ApiProvider;
  defaultModelName?: string;
  apiKey?: string;
  vertexProjectId?: string;
  vertexLocation?: string;
}

export default function JobRowActions({ job, onRefresh, compact = false, apiProvider, defaultModelName, apiKey, vertexProjectId, vertexLocation }: JobRowActionsProps) {
  const onRowRefresh = () => onRefresh(job.id);
  const jobId = job.id.toString();
  
  // State for dialogs and their options, managed locally
  const [validationDialogOpen, setValidationDialogOpen] = useState(false);
  const [quickValidation, setQuickValidation] = useState(false);
  const [validationSampleRate, setValidationSampleRate] = useState(100);
  const [validationModelName, setValidationModelName] = useState<string>('');

  const [postEditDialogOpen, setPostEditDialogOpen] = useState(false);
  const [postEditModelName, setPostEditModelName] = useState<string>('');

  // State for validation report - loaded on demand for post-edit
  const [validationReport, setValidationReport] = useState<ValidationReport | null>(null);
  const [selectedCases, setSelectedCases] = useState<Record<number, boolean[]>>({});
  const [loadingReport, setLoadingReport] = useState(false);

  const { handleTriggerValidation, handleTriggerPostEdit } = useJobActions({
    apiUrl: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
    apiKey,
    apiProvider,
    vertexProjectId,
    vertexLocation,
    onSuccess: onRowRefresh,
    onError: (error) => console.error(error),
  });

  const onConfirmValidation = () => {
    handleTriggerValidation(job.id, {
      quick_validation: quickValidation,
      validation_sample_rate: validationSampleRate / 100,
      model_name: validationModelName || defaultModelName,
    });
    setValidationDialogOpen(false);
  };

  const onConfirmPostEdit = () => {
    handleTriggerPostEdit(job.id, {
      selected_cases: selectedCases || {},
      model_name: postEditModelName || defaultModelName,
    });
    setPostEditDialogOpen(false);
  };

  const { getToken } = useAuth();
  const [tasks, setTasks] = useState<import('../../../types/api').components['schemas']['TaskExecutionResponse'][]>([]);

  // Poll tasks when relevant phases are IN_PROGRESS
  useEffect(() => {
    let timer: NodeJS.Timeout | null = null;
    const load = async () => {
      try {
        const token = await getCachedClerkToken(getToken);
        const list = await fetchJobTasks(job.id, token || undefined);
        setTasks(list);
      } catch (e) {
        // silent fail to avoid noisy UI
      }
    };
    if (job.validation_status === 'IN_PROGRESS' || job.post_edit_status === 'IN_PROGRESS' || job.illustrations_status === 'IN_PROGRESS') {
      load();
      timer = setInterval(load, 10000);
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [job.id, job.validation_status, job.post_edit_status, job.illustrations_status, getToken]);

  const hasActive = (kind: string) =>
    tasks.some(t => t.kind === (kind as any) && ['PENDING', 'STARTED', 'RETRY', 'running'].includes((t.celery_state || '').toUpperCase()));

  const validationStalled = job.validation_status === 'IN_PROGRESS' && !hasActive('validation');
  const postEditStalled = job.post_edit_status === 'IN_PROGRESS' && !hasActive('post_edit');

  const canRunValidation = job.status === 'COMPLETED' && 
    job.validation_status !== 'IN_PROGRESS';
  const canRunPostEdit = job.validation_status === 'COMPLETED' && 
    (!job.post_edit_status || job.post_edit_status === 'FAILED');

  // Load validation report when post-edit dialog opens
  useEffect(() => {
    if (postEditDialogOpen && job.validation_status === 'COMPLETED' && !validationReport && !loadingReport) {
      setLoadingReport(true);
      getCachedClerkToken(getToken)
        .then(token => fetchValidationReport(jobId, token || undefined))
        .then(report => {
          if (report) {
            setValidationReport(report);
            // Auto-select all cases for post-editing from job row
            const newSelectedCases: Record<number, boolean[]> = {};
            report.detailed_results?.forEach((result: any) => {
              if (result.structured_cases && result.structured_cases.length > 0) {
                newSelectedCases[result.segment_index] = new Array(result.structured_cases.length).fill(true);
              }
            });
            setSelectedCases(newSelectedCases);
          }
        })
        .catch(err => console.error('Failed to load validation report:', err))
        .finally(() => setLoadingReport(false));
    }
  }, [postEditDialogOpen, job.validation_status, validationReport, loadingReport, jobId, getToken]);

  // Calculate selected counts
  const selectedCounts = {
    total: Object.values(selectedCases).reduce((acc, arr) => acc + (arr?.filter(Boolean).length || 0), 0)
  };

  // Get appropriate icon for validation status
  const getValidationIcon = () => {
    if (job.validation_status === 'IN_PROGRESS') {
      return <CircularProgress size={16} />;
    }
    if (job.validation_status === 'COMPLETED') {
      // We don't show issue count in sidebar to prevent loading data for all jobs
      return <ValidateIcon fontSize="small" color="success" />;
    }
    if (job.validation_status === 'FAILED') {
      return <ErrorIcon fontSize="small" color="error" />;
    }
    return <ValidateIcon fontSize="small" />;
  };

  // Get appropriate icon for post-edit status
  const getPostEditIcon = () => {
    if (job.post_edit_status === 'IN_PROGRESS') {
      return <CircularProgress size={16} />;
    }
    if (job.post_edit_status === 'COMPLETED') {
      return <EditIcon fontSize="small" color="info" />;
    }
    if (job.post_edit_status === 'FAILED') {
      return <ErrorIcon fontSize="small" color="error" />;
    }
    return <EditIcon fontSize="small" />;
  };

  if (compact) {
    return (
      <>
        <Stack direction="row" spacing={0.5} onClick={(e) => e.stopPropagation()}>
          {/* Validation Button */}
          {(canRunValidation || job.validation_status) && (
            <Tooltip title={
              job.validation_status === 'IN_PROGRESS' 
                ? `검증 진행 중 (${job.validation_progress || 0}%)`
                : job.validation_status === 'COMPLETED'
                ? '검증 완료'
                : job.validation_status === 'FAILED'
                ? '검증 실패'
                : '검증 실행'
            }>
              <span>
                <IconButton
                  size="small"
                  onClick={() => setValidationDialogOpen(true)}
                  disabled={!canRunValidation || job.validation_status === 'IN_PROGRESS'}
                  sx={{ p: 0.5 }}
                >
                  {getValidationIcon()}
                </IconButton>
              </span>
            </Tooltip>
          )}

          {/* Validation Retry when stalled */}
          {validationStalled && (
            <Tooltip title="검증 재시도 (작업이 멈춘 경우)">
              <span>
                <IconButton
                  size="small"
                  sx={{ p: 0.5 }}
                  onClick={(e) => {
                    e.stopPropagation();
                    handleTriggerValidation(job.id, {
                      quick_validation: Boolean((job as any).quick_validation),
                      validation_sample_rate: Number((job as any).validation_sample_rate || 100) / 100,
                      model_name: defaultModelName,
                    });
                  }}
                >
                  <RefreshIcon fontSize="small" />
                </IconButton>
              </span>
            </Tooltip>
          )}

          {/* Post-Edit Button */}
          {(canRunPostEdit || job.post_edit_status) && (
            <Tooltip title={
              job.post_edit_status === 'IN_PROGRESS'
                ? `포스트에디팅 진행 중 (${job.post_edit_progress || 0}%)`
                : job.post_edit_status === 'COMPLETED'
                ? '포스트에디팅 완료'
                : job.post_edit_status === 'FAILED'
                ? '포스트에디팅 실패'
                : '포스트에디팅 실행'
            }>
              <span>
                <IconButton
                  size="small"
                  onClick={() => setPostEditDialogOpen(true)}
                  disabled={!canRunPostEdit || job.post_edit_status === 'IN_PROGRESS'}
                  sx={{ p: 0.5 }}
                >
                  {getPostEditIcon()}
                </IconButton>
              </span>
            </Tooltip>
          )}

          {/* Optional: Post-Edit Retry when stalled */}
          {postEditStalled && (
            <Tooltip title="포스트에디팅 재시도 (작업이 멈춘 경우)">
              <span>
                <IconButton
                  size="small"
                  sx={{ p: 0.5 }}
                  onClick={(e) => {
                    e.stopPropagation();
                    handleTriggerPostEdit(job.id, {
                      selected_cases: {},
                      default_select_all: true,
                      model_name: defaultModelName,
                    } as any);
                  }}
                >
                  <RefreshIcon fontSize="small" />
                </IconButton>
              </span>
            </Tooltip>
          )}
        </Stack>

        {/* Validation Dialog */}
        <ValidationDialog
          open={validationDialogOpen}
          onClose={() => setValidationDialogOpen(false)}
          onConfirm={onConfirmValidation}
          quickValidation={quickValidation}
          onQuickValidationChange={setQuickValidation}
          validationSampleRate={validationSampleRate}
          onValidationSampleRateChange={setValidationSampleRate}
          loading={loadingReport} // Or a dedicated loading state if available
          apiProvider={apiProvider}
          modelName={validationModelName || defaultModelName}
          onModelNameChange={setValidationModelName}
        />

        {/* Post-Edit Dialog */}
        <PostEditDialog
          open={postEditDialogOpen}
          onClose={() => setPostEditDialogOpen(false)}
          onConfirm={onConfirmPostEdit}
          validationReport={validationReport}
          loading={loadingReport}
          selectedCounts={selectedCounts}
          apiProvider={apiProvider}
          modelName={postEditModelName || defaultModelName}
          onModelNameChange={setPostEditModelName}
        />
      </>
    );
  }

  return (
    <>
      <Box sx={{ display: 'flex', gap: 1 }}>
        {/* Validation Button */}
        {(canRunValidation || job.validation_status) && (
          <Tooltip title="검증 실행">
            <span>
              <IconButton
                onClick={() => setValidationDialogOpen(true)}
                disabled={!canRunValidation || job.validation_status === 'IN_PROGRESS'}
                color={job.validation_status === 'COMPLETED' ? 'success' : 'default'}
              >
                {getValidationIcon()}
              </IconButton>
            </span>
          </Tooltip>
        )}

        {/* Post-Edit Button */}
        {(canRunPostEdit || job.post_edit_status) && (
          <Tooltip title="포스트에디팅 실행">
            <span>
              <IconButton
                onClick={() => setPostEditDialogOpen(true)}
                disabled={!canRunPostEdit || job.post_edit_status === 'IN_PROGRESS'}
                color={job.post_edit_status === 'COMPLETED' ? 'info' : 'default'}
              >
                {getPostEditIcon()}
              </IconButton>
            </span>
          </Tooltip>
        )}
      </Box>

      {/* Validation Dialog */}
      <ValidationDialog
        open={validationDialogOpen}
        onClose={() => setValidationDialogOpen(false)}
        onConfirm={onConfirmValidation}
        quickValidation={quickValidation}
        onQuickValidationChange={setQuickValidation}
        validationSampleRate={validationSampleRate}
        onValidationSampleRateChange={setValidationSampleRate}
        loading={loadingReport} // Or a dedicated loading state if available
        apiProvider={apiProvider}
        modelName={validationModelName || defaultModelName}
        onModelNameChange={setValidationModelName}
      />

      {/* Post-Edit Dialog */}
      <PostEditDialog
        open={postEditDialogOpen}
        onClose={() => setPostEditDialogOpen(false)}
        onConfirm={onConfirmPostEdit}
        validationReport={validationReport}
        loading={loadingReport}
        selectedCounts={selectedCounts}
        apiProvider={apiProvider}
        modelName={postEditModelName || defaultModelName}
        onModelNameChange={setPostEditModelName}
      />
    </>
  );
}
