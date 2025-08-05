'use client';

import React from 'react';
import { Chip, CircularProgress } from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import PendingIcon from '@mui/icons-material/Pending';
import ErrorIcon from '@mui/icons-material/Error';

type StatusType = 'validation' | 'postedit';

interface StatusChipsProps {
  validationStatus?: string;
  postEditStatus?: string;
}

export default function StatusChips({ validationStatus, postEditStatus }: StatusChipsProps) {
  const getStatusChip = (status: string | undefined, type: StatusType) => {
    const label = type === 'validation' ? '검증' : '포스트 에디팅';
    
    if (!status || status === 'PENDING') {
      return <Chip size="small" label={`${label} 대기`} icon={<PendingIcon />} />;
    }
    if (status === 'IN_PROGRESS') {
      return <Chip size="small" label={`${label} 진행중`} icon={<CircularProgress size={16} />} color="primary" />;
    }
    if (status === 'COMPLETED') {
      return <Chip size="small" label={`${label} 완료`} icon={<CheckCircleIcon />} color="success" />;
    }
    if (status === 'FAILED') {
      return <Chip size="small" label={`${label} 실패`} icon={<ErrorIcon />} color="error" />;
    }
    return null;
  };

  return (
    <>
      {getStatusChip(validationStatus, 'validation')}
      {getStatusChip(postEditStatus, 'postedit')}
    </>
  );
}