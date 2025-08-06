'use client';

import React, { useState } from 'react';
import {
  Box,
  IconButton,
  Tooltip,
  CircularProgress,
  Badge,
  Stack,
} from '@mui/material';
import {
  CheckCircle as ValidateIcon,
  Edit as EditIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
} from '@mui/icons-material';
import { Job } from '../../types/job';
import ValidationDialog from '../TranslationSidebar/ValidationDialog';
import PostEditDialog from '../TranslationSidebar/PostEditDialog';
import { useValidation } from '../TranslationSidebar/hooks/useValidation';
import { usePostEdit } from '../TranslationSidebar/hooks/usePostEdit';
import { useTranslationData } from '../TranslationSidebar/hooks/useTranslationData';

interface JobRowActionsProps {
  job: Job;
  onRefresh: () => void;
  compact?: boolean;
}

export default function JobRowActions({ job, onRefresh, compact = false }: JobRowActionsProps) {
  const jobId = job.id.toString();
  
  // Load translation data to get validation report
  const {
    validationReport,
    postEditLog,
    selectedIssues,
    setSelectedIssues,
  } = useTranslationData({
    open: true,
    jobId,
    jobStatus: job.status,
    validationStatus: job.validation_status || undefined,
    postEditStatus: job.post_edit_status || undefined,
  });

  const validation = useValidation({ jobId, onRefresh });
  const postEdit = usePostEdit({ jobId, onRefresh, selectedIssues });

  const canRunValidation = job.status === 'COMPLETED' && 
    (!job.validation_status || job.validation_status === 'FAILED');
  const canRunPostEdit = job.validation_status === 'COMPLETED' && 
    (!job.post_edit_status || job.post_edit_status === 'FAILED');

  // Calculate total issues from validation report
  const calculateIssueCount = () => {
    if (!validationReport) return 0;
    
    let totalIssues = 0;
    validationReport.detailed_results.forEach((result) => {
      totalIssues += result.critical_issues.length;
      totalIssues += result.missing_content.length;
      totalIssues += result.added_content.length;
      totalIssues += result.name_inconsistencies.length;
    });
    
    return totalIssues;
  };

  const issueCount = calculateIssueCount();
  const hasIssues = issueCount > 0;

  // Calculate selected issue counts for post-edit
  const calculateSelectedCounts = () => {
    let critical = 0;
    let missingContent = 0;
    let addedContent = 0;
    let nameInconsistencies = 0;

    if (validationReport) {
      validationReport.detailed_results.forEach((result) => {
        const segmentSelection = selectedIssues?.[result.segment_index];
        
        if (segmentSelection) {
          critical += segmentSelection.critical?.filter(selected => selected).length || 0;
          missingContent += segmentSelection.missing_content?.filter(selected => selected).length || 0;
          addedContent += segmentSelection.added_content?.filter(selected => selected).length || 0;
          nameInconsistencies += segmentSelection.name_inconsistencies?.filter(selected => selected).length || 0;
        } else {
          critical += result.critical_issues.length;
          missingContent += result.missing_content.length;
          addedContent += result.added_content.length;
          nameInconsistencies += result.name_inconsistencies.length;
        }
      });
    }

    return {
      critical,
      missingContent,
      addedContent,
      nameInconsistencies,
      total: critical + missingContent + addedContent + nameInconsistencies
    };
  };

  const selectedCounts = calculateSelectedCounts();

  // Get appropriate icon for validation status
  const getValidationIcon = () => {
    if (job.validation_status === 'IN_PROGRESS') {
      return <CircularProgress size={16} />;
    }
    if (job.validation_status === 'COMPLETED') {
      if (hasIssues) {
        return (
          <Badge badgeContent={issueCount} color="error" max={99}>
            <WarningIcon fontSize="small" color="warning" />
          </Badge>
        );
      }
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
      <Stack direction="row" spacing={0.5} onClick={(e) => e.stopPropagation()}>
        {/* Validation Button */}
        {(canRunValidation || job.validation_status) && (
          <Tooltip title={
            job.validation_status === 'IN_PROGRESS' 
              ? `검증 진행 중 (${job.validation_progress || 0}%)`
              : job.validation_status === 'COMPLETED'
              ? hasIssues ? `${issueCount}개 문제 발견` : '검증 완료 (문제 없음)'
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
      />

      {/* Post-Edit Dialog */}
      <PostEditDialog
        open={postEdit.postEditDialogOpen}
        onClose={() => postEdit.setPostEditDialogOpen(false)}
        onConfirm={postEdit.handleTriggerPostEdit}
        selectedIssueTypes={postEdit.selectedIssueTypes}
        onIssueTypeChange={(issueType, checked) => 
          postEdit.setSelectedIssueTypes({ ...postEdit.selectedIssueTypes, [issueType]: checked })
        }
        validationReport={validationReport}
        loading={postEdit.loading}
        selectedCounts={selectedCounts}
      />
    </>
  );
}