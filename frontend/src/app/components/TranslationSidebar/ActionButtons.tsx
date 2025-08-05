'use client';

import React from 'react';
import { Stack, Button, Box, LinearProgress, Typography } from '@mui/material';
import AssessmentIcon from '@mui/icons-material/Assessment';
import EditNoteIcon from '@mui/icons-material/EditNote';
import DownloadIcon from '@mui/icons-material/Download';
import { ValidationReport, PostEditLog } from '../../utils/api';

interface ActionButtonsProps {
  canRunValidation: boolean;
  canRunPostEdit: boolean;
  onValidationClick: () => void;
  onPostEditClick: () => void;
  validationReport: ValidationReport | null;
  postEditLog: PostEditLog | null;
  jobId: string;
  loading: boolean;
  validationStatus?: string;
  validationProgress?: number;
}

export default function ActionButtons({
  canRunValidation,
  canRunPostEdit,
  onValidationClick,
  onPostEditClick,
  validationReport,
  postEditLog,
  jobId,
  loading,
  validationStatus,
  validationProgress,
}: ActionButtonsProps) {
  const handleDownloadValidationReport = () => {
    if (!validationReport) return;
    const blob = new Blob([JSON.stringify(validationReport, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `validation_report_${jobId}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleDownloadPostEditLog = () => {
    if (!postEditLog) return;
    const blob = new Blob([JSON.stringify(postEditLog, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `postedit_log_${jobId}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <Stack spacing={2}>
      <Stack direction="row" spacing={2}>
        <Button
          variant="outlined"
          startIcon={<AssessmentIcon />}
          onClick={onValidationClick}
          disabled={!canRunValidation || loading}
        >
          검증 실행
        </Button>
        
        <Button
          variant="outlined"
          startIcon={<EditNoteIcon />}
          onClick={onPostEditClick}
          disabled={!canRunPostEdit || loading}
        >
          포스트 에디팅 실행
        </Button>
      
        {validationReport && (
          <Button
            variant="text"
            startIcon={<DownloadIcon />}
            onClick={handleDownloadValidationReport}
          >
            검증 보고서 다운로드
          </Button>
        )}
        
        {postEditLog && (
          <Button
            variant="text"
            startIcon={<DownloadIcon />}
            onClick={handleDownloadPostEditLog}
          >
            수정 로그 다운로드
          </Button>
        )}
      </Stack>
      
      {validationStatus === 'IN_PROGRESS' && (
        <Box sx={{ mt: 2 }}>
          <Stack direction="row" alignItems="center" spacing={2}>
            <Typography variant="body2" color="text.secondary">
              검증 진행중: {validationProgress !== undefined ? `${validationProgress}%` : '계산중...'}
            </Typography>
          </Stack>
          <LinearProgress 
            variant={validationProgress !== undefined ? "determinate" : "indeterminate"} 
            value={validationProgress} 
            sx={{ mt: 1 }}
          />
        </Box>
      )}
    </Stack>
  );
}