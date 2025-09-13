'use client';

import React, { useCallback } from 'react';
import {
  Box,
  Paper,
  IconButton,
  Typography,
  Stack,
  TextField,
  Tooltip,
  LinearProgress,
} from '@mui/material';
import {
  NavigateBefore as PrevIcon,
  NavigateNext as NextIcon,
  FirstPage as FirstIcon,
  LastPage as LastIcon,
  Keyboard as KeyboardIcon,
} from '@mui/icons-material';

interface SegmentNavigationProps {
  currentSegmentIndex: number;
  totalSegments: number;
  onSegmentChange: (index: number) => void;
  loading?: boolean;
}

export default function SegmentNavigation({
  currentSegmentIndex,
  totalSegments,
  onSegmentChange,
  loading = false,
}: SegmentNavigationProps) {
  const [jumpToValue, setJumpToValue] = React.useState('');

  // Navigation functions
  const goToFirst = useCallback(() => onSegmentChange(0), [onSegmentChange]);
  const goToLast = useCallback(() => onSegmentChange(totalSegments - 1), [onSegmentChange, totalSegments]);
  const goToPrevious = useCallback(() => {
    if (currentSegmentIndex > 0) {
      onSegmentChange(currentSegmentIndex - 1);
    }
  }, [currentSegmentIndex, onSegmentChange]);
  const goToNext = useCallback(() => {
    if (currentSegmentIndex < totalSegments - 1) {
      onSegmentChange(currentSegmentIndex + 1);
    }
  }, [currentSegmentIndex, totalSegments, onSegmentChange]);

  // Handle jump to segment
  const handleJumpTo = (e: React.FormEvent) => {
    e.preventDefault();
    const segmentNumber = parseInt(jumpToValue);
    if (!isNaN(segmentNumber) && segmentNumber >= 1 && segmentNumber <= totalSegments) {
      onSegmentChange(segmentNumber - 1); // Convert to 0-based index
      setJumpToValue('');
    }
  };

  // Keyboard navigation
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't navigate if user is typing in an input
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return;
      }

      switch (e.key) {
        case 'ArrowLeft':
          e.preventDefault();
          goToPrevious();
          break;
        case 'ArrowRight':
          e.preventDefault();
          goToNext();
          break;
        case 'Home':
          if (e.ctrlKey) {
            e.preventDefault();
            goToFirst();
          }
          break;
        case 'End':
          if (e.ctrlKey) {
            e.preventDefault();
            goToLast();
          }
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [currentSegmentIndex, totalSegments, goToPrevious, goToNext, goToFirst, goToLast]);

  // Calculate progress
  const progress = totalSegments > 0 ? ((currentSegmentIndex + 1) / totalSegments) * 100 : 0;

  return (
    <Paper 
      elevation={1} 
      sx={{ 
        p: 2, 
        position: 'sticky',
        bottom: 0,
        zIndex: 5,
        bgcolor: 'background.paper',
      }}
    >
      <Stack spacing={2}>
        {/* Progress Bar */}
        <Box>
          <Stack direction="row" justifyContent="space-between" alignItems="center" mb={0.5}>
            <Typography variant="caption" color="text.secondary">
              진행률
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {currentSegmentIndex + 1} / {totalSegments}
            </Typography>
          </Stack>
          <LinearProgress 
            variant="determinate" 
            value={progress} 
            sx={{ height: 6, borderRadius: 1 }}
          />
        </Box>

        {/* Navigation Controls */}
        <Stack direction="row" alignItems="center" justifyContent="space-between">
          {/* Left: Navigation Buttons */}
          <Stack direction="row" spacing={1} alignItems="center">
            <Tooltip title="첫 세그먼트 (Ctrl+Home)">
              <span>
                <IconButton 
                  onClick={goToFirst}
                  disabled={currentSegmentIndex === 0 || loading}
                  size="small"
                  aria-label="첫 세그먼트로 이동"
                >
                  <FirstIcon />
                </IconButton>
              </span>
            </Tooltip>
            
            <Tooltip title="이전 세그먼트 (←)">
              <span>
                <IconButton 
                  onClick={goToPrevious}
                  disabled={currentSegmentIndex === 0 || loading}
                  aria-label="이전 세그먼트로 이동"
                >
                  <PrevIcon />
                </IconButton>
              </span>
            </Tooltip>

            {/* Current Position Display */}
            <Box 
              sx={{ 
                px: 2, 
                py: 0.5, 
                bgcolor: 'primary.main',
                color: 'primary.contrastText',
                borderRadius: 2,
                minWidth: 100,
                textAlign: 'center',
              }}
            >
              <Typography variant="body2" fontWeight="medium">
                세그먼트 {currentSegmentIndex + 1}
              </Typography>
            </Box>

            <Tooltip title="다음 세그먼트 (→)">
              <span>
                <IconButton 
                  onClick={goToNext}
                  disabled={currentSegmentIndex >= totalSegments - 1 || loading}
                  aria-label="다음 세그먼트로 이동"
                >
                  <NextIcon />
                </IconButton>
              </span>
            </Tooltip>
            
            <Tooltip title="마지막 세그먼트 (Ctrl+End)">
              <span>
                <IconButton 
                  onClick={goToLast}
                  disabled={currentSegmentIndex >= totalSegments - 1 || loading}
                  size="small"
                  aria-label="마지막 세그먼트로 이동"
                >
                  <LastIcon />
                </IconButton>
              </span>
            </Tooltip>
          </Stack>

          {/* Center: Jump to Segment */}
          <Box component="form" onSubmit={handleJumpTo}>
            <Stack direction="row" spacing={1} alignItems="center">
              <TextField
                size="small"
                placeholder="이동할 세그먼트"
                value={jumpToValue}
                onChange={(e) => setJumpToValue(e.target.value)}
                disabled={loading}
                sx={{ width: 120 }}
                type="number"
                inputProps={{
                  min: 1,
                  max: totalSegments,
                }}
              />
              <IconButton 
                type="submit"
                size="small"
                disabled={!jumpToValue || loading}
                aria-label="세그먼트로 이동"
              >
                <NextIcon />
              </IconButton>
            </Stack>
          </Box>

          {/* Right: Keyboard Shortcuts Info */}
          <Stack direction="row" spacing={1} alignItems="center">
            <KeyboardIcon fontSize="small" color="action" />
            <Typography variant="caption" color="text.secondary">
              ← → 이동 | Ctrl+Home/End 처음/끝
            </Typography>
          </Stack>
        </Stack>
      </Stack>
    </Paper>
  );
}
