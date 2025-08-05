'use client';

import React from 'react';
import {
  Box,
  Typography,
  Paper,
  LinearProgress,
  Stack,
  Divider,
} from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import { IssueChip } from './IssueChip';

interface StatItem {
  label: string;
  value: number | string;
  total?: number;
  color?: 'primary' | 'secondary' | 'success' | 'error' | 'warning' | 'info';
}

interface IssueStat {
  type: 'critical' | 'missing_content' | 'added_content' | 'name_inconsistencies' | 'success';
  count: number;
  label: string;
}

interface SummaryStatisticsProps {
  title: string;
  stats: StatItem[];
  progressBar?: {
    value: number;
    label: string;
  };
  issueStats?: IssueStat[];
  passFailStats?: {
    passed: number;
    failed: number;
  };
}

export function SummaryStatistics({
  title,
  stats,
  progressBar,
  issueStats,
  passFailStats,
}: SummaryStatisticsProps) {
  return (
    <Paper elevation={1} sx={{ p: 2, mb: 3 }}>
      <Typography variant="h6" gutterBottom>
        {title}
      </Typography>
      
      <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
        {stats.map((stat, index) => (
          <Box key={index} sx={{ flex: 1 }}>
            <Typography variant="body2" color="text.secondary">
              {stat.label}
            </Typography>
            <Typography variant="h4" color={stat.color}>
              {stat.value}
              {stat.total && (
                <Typography component="span" variant="body1" color="text.secondary">
                  /{stat.total}
                </Typography>
              )}
            </Typography>
          </Box>
        ))}
      </Box>

      {progressBar && (
        <Box sx={{ mb: 2 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
            <Typography variant="body2">
              {progressBar.label}
            </Typography>
            <Typography variant="body2" fontWeight="bold">
              {progressBar.value.toFixed(1)}%
            </Typography>
          </Box>
          <LinearProgress 
            variant="determinate" 
            value={progressBar.value} 
            color={progressBar.value >= 80 ? 'success' : progressBar.value >= 60 ? 'warning' : 'error'}
            sx={{ height: 8, borderRadius: 1 }}
          />
        </Box>
      )}

      {passFailStats && (
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Box sx={{ flex: 1 }}>
            <Stack direction="row" spacing={1} alignItems="center">
              <CheckCircleIcon color="success" fontSize="small" />
              <Typography variant="body2">
                통과: {passFailStats.passed}
              </Typography>
            </Stack>
          </Box>
          <Box sx={{ flex: 1 }}>
            <Stack direction="row" spacing={1} alignItems="center">
              <ErrorIcon color="error" fontSize="small" />
              <Typography variant="body2">
                실패: {passFailStats.failed}
              </Typography>
            </Stack>
          </Box>
        </Box>
      )}

      {issueStats && issueStats.length > 0 && (
        <>
          <Divider sx={{ my: 2 }} />
          <Typography variant="subtitle2" gutterBottom>
            발견된 문제
          </Typography>
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            {issueStats.map((issue, index) => (
              issue.count > 0 && (
                <IssueChip
                  key={index}
                  type={issue.type}
                  label={`${issue.label}: ${issue.count}`}
                />
              )
            ))}
          </Stack>
        </>
      )}
    </Paper>
  );
}