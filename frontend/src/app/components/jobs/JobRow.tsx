import { useState } from 'react';
import {
  TableRow, TableCell, Typography, Box, Tooltip, IconButton,
  LinearProgress, Chip, CircularProgress
} from '@mui/material';
import {
  Download as DownloadIcon,
  Delete as DeleteIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Pending as PendingIcon,
  MenuBook as MenuBookIcon,
  Visibility as VisibilityIcon,
  FactCheck as FactCheckIcon,
  Assessment as AssessmentIcon,
  Edit as EditIcon,
  Description as DescriptionIcon,
  Chat as ChatIcon,
} from '@mui/icons-material';
import { Job } from '../../types/job';

interface JobRowProps {
  job: Job;
  onDelete: (jobId: number) => void;
  onDownload: (url: string, filename: string) => void;
  onOpenSidebar: (job: Job) => void;
  onTriggerValidation: (jobId: number) => void;
  onTriggerPostEdit: (jobId: number) => void;
  onDownloadValidationReport: (jobId: number) => void;
  onDownloadPostEditLog: (jobId: number) => void;
  devMode?: boolean;
  apiUrl: string;
}

const getStatusIcon = (status: string) => {
  switch (status) {
    case 'COMPLETED': return <CheckCircleIcon color="success" />;
    case 'FAILED': return <ErrorIcon color="error" />;
    case 'PENDING': return <PendingIcon color="warning" />;
    default: return <CircularProgress size={20} />;
  }
};

const formatDuration = (start: string, end: string | null): string => {
  if (!end) return '';
  const startDate = new Date(start);
  const endDate = new Date(end);
  const seconds = Math.floor((endDate.getTime() - startDate.getTime()) / 1000);
  if (seconds < 60) return `${seconds}초`;
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}분 ${remainingSeconds}초`;
};

export default function JobRow({
  job,
  onDelete,
  onDownload,
  onOpenSidebar,
  onTriggerValidation,
  onTriggerPostEdit,
  onDownloadValidationReport,
  onDownloadPostEditLog,
  devMode = false,
  apiUrl
}: JobRowProps) {
  const handleDownloadTranslation = () => {
    const extension = job.filename.toLowerCase().endsWith('.epub') ? 'epub' : 'txt';
    const filename = `${job.filename.split('.')[0]}_translated.${extension}`;
    onDownload(`${apiUrl}/api/v1/jobs/${job.id}/output`, filename);
  };

  const handleDownloadGlossary = () => {
    const filename = `${job.filename.split('.')[0]}_glossary.json`;
    onDownload(`${apiUrl}/api/v1/jobs/${job.id}/glossary`, filename);
  };

  const handleDownloadPromptLogs = () => {
    const filename = `prompts_job_${job.id}_${job.filename.split('.')[0]}.txt`;
    onDownload(`${apiUrl}/api/v1/jobs/${job.id}/logs/prompts`, filename);
  };

  const handleDownloadContextLogs = () => {
    const filename = `context_job_${job.id}_${job.filename.split('.')[0]}.txt`;
    onDownload(`${apiUrl}/api/v1/jobs/${job.id}/logs/context`, filename);
  };

  return (
    <TableRow hover>
      <TableCell component="th" scope="row">
        <Typography variant="body2" noWrap title={job.filename} sx={{ maxWidth: '300px' }}>
          {job.filename}
        </Typography>
        <Typography variant="caption" color="text.secondary">
          {new Date(job.created_at).toLocaleString()}
        </Typography>
      </TableCell>
      <TableCell>
        {job.status === 'FAILED' && job.error_message ? (
          <Tooltip title={job.error_message} arrow>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, cursor: 'help' }}>
              {getStatusIcon(job.status)}
              <Typography variant="body2">
                {job.status}
              </Typography>
            </Box>
          </Tooltip>
        ) : (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            {getStatusIcon(job.status)}
            <Typography variant="body2">
              {job.status} {job.status === 'PROCESSING' && `(${job.progress}%)`}
            </Typography>
          </Box>
        )}
        {job.status === 'PROCESSING' && <LinearProgress variant="determinate" value={job.progress} sx={{ mt: 0.5 }} />}
        
        {job.validation_enabled && (
          <Box sx={{ mt: 1 }}>
            <Chip 
              label={`검증: ${job.validation_status || 'PENDING'}`}
              size="small"
              color={
                job.validation_status === 'COMPLETED' ? 'success' :
                job.validation_status === 'IN_PROGRESS' ? 'warning' :
                job.validation_status === 'FAILED' ? 'error' : 'default'
              }
            />
          </Box>
        )}
        
        {job.post_edit_enabled && (
          <Box sx={{ mt: 0.5 }}>
            <Chip 
              label={`수정: ${job.post_edit_status || 'PENDING'}`}
              size="small"
              color={
                job.post_edit_status === 'COMPLETED' ? 'success' :
                job.post_edit_status === 'IN_PROGRESS' ? 'warning' :
                job.post_edit_status === 'FAILED' ? 'error' : 'default'
              }
            />
          </Box>
        )}
      </TableCell>
      <TableCell>
        {job.status === 'COMPLETED' ? formatDuration(job.created_at, job.completed_at) : '-'}
      </TableCell>
      <TableCell align="right">
        <Box sx={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center' }}>
          {(job.status === 'COMPLETED' || job.status === 'FAILED') && (
            <Tooltip title="번역 파일 다운로드">
              <IconButton color="primary" onClick={handleDownloadTranslation}>
                <DownloadIcon />
              </IconButton>
            </Tooltip>
          )}
          {job.status === 'COMPLETED' && (
            <>
              <Tooltip title="용어집 다운로드">
                <IconButton color="secondary" onClick={handleDownloadGlossary}>
                  <MenuBookIcon />
                </IconButton>
              </Tooltip>
              <Tooltip title="상세 보기">
                <IconButton color="primary" onClick={() => onOpenSidebar(job)}>
                  <VisibilityIcon />
                </IconButton>
              </Tooltip>
            </>
          )}
          
          {job.status === 'COMPLETED' && !job.validation_enabled && (
            <Tooltip title="번역 검증 시작">
              <IconButton color="info" onClick={() => onTriggerValidation(job.id)}>
                <FactCheckIcon />
              </IconButton>
            </Tooltip>
          )}
          {job.validation_status === 'COMPLETED' && (
            <Tooltip title="검증 보고서 다운로드">
              <IconButton color="info" onClick={() => onDownloadValidationReport(job.id)}>
                <AssessmentIcon />
              </IconButton>
            </Tooltip>
          )}
          
          {job.validation_status === 'COMPLETED' && !job.post_edit_enabled && (
            <Tooltip title="자동 수정 시작">
              <IconButton color="success" onClick={() => onTriggerPostEdit(job.id)}>
                <EditIcon />
              </IconButton>
            </Tooltip>
          )}
          {job.post_edit_status === 'COMPLETED' && (
            <Tooltip title="수정 로그 다운로드">
              <IconButton color="success" onClick={() => onDownloadPostEditLog(job.id)}>
                <DescriptionIcon />
              </IconButton>
            </Tooltip>
          )}
          {devMode && (job.status === 'COMPLETED' || job.status === 'FAILED') && (
            <>
              <Tooltip title="프롬프트 로그 다운로드">
                <IconButton size="small" onClick={handleDownloadPromptLogs}>
                  <ChatIcon />
                </IconButton>
              </Tooltip>
              <Tooltip title="컨텍스트 로그 다운로드">
                <IconButton size="small" onClick={handleDownloadContextLogs}>
                  <DescriptionIcon />
                </IconButton>
              </Tooltip>
            </>
          )}
          <Tooltip title="작업 삭제">
            <IconButton onClick={() => onDelete(job.id)}>
              <DeleteIcon />
            </IconButton>
          </Tooltip>
        </Box>
      </TableCell>
    </TableRow>
  );
}