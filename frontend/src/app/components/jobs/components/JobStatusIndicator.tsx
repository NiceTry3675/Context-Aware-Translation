'use client';

import React from 'react';
import {
  Box,
  Typography,
  Tooltip,
  LinearProgress,
  Chip,
  CircularProgress,
} from '@mui/material';
import {
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Pending as PendingIcon,
} from '@mui/icons-material';

interface JobStatusIndicatorProps {
  status: string;
  errorMessage?: string | null;
  progress?: number;
  validationEnabled?: boolean;
  validationStatus?: string;
  postEditEnabled?: boolean;
  postEditStatus?: string;
}

const getStatusIcon = (status: string) => {
  switch (status) {
    case 'COMPLETED': return <CheckCircleIcon color="success" />;
    case 'FAILED': return <ErrorIcon color="error" />;
    case 'PENDING': return <PendingIcon color="warning" />;
    default: return <CircularProgress size={20} />;
  }
};

export default function JobStatusIndicator({
  status,
  errorMessage,
  progress = 0,
  validationEnabled,
  validationStatus,
  postEditEnabled,
  postEditStatus,
}: JobStatusIndicatorProps) {
  const getChipColor = (status?: string): 'success' | 'warning' | 'error' | 'default' => {
    if (!status) return 'default';
    if (status === 'COMPLETED') return 'success';
    if (status === 'IN_PROGRESS') return 'warning';
    if (status === 'FAILED') return 'error';
    return 'default';
  };

  return (
    <>
      {status === 'FAILED' && errorMessage ? (
        <Tooltip title={errorMessage} arrow>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, cursor: 'help' }}>
            {getStatusIcon(status)}
            <Typography variant="body2">
              {status}
            </Typography>
          </Box>
        </Tooltip>
      ) : (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          {getStatusIcon(status)}
          <Typography variant="body2">
            {status} {status === 'PROCESSING' && `(${progress}%)`}
          </Typography>
        </Box>
      )}
      
      {status === 'PROCESSING' && (
        <LinearProgress variant="determinate" value={progress} sx={{ mt: 0.5 }} />
      )}
      
      {validationEnabled && (
        <Box sx={{ mt: 1 }}>
          <Chip 
            label={`검증: ${validationStatus || 'PENDING'}`}
            size="small"
            color={getChipColor(validationStatus)}
          />
        </Box>
      )}
      
      {postEditEnabled && (
        <Box sx={{ mt: 0.5 }}>
          <Chip 
            label={`수정: ${postEditStatus || 'PENDING'}`}
            size="small"
            color={getChipColor(postEditStatus)}
          />
        </Box>
      )}
    </>
  );
}