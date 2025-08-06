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
} from '@mui/material';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import { TranslationContent } from '../utils/api';

interface TranslationContentViewerProps {
  content: TranslationContent;
}

export default function TranslationContentViewer({ content }: TranslationContentViewerProps) {
  const handleCopyContent = () => {
    navigator.clipboard.writeText(content.content);
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
            <Tooltip title="전체 텍스트 복사">
              <IconButton onClick={handleCopyContent} size="small">
                <ContentCopyIcon />
              </IconButton>
            </Tooltip>
          </Stack>
        </Paper>

        <Divider />

        {/* Translation content */}
        <Paper elevation={0} sx={{ p: 3 }}>
          <Box
            sx={{
              fontFamily: '"Noto Sans KR", "Malgun Gothic", sans-serif',
              fontSize: '0.95rem',
              lineHeight: 1.8,
              whiteSpace: 'pre-wrap',
              wordBreak: 'keep-all',
              color: 'text.primary',
            }}
          >
            {content.content}
          </Box>
        </Paper>
      </Stack>
    </Box>
  );
}