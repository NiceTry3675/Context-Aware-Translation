'use client';

import React from 'react';
import { Chip } from '@mui/material';
import ErrorIcon from '@mui/icons-material/Error';
import WarningIcon from '@mui/icons-material/Warning';
import InfoIcon from '@mui/icons-material/Info';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';

type IssueType = 'critical' | 'missing_content' | 'added_content' | 'name_inconsistencies' | 'minor' | 'success';

interface IssueChipProps {
  type: IssueType;
  label: string;
  variant?: 'filled' | 'outlined';
  size?: 'small' | 'medium';
}

export function IssueChip({ type, label, variant = 'outlined', size = 'small' }: IssueChipProps) {
  const getColor = (): 'error' | 'warning' | 'info' | 'success' | 'default' => {
    if (type === 'critical') return 'error';
    if (type === 'missing_content' || type === 'added_content') return 'warning';
    if (type === 'name_inconsistencies') return 'info';
    if (type === 'success') return 'success';
    return 'default';
  };

  const getIcon = () => {
    if (type === 'critical') return <ErrorIcon />;
    if (type === 'missing_content' || type === 'added_content') return <WarningIcon />;
    if (type === 'name_inconsistencies') return <InfoIcon />;
    if (type === 'success') return <CheckCircleIcon />;
    return undefined;
  };

  return (
    <Chip
      size={size}
      icon={getIcon()}
      label={label}
      color={getColor()}
      variant={variant}
    />
  );
}