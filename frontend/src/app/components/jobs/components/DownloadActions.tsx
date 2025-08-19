'use client';

import React from 'react';
import { Box, Tooltip, IconButton } from '@mui/material';
import {
  Download as DownloadIcon,
  Delete as DeleteIcon,
  MenuBook as MenuBookIcon,
  Visibility as VisibilityIcon,
  FactCheck as FactCheckIcon,
  Assessment as AssessmentIcon,
  Edit as EditIcon,
  Description as DescriptionIcon,
  Chat as ChatIcon,
} from '@mui/icons-material';
import { Job } from '../../../types/ui';

interface DownloadActionsProps {
  job: Job;
  onDownloadTranslation: () => void;
  onDownloadGlossary: () => void;
  onDownloadPromptLogs: () => void;
  onDownloadContextLogs: () => void;
  onDownloadValidationReport: () => void;
  onDownloadPostEditLog: () => void;
  onOpenSidebar: () => void;
  onTriggerValidation: () => void;
  onTriggerPostEdit: () => void;
  onDelete: () => void;
  devMode?: boolean;
}

export default function DownloadActions({
  job,
  onDownloadTranslation,
  onDownloadGlossary,
  onDownloadPromptLogs,
  onDownloadContextLogs,
  onDownloadValidationReport,
  onDownloadPostEditLog,
  onOpenSidebar,
  onTriggerValidation,
  onTriggerPostEdit,
  onDelete,
  devMode = false,
}: DownloadActionsProps) {
  return (
    <Box sx={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center' }}>
      {(job.status === 'COMPLETED' || job.status === 'FAILED') && (
        <Tooltip title="번역 파일 다운로드">
          <IconButton color="primary" onClick={onDownloadTranslation}>
            <DownloadIcon />
          </IconButton>
        </Tooltip>
      )}
      
      {job.status === 'COMPLETED' && (
        <>
          <Tooltip title="용어집 다운로드">
            <IconButton color="secondary" onClick={onDownloadGlossary}>
              <MenuBookIcon />
            </IconButton>
          </Tooltip>
          <Tooltip title="캔버스에서 보기">
            <IconButton color="primary" onClick={onOpenSidebar}>
              <VisibilityIcon />
            </IconButton>
          </Tooltip>
        </>
      )}
      
      {job.status === 'COMPLETED' && !job.validation_enabled && (
        <Tooltip title="번역 검증 시작">
          <IconButton color="info" onClick={onTriggerValidation}>
            <FactCheckIcon />
          </IconButton>
        </Tooltip>
      )}
      
      {job.validation_status === 'COMPLETED' && (
        <Tooltip title="검증 보고서 다운로드">
          <IconButton color="info" onClick={onDownloadValidationReport}>
            <AssessmentIcon />
          </IconButton>
        </Tooltip>
      )}
      
      {job.validation_status === 'COMPLETED' && !job.post_edit_enabled && (
        <Tooltip title="자동 수정 시작">
          <IconButton color="success" onClick={onTriggerPostEdit}>
            <EditIcon />
          </IconButton>
        </Tooltip>
      )}
      
      {job.post_edit_status === 'COMPLETED' && (
        <Tooltip title="수정 로그 다운로드">
          <IconButton color="success" onClick={onDownloadPostEditLog}>
            <DescriptionIcon />
          </IconButton>
        </Tooltip>
      )}
      
      {devMode && (job.status === 'COMPLETED' || job.status === 'FAILED') && (
        <>
          <Tooltip title="프롬프트 로그 다운로드">
            <IconButton size="small" onClick={onDownloadPromptLogs}>
              <ChatIcon />
            </IconButton>
          </Tooltip>
          <Tooltip title="컨텍스트 로그 다운로드">
            <IconButton size="small" onClick={onDownloadContextLogs}>
              <DescriptionIcon />
            </IconButton>
          </Tooltip>
        </>
      )}
      
      <Tooltip title="작업 삭제">
        <IconButton onClick={onDelete}>
          <DeleteIcon />
        </IconButton>
      </Tooltip>
    </Box>
  );
}