'use client';

import React, { useState } from 'react';
import { useAuth } from '@clerk/nextjs';
import { getCachedClerkToken } from '../../utils/authToken';
import {
  Box,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  ListItemIcon,
  Typography,
  Chip,
  IconButton,
  TextField,
  InputAdornment,
  Divider,
  Button,
  LinearProgress,
  Stack,
  Tooltip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
} from '@mui/material';
import {
  Article as ArticleIcon,
  Search as SearchIcon,
  Add as AddIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  HourglassEmpty as PendingIcon,
  PlayCircle as ProcessingIcon,
  Delete as DeleteIcon,
  Download as DownloadIcon,
  PictureAsPdf as PdfIcon,
  AutoStories as AutoStoriesIcon,
} from '@mui/icons-material';
import { Job } from '../../types/ui';
import JobRowActions from './JobRowActions';

interface JobSidebarProps {
  jobs: Job[];
  selectedJobId: string | null;
  onJobSelect: (jobId: string) => void;
  onJobDelete: (jobId: number) => void;
  onNewTranslation: () => void;
  onRefreshJobs: (jobId: number) => void | Promise<void>;
  loading?: boolean;
  apiProvider?: 'gemini' | 'openrouter';
  defaultModelName?: string;
  apiKey?: string;
}

const getStatusIcon = (status: string) => {
  switch (status) {
    case 'COMPLETED':
      return <CheckCircleIcon sx={{ color: 'success.main' }} />;
    case 'FAILED':
      return <ErrorIcon sx={{ color: 'error.main' }} />;
    case 'PROCESSING':
      return <ProcessingIcon sx={{ color: 'info.main' }} />;
    case 'PENDING':
      return <PendingIcon sx={{ color: 'text.secondary' }} />;
    default:
      return <ArticleIcon sx={{ color: 'text.secondary' }} />;
  }
};

const getStatusChip = (job: Job) => {
  const statusColors: Record<string, 'success' | 'error' | 'warning' | 'info' | 'default'> = {
    COMPLETED: 'success',
    FAILED: 'error',
    PROCESSING: 'info',
    PENDING: 'warning',
  };

  const chip = (
    <Chip
      label={job.status}
      size="small"
      color={statusColors[job.status] || 'default'}
      sx={{ fontSize: '0.7rem', height: 20 }}
      // Native title as a fallback tooltip if MUI Tooltip isn't available
      title={job.status === 'FAILED' && job.error_message ? job.error_message : undefined}
    />
  );

  // Show detailed error on hover when job failed and error_message exists
  if (job.status === 'FAILED' && job.error_message) {
    return (
      <Tooltip title={job.error_message}>
        <span>{chip}</span>
      </Tooltip>
    );
  }

  return chip;
};

export default function JobSidebar({
  jobs,
  selectedJobId,
  onJobSelect,
  onJobDelete,
  onNewTranslation,
  onRefreshJobs,
  loading = false,
  apiProvider,
  defaultModelName,
  apiKey,
}: JobSidebarProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const { getToken } = useAuth();
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [jobToDelete, setJobToDelete] = useState<Job | null>(null);

  const handleOpenDeleteDialog = (job: Job) => {
    setJobToDelete(job);
    setDeleteDialogOpen(true);
  };

  const handleCloseDeleteDialog = () => {
    setJobToDelete(null);
    setDeleteDialogOpen(false);
  };

  const handleConfirmDelete = () => {
    if (jobToDelete) {
      onJobDelete(jobToDelete.id);
    }
    handleCloseDeleteDialog();
  };

  const filteredJobs = jobs.filter(job =>
    job.filename.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('ko-KR', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <Box
      sx={{
        width: 380,
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        borderRight: 1,
        borderColor: 'divider',
        backgroundColor: 'background.paper',
      }}
    >
      {/* Header */}
      <Box sx={{ p: 2 }}>
        <Typography variant="h6" gutterBottom>
          번역 작업
        </Typography>
        
        {/* Search */}
        <TextField
          fullWidth
          size="small"
          placeholder="작업 검색..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon fontSize="small" />
              </InputAdornment>
            ),
          }}
          sx={{ mb: 2 }}
        />
        
        {/* New Translation Button */}
        <Button
          fullWidth
          variant="contained"
          startIcon={<AddIcon />}
          onClick={onNewTranslation}
          sx={{ mb: 1 }}
        >
          새 번역 시작
        </Button>
      </Box>
      
      <Divider />
      
      {/* Jobs List */}
      <Box sx={{ flex: 1, overflow: 'auto' }}>
        {loading && <LinearProgress />}
        
        {filteredJobs.length === 0 ? (
          <Box sx={{ p: 3, textAlign: 'center' }}>
            <AutoStoriesIcon sx={{ fontSize: 48, color: 'text.disabled', mb: 2 }} />
            <Typography variant="body2" color="text.secondary">
              {searchQuery ? '검색 결과가 없습니다' : '번역 작업이 없습니다'}
            </Typography>
            {!searchQuery && (
              <Button
                size="small"
                sx={{ mt: 1 }}
                onClick={onNewTranslation}
              >
                첫 번역 시작하기
              </Button>
            )}
          </Box>
        ) : (
          <List sx={{ py: 0 }}>
            {filteredJobs.map((job) => {
              const isSelected = job.id.toString() === selectedJobId;
              const isProcessing = job.status === 'PROCESSING' || job.status === 'PENDING';
              const isValidating = job.validation_status === 'IN_PROGRESS';
              const isPostEditing = job.post_edit_status === 'IN_PROGRESS';
              const isIllustrating = job.illustrations_status === 'IN_PROGRESS';
              const showProgress = isProcessing || isValidating || isPostEditing || isIllustrating;
              
              return (
                <ListItem
                  key={job.id}
                  disablePadding
                  sx={{
                    borderLeft: isSelected ? 3 : 0,
                    borderColor: 'primary.main',
                    backgroundColor: isSelected ? 'action.selected' : 'transparent',
                  }}
                  secondaryAction={
                    <Stack direction="row" alignItems="center" spacing={0.5}>
                      {job.status === 'COMPLETED' && (
                        <>
                          <JobRowActions 
                            job={job} 
                            onRefresh={onRefreshJobs} 
                            compact={true}
                            apiProvider={apiProvider}
                            defaultModelName={defaultModelName}
                            apiKey={apiKey}
                          />
                          <Tooltip title="다운로드">
                            <IconButton
                              size="small"
                              onClick={async (e) => {
                                e.stopPropagation();
                                const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
                                try {
                                  const token = await getCachedClerkToken(getToken);
                                  const response = await fetch(`${API_URL}/api/v1/download/${job.id}`, {
                                    headers: {
                                      'Authorization': token ? `Bearer ${token}` : '',
                                    },
                                  });
                                  if (!response.ok) throw new Error('Download failed');
                                  
                                  const blob = await response.blob();
                                  const url = window.URL.createObjectURL(blob);
                                  const a = document.createElement('a');
                                  a.href = url;
                                  a.download = job.filename || `translation_${job.id}.txt`;
                                  document.body.appendChild(a);
                                  a.click();
                                  document.body.removeChild(a);
                                  window.URL.revokeObjectURL(url);
                                } catch (error) {
                                  console.error('Download error:', error);
                                }
                              }}
                            >
                              <DownloadIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="PDF 다운로드">
                            <IconButton
                              size="small"
                              onClick={async (e) => {
                                e.stopPropagation();
                                const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
                                try {
                                  const token = await getCachedClerkToken(getToken);
                                  const response = await fetch(`${API_URL}/api/v1/jobs/${job.id}/pdf?include_source=false&include_illustrations=true`, {
                                    headers: {
                                      'Authorization': token ? `Bearer ${token}` : '',
                                    },
                                  });
                                  if (!response.ok) throw new Error('PDF download failed');
                                  
                                  const blob = await response.blob();
                                  const url = window.URL.createObjectURL(blob);
                                  const a = document.createElement('a');
                                  a.href = url;
                                  const baseFilename = job.filename ? job.filename.replace(/\.[^/.]+$/, '') : `translation_${job.id}`;
                                  a.download = `${baseFilename}.pdf`;
                                  document.body.appendChild(a);
                                  a.click();
                                  document.body.removeChild(a);
                                  window.URL.revokeObjectURL(url);
                                } catch (error) {
                                  console.error('PDF download error:', error);
                                }
                              }}
                            >
                              <PdfIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        </>
                      )}
                      <Tooltip title="삭제">
                        <IconButton
                          edge="end"
                          size="small"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleOpenDeleteDialog(job);
                          }}
                        >
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </Stack>
                  }
                >
                  <ListItemButton
                    onClick={() => onJobSelect(job.id.toString())}
                    selected={isSelected}
                  >
                    <ListItemIcon sx={{ minWidth: 36 }}>
                      {getStatusIcon(job.status)}
                    </ListItemIcon>
                    <ListItemText
                      primary={
                        <Typography
                          variant="body2"
                          noWrap
                          sx={{ fontWeight: isSelected ? 600 : 400 }}
                        >
                          {job.filename}
                        </Typography>
                      }
                      secondary={
                        <Stack spacing={0.5}>
                          <Typography variant="caption" color="text.secondary">
                            {formatDate(job.created_at)}
                          </Typography>
                          <Stack direction="row" spacing={0.5}>
                            {getStatusChip(job)}
                            {job.validation_status === 'COMPLETED' && (
                              <Chip
                                label="검증완료"
                                size="small"
                                color="success"
                                variant="outlined"
                                sx={{ fontSize: '0.7rem', height: 20 }}
                              />
                            )}
                            {job.post_edit_status === 'COMPLETED' && (
                              <Chip
                                label="수정완료"
                                size="small"
                                color="info"
                                variant="outlined"
                                sx={{ fontSize: '0.7rem', height: 20 }}
                              />
                            )}
                            {job.illustrations_status === 'COMPLETED' && (
                              <Chip
                                label="삽화생성완료"
                                size="small"
                                color="warning"
                                variant="outlined"
                                sx={{ fontSize: '0.7rem', height: 20 }}
                              />
                            )}
                          </Stack>
                          {showProgress && (
                            <Box sx={{ mt: 0.5 }}>
                              {isProcessing && job.progress !== undefined && (
                                <Tooltip title={`번역 진행: ${job.progress}%`}>
                                  <LinearProgress
                                    variant="determinate"
                                    value={job.progress}
                                    sx={{ height: 3 }}
                                  />
                                </Tooltip>
                              )}
                              {isValidating && job.validation_progress !== undefined && (
                                <Tooltip title={`검증 진행: ${job.validation_progress}%`}>
                                  <LinearProgress
                                    variant="determinate"
                                    value={job.validation_progress ?? undefined}
                                    color="secondary"
                                    sx={{ height: 3 }}
                                  />
                                </Tooltip>
                              )}
                              {isPostEditing && job.post_edit_progress !== undefined && (
                                <Tooltip title={`수정 진행: ${job.post_edit_progress}%`}>
                                  <LinearProgress
                                    variant="determinate"
                                    value={job.post_edit_progress ?? undefined}
                                    color="info"
                                    sx={{ height: 3 }}
                                  />
                                </Tooltip>
                              )}
                              {isIllustrating && job.illustrations_progress !== undefined && (
                                <Tooltip title={`삽화 생성 진행: ${job.illustrations_progress}%`}>
                                  <LinearProgress
                                    variant="determinate"
                                    value={job.illustrations_progress ?? undefined}
                                    color="warning"
                                    sx={{ height: 3, mt: 0.5 }}
                                  />
                                </Tooltip>
                              )}
                            </Box>
                          )}
                        </Stack>
                      }
                      secondaryTypographyProps={{
                        component: 'div'
                      }}
                    />
                  </ListItemButton>
                </ListItem>
              );
            })}
          </List>
        )}
      </Box>
      <Dialog
        open={deleteDialogOpen}
        onClose={handleCloseDeleteDialog}
        aria-labelledby="alert-dialog-title"
        aria-describedby="alert-dialog-description"
      >
        <DialogTitle id="alert-dialog-title">
          {"작업 삭제"}
        </DialogTitle>
        <DialogContent>
          <DialogContentText id="alert-dialog-description">
            {jobToDelete && `정말로 "${jobToDelete.filename}"을(를) 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.`}
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDeleteDialog}>취소</Button>
          <Button onClick={handleConfirmDelete} autoFocus color="error">
            삭제
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
