'use client';

import React from 'react';
import {
  Box,
  Typography,
  Paper,
  Stack,
  Divider,
  IconButton,
  Tooltip,
  Grid,
} from '@mui/material';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import { TranslationContent } from '../utils/api';

interface TranslationContentViewerProps {
  content: TranslationContent;
  sourceText?: string;
}

export default function TranslationContentViewer({ content, sourceText }: TranslationContentViewerProps) {
  const handleCopyContent = () => {
    navigator.clipboard.writeText(content.content);
  };

  const handleCopySource = () => {
    if (sourceText) {
      navigator.clipboard.writeText(sourceText);
    }
  };

  return (
    <Box>
      <Stack spacing={2}>
        {/* Header with file info */}
        <Paper elevation={0} sx={{ p: 2, backgroundColor: 'background.default' }}>
          <Stack direction="row" justifyContent="space-between" alignItems="center">
            <Box>
              <Typography variant="subtitle1" fontWeight="medium">
                번역된 파일
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {content.filename}
              </Typography>
              {content.completed_at && (
                <Typography variant="caption" color="text.secondary">
                  완료 시간: {new Date(content.completed_at).toLocaleString('ko-KR')}
                </Typography>
              )}
            </Box>
          </Stack>
        </Paper>

        <Divider />

        {/* Content display - side by side if source is available */}
        {sourceText ? (
          <Grid container spacing={2}>
            {/* Source content */}
            <Grid size={{ xs: 12, md: 6 }}>
              <Paper elevation={0} sx={{ p: 3, height: '100%' }}>
                <Stack direction="row" justifyContent="space-between" alignItems="center" mb={2}>
                  <Typography variant="h6" color="text.secondary">
                    원문
                  </Typography>
                  <Tooltip title="원문 복사">
                    <IconButton onClick={handleCopySource} size="small">
                      <ContentCopyIcon />
                    </IconButton>
                  </Tooltip>
                </Stack>
                <Box
                  sx={{
                    fontFamily: 'monospace',
                    fontSize: '0.95rem',
                    lineHeight: 1.8,
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                    color: 'text.primary',
                    maxHeight: '70vh',
                    overflowY: 'auto',
                  }}
                >
                  {sourceText}
                </Box>
              </Paper>
            </Grid>

            {/* Translated content */}
            <Grid size={{ xs: 12, md: 6 }}>
              <Paper elevation={0} sx={{ p: 3, height: '100%' }}>
                <Stack direction="row" justifyContent="space-between" alignItems="center" mb={2}>
                  <Typography variant="h6" color="text.secondary">
                    번역문
                  </Typography>
                  <Tooltip title="번역문 복사">
                    <IconButton onClick={handleCopyContent} size="small">
                      <ContentCopyIcon />
                    </IconButton>
                  </Tooltip>
                </Stack>
                <Box
                  sx={{
                    fontFamily: '"Noto Sans KR", "Malgun Gothic", sans-serif',
                    fontSize: '0.95rem',
                    lineHeight: 1.8,
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                    color: 'text.primary',
                    maxHeight: '70vh',
                    overflowY: 'auto',
                  }}
                >
                  {content.content}
                </Box>
              </Paper>
            </Grid>
          </Grid>
        ) : (
          // Original single column view when no source text
          <Paper elevation={0} sx={{ p: 3 }}>
            <Stack direction="row" justifyContent="space-between" alignItems="center" mb={2}>
              <Typography variant="h6" color="text.secondary">
                번역문
              </Typography>
              <Tooltip title="번역문 복사">
                <IconButton onClick={handleCopyContent} size="small">
                  <ContentCopyIcon />
                </IconButton>
              </Tooltip>
            </Stack>
            <Box
              sx={{
                fontFamily: '"Noto Sans KR", "Malgun Gothic", sans-serif',
                fontSize: '0.95rem',
                lineHeight: 1.8,
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
                color: 'text.primary',
              }}
            >
              {content.content}
            </Box>
          </Paper>
        )}
      </Stack>
    </Box>
  );
}