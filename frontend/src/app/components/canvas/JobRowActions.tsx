'use client';

import React, { useState, useEffect } from 'react';
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
import { useValidation } from '../TranslationSidebar/hooks/useValidation';
import { usePostEdit } from '../TranslationSidebar/hooks/usePostEdit';
import { useAuth } from '@clerk/nextjs';
import { fetchValidationReport, ValidationReport } from '../../utils/api';
import { getCachedClerkToken } from '../../utils/authToken';

interface JobRowActionsProps {
  job: Job;
  onRefresh: (jobId: number) => void | Promise<void>;
  compact?: boolean;
  apiProvider?: 'gemini' | 'openrouter';
  defaultModelName?: string;
}

export default function JobRowActions({ job, onRefresh, compact = false, apiProvider, defaultModelName }: JobRowActionsProps) {
  const jobId = job.id.toString();
  const { getToken } = useAuth();
  const onRowRefresh = () => onRefresh(job.id);
  
  // State for validation report - loaded on demand
  const [validationReport, setValidationReport] = useState<ValidationReport | null>(null);
  const [selectedCases, setSelectedCases] = useState<Record<number, boolean[]>>({});
  const [loadingReport, setLoadingReport] = useState(false);

  const validation = useValidation({ jobId, onRefresh: onRowRefresh, apiProvider, defaultModelName });
  const postEdit = usePostEdit({ jobId, onRefresh: onRowRefresh, selectedCases, apiProvider, defaultModelName });

  const canRunValidation = job.status === 'COMPLETED' && 
    (!job.validation_status || job.validation_status === 'FAILED');
  const canRunPostEdit = job.validation_status === 'COMPLETED' && 
    (!job.post_edit_status || job.post_edit_status === 'FAILED');

  // Load validation report when post-edit dialog opens
  useEffect(() => {
    if (postEdit.postEditDialogOpen && job.validation_status === 'COMPLETED' && !validationReport && !loadingReport) {
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
  }, [postEdit.postEditDialogOpen, job.validation_status, validationReport, loadingReport, jobId, getToken]);

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
                  onClick={() => validation.setValidationDialogOpen(true)}
                  disabled={!canRunValidation || job.validation_status === 'IN_PROGRESS'}
                  sx={{ p: 0.5 }}
                >
                  {getValidationIcon()}
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
                  onClick={() => postEdit.setPostEditDialogOpen(true)}
                  disabled={!canRunPostEdit || job.post_edit_status === 'IN_PROGRESS'}
                  sx={{ p: 0.5 }}
                >
                  {getPostEditIcon()}
                </IconButton>
              </span>
            </Tooltip>
          )}
        </Stack>

        {/* Validation Dialog */}
        <ValidationDialog
          open={validation.validationDialogOpen}
          onClose={() => validation.setValidationDialogOpen(false)}
          onConfirm={validation.handleTriggerValidation}
          quickValidation={validation.quickValidation}
          onQuickValidationChange={validation.setQuickValidation}
          validationSampleRate={validation.validationSampleRate}
          onValidationSampleRateChange={validation.setValidationSampleRate}
          loading={validation.loading}
          apiProvider={validation.apiProvider}
          modelName={validation.modelName || defaultModelName}
          onModelNameChange={validation.setModelName}
        />

        {/* Post-Edit Dialog */}
        <PostEditDialog
          open={postEdit.postEditDialogOpen}
          onClose={() => postEdit.setPostEditDialogOpen(false)}
          onConfirm={postEdit.handleTriggerPostEdit}
          validationReport={validationReport}
          loading={postEdit.loading || loadingReport}
          selectedCounts={selectedCounts}
          apiProvider={postEdit.apiProvider}
          modelName={postEdit.modelName || defaultModelName}
          onModelNameChange={postEdit.setModelName}
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
                onClick={() => validation.setValidationDialogOpen(true)}
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
                onClick={() => postEdit.setPostEditDialogOpen(true)}
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
        open={validation.validationDialogOpen}
        onClose={() => validation.setValidationDialogOpen(false)}
        onConfirm={validation.handleTriggerValidation}
        quickValidation={validation.quickValidation}
        onQuickValidationChange={validation.setQuickValidation}
        validationSampleRate={validation.validationSampleRate}
        onValidationSampleRateChange={validation.setValidationSampleRate}
        loading={validation.loading}
        apiProvider={validation.apiProvider}
        modelName={validation.modelName || defaultModelName}
        onModelNameChange={validation.setModelName}
      />

      {/* Post-Edit Dialog */}
      <PostEditDialog
        open={postEdit.postEditDialogOpen}
        onClose={() => postEdit.setPostEditDialogOpen(false)}
        onConfirm={postEdit.handleTriggerPostEdit}
        validationReport={validationReport}
        loading={postEdit.loading}
        selectedCounts={selectedCounts}
        apiProvider={postEdit.apiProvider}
        modelName={postEdit.modelName || defaultModelName}
        onModelNameChange={postEdit.setModelName}
      />
    </>
  );
}
