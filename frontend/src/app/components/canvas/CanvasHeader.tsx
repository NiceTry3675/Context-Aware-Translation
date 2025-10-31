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
import BarChartIcon from '@mui/icons-material/BarChart';
import SettingsIcon from '@mui/icons-material/Settings';
import MenuIcon from '@mui/icons-material/Menu';
import { Job } from '../../types/ui';

interface CanvasHeaderProps {
  selectedJob: Job | null;
  fullscreen: boolean;
  onToggleFullscreen: () => void;
  onRefresh: () => void;
  onMenuClick?: () => void;
}

export default function CanvasHeader({
  selectedJob,
  fullscreen,
  onToggleFullscreen,
  onRefresh,
  onMenuClick,
}: CanvasHeaderProps) {
  const router = useRouter();

  return (
    <Paper elevation={1} sx={{ borderRadius: 0, borderBottom: 1, borderColor: 'divider' }}>
      <Container maxWidth={false}>
        <Box sx={{ py: { xs: 1, sm: 2 }, px: { xs: 1, sm: 2 } }}>
          <Stack direction="row" justifyContent="space-between" alignItems="center">
            <Stack direction="row" spacing={{ xs: 1, sm: 2 }} alignItems="center">
              {onMenuClick && (
                <IconButton
                  aria-label="메뉴 열기"
                  onClick={onMenuClick}
                  sx={{ display: { xs: 'inline-flex', md: 'none' } }}
                >
                  <MenuIcon />
                </IconButton>
              )}
              <Typography
                variant="h6"
                component="h1"
                sx={{
                  fontSize: { xs: '1rem', sm: '1.25rem' },
                  display: { xs: 'none', sm: 'block' }
                }}
              >
                번역 캔버스
              </Typography>
              {selectedJob && (
                <Tooltip title={selectedJob.filename}>
                  <Chip
                    label={selectedJob.filename}
                    size="small"
                    sx={{
                      maxWidth: { xs: 150, sm: 200, md: 300 },
                      '& .MuiChip-label': { overflow: 'hidden', textOverflow: 'ellipsis' },
                      fontSize: { xs: '0.7rem', sm: '0.8125rem' }
                    }}
                  />
                </Tooltip>
              )}
            </Stack>

            <Stack direction="row" spacing={{ xs: 0.5, sm: 1 }} alignItems="center">
              <Tooltip title="새로고침">
                <IconButton
                  aria-label="새로고침"
                  onClick={onRefresh}
                  size="small"
                >
                  <RefreshIcon fontSize="small" />
                </IconButton>
              </Tooltip>
              <Tooltip title="토큰 사용량">
                <IconButton
                  aria-label="토큰 사용량"
                  onClick={() => router.push('/usage')}
                  size="small"
                  sx={{ display: { xs: 'none', sm: 'inline-flex' } }}
                >
                  <BarChartIcon fontSize="small" />
                </IconButton>
              </Tooltip>
              <Tooltip title="API 설정">
                <IconButton
                  aria-label="API 설정"
                  onClick={() => router.push('/settings')}
                  size="small"
                  sx={{ display: { xs: 'none', sm: 'inline-flex' } }}
                >
                  <SettingsIcon fontSize="small" />
                </IconButton>
              </Tooltip>
              <Tooltip title="정보">
                <IconButton
                  aria-label="소개 페이지"
                  onClick={() => router.push('/about')}
                  size="small"
                  sx={{ display: { xs: 'none', sm: 'inline-flex' } }}
                >
                  <InfoOutlinedIcon fontSize="small" />
                </IconButton>
              </Tooltip>
              <Tooltip title={fullscreen ? "전체화면 종료" : "전체화면"}>
                <IconButton
                  aria-label={fullscreen ? '전체화면 종료' : '전체화면'}
                  onClick={onToggleFullscreen}
                  size="small"
                  sx={{ display: { xs: 'none', sm: 'inline-flex' } }}
                >
                  {fullscreen ? <FullscreenExitIcon fontSize="small" /> : <FullscreenIcon fontSize="small" />}
                </IconButton>
              </Tooltip>
            </Stack>
          </Stack>
        </Box>
      </Container>
    </Paper>
  );
}
