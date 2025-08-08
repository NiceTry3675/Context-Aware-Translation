'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import {
  Box,
  Container,
  Paper,
  Typography,
  IconButton,
  Stack,
  Chip,
  Tooltip,
} from '@mui/material';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import RefreshIcon from '@mui/icons-material/Refresh';
import FullscreenIcon from '@mui/icons-material/Fullscreen';
import FullscreenExitIcon from '@mui/icons-material/FullscreenExit';
import { Job } from '../../types/job';

interface CanvasHeaderProps {
  selectedJob: Job | null;
  fullscreen: boolean;
  onToggleFullscreen: () => void;
}

export default function CanvasHeader({ 
  selectedJob, 
  fullscreen, 
  onToggleFullscreen 
}: CanvasHeaderProps) {
  const router = useRouter();
  
  return (
    <Paper elevation={1} sx={{ borderRadius: 0 }}>
      <Container maxWidth={false}>
        <Box sx={{ py: 2 }}>
          <Stack direction="row" justifyContent="space-between" alignItems="center">
            <Stack direction="row" spacing={2} alignItems="center">
              <Typography variant="h6" component="h1">
                번역 캔버스
              </Typography>
              {selectedJob && (
                <Chip
                  label={selectedJob.filename}
                  size="small"
                  sx={{ maxWidth: 300 }}
                />
              )}
            </Stack>

            <Stack direction="row" spacing={1} alignItems="center">
              <Tooltip title="새로고침">
                <IconButton onClick={() => window.location.reload()}>
                  <RefreshIcon />
                </IconButton>
              </Tooltip>
              <Tooltip title="About">
                <IconButton onClick={() => router.push('/about')}>
                  <InfoOutlinedIcon />
                </IconButton>
              </Tooltip>
              <Tooltip title={fullscreen ? "전체화면 종료" : "전체화면"}>
                <IconButton onClick={onToggleFullscreen}>
                  {fullscreen ? <FullscreenExitIcon /> : <FullscreenIcon />}
                </IconButton>
              </Tooltip>
            </Stack>
          </Stack>
        </Box>
      </Container>
    </Paper>
  );
}