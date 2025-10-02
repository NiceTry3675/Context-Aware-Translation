'use client';

import React from 'react';
import {
  Box,
  Typography,
  Paper,
  Stack,
  IconButton,
  Tooltip,
  Grid,
} from '@mui/material';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import { TranslationContent, TranslationSegments, PostEditLog } from '../utils/api';

interface TranslationContentViewerProps {
  content: TranslationContent;
  sourceText?: string;
  segments?: TranslationSegments | null;
  postEditLog?: PostEditLog | null;
}

export default function TranslationContentViewer({ content, sourceText, segments, postEditLog }: TranslationContentViewerProps) {
  // Merge translated text from segments if available for consistency
  const mergedTranslatedText = React.useMemo(() => {
    // First priority: use post-edit log segments if available (has edited translations)
    if (postEditLog?.segments) {
      return postEditLog.segments
        .sort((a, b) => a.segment_index - b.segment_index)
        .map(segment => segment.edited_translation || segment.original_translation)
        .join('\n');
    }
    // Second priority: use translation segments if available
    if (segments?.segments && segments.segments.length > 0) {
      return segments.segments
        .sort((a, b) => a.segment_index - b.segment_index)
        .map(segment => segment.translated_text)
        .join('\n');
    }
    // Fallback: use content from translation content
    return content.content;
  }, [content.content, segments, postEditLog]);

  // Merge source text from segments if available for consistency
  const mergedSourceText = React.useMemo(() => {
    // First priority: use the sourceText prop if provided (already merged)
    if (sourceText) {
      return sourceText;
    }
    // Second priority: use source_content from content if available
    if (content.source_content) {
      return content.source_content;
    }
    // Third priority: merge from post-edit log segments
    if (postEditLog?.segments) {
      return postEditLog.segments
        .sort((a, b) => a.segment_index - b.segment_index)
        .map(segment => segment.source_text)
        .join('\n');
    }
    // Fourth priority: merge from translation segments
    if (segments?.segments && segments.segments.length > 0) {
      return segments.segments
        .sort((a, b) => a.segment_index - b.segment_index)
        .map(segment => segment.source_text)
        .join('\n');
    }
    return undefined;
  }, [sourceText, content.source_content, segments, postEditLog]);
  const handleCopyContent = () => {
    navigator.clipboard.writeText(mergedTranslatedText);
  };

  const handleCopySource = () => {
    if (mergedSourceText) {
      navigator.clipboard.writeText(mergedSourceText);
    }
  };

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
      <Stack spacing={2} sx={{ height: '100%', minHeight: 0 }}>
        {/* Removed header box as requested */}

        {/* Content display - side by side if source is available */}
        {mergedSourceText ? (
          <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            {/* Fixed headers */}
            <Grid container spacing={2} sx={{ mb: 2 }}>
              <Grid size={{ xs: 12, md: 6 }}>
                <Stack direction="row" justifyContent="space-between" alignItems="center">
                  <Typography variant="h6" color="text.secondary">
                    원문
                  </Typography>
                  <Tooltip title="원문 복사">
                    <IconButton onClick={handleCopySource} size="small">
                      <ContentCopyIcon />
                    </IconButton>
                  </Tooltip>
                </Stack>
              </Grid>
              <Grid size={{ xs: 12, md: 6 }}>
                <Stack direction="row" justifyContent="space-between" alignItems="center">
                  <Typography variant="h6" color="text.secondary">
                    번역문
                  </Typography>
                  <Tooltip title="번역문 복사">
                    <IconButton onClick={handleCopyContent} size="small">
                      <ContentCopyIcon />
                    </IconButton>
                  </Tooltip>
                </Stack>
              </Grid>
            </Grid>
            
            {/* Shared scrollable content area */}
            <Box
              sx={{
                flex: 1,
                overflowY: 'auto',
                border: 1,
                borderColor: 'divider',
                borderRadius: 1,
              }}
            >
              <Grid container spacing={0}>
                {/* Source content */}
                <Grid size={{ xs: 12, md: 6 }}>
                  <Paper elevation={0} sx={{ p: 3, height: '100%', borderRadius: 0, borderRight: { md: 1 }, borderColor: 'divider' }}>
                    <Typography
                      variant="body2"
                      sx={{
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word',
                      }}
                    >
                      {mergedSourceText}
                    </Typography>
                  </Paper>
                </Grid>

                {/* Translated content */}
                <Grid size={{ xs: 12, md: 6 }}>
                  <Paper elevation={0} sx={{ p: 3, height: '100%', borderRadius: 0 }}>
                    <Typography
                      variant="body2"
                      sx={{
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word',
                      }}
                    >
                      {mergedTranslatedText}
                    </Typography>
                  </Paper>
                </Grid>
              </Grid>
            </Box>
          </Box>
        ) : (
          // Original single column view when no source text
          <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
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
                flex: 1,
                overflowY: 'auto',
                border: 1,
                borderColor: 'divider',
                borderRadius: 1,
              }}
            >
              <Paper elevation={0} sx={{ p: 3, borderRadius: 0 }}>
                <Typography
                  variant="body2"
                  sx={{
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                  }}
                >
                  {mergedTranslatedText}
                </Typography>
              </Paper>
            </Box>
          </Box>
        )}
      </Stack>
    </Box>
  );
}
