'use client';

import React from 'react';
import { Box, Typography, Paper, Grid } from '@mui/material';
import { DiffViewer, DiffMode, ViewMode } from './DiffViewer';

interface TextSegmentDisplayProps {
  sourceText: string;
  translatedText?: string;
  editedText?: string;
  showComparison?: boolean;
  hideSource?: boolean;
  showDiff?: boolean;
  diffMode?: DiffMode;
  diffViewMode?: ViewMode;
}

export function TextSegmentDisplay({ 
  sourceText, 
  translatedText, 
  editedText,
  showComparison = false,
  hideSource = false,
  showDiff = false,
  diffMode = 'word',
  diffViewMode = 'unified'
}: TextSegmentDisplayProps) {
  if (showComparison && translatedText && editedText) {
    return (
      <Grid container spacing={2}>
        {/* Source Text - only show if not hidden */}
        {!hideSource && (
          <Grid item xs={12}>
            <Typography variant="subtitle2" gutterBottom color="text.secondary">
              원문
            </Typography>
            <Paper variant="outlined" sx={{ 
              p: 1.5, 
              backgroundColor: 'background.paper'
            }}>
              <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                {sourceText}
              </Typography>
            </Paper>
          </Grid>
        )}
        
        {/* Diff View or Side-by-Side Comparison */}
        {showDiff ? (
          <Grid item xs={12}>
            <Typography variant="subtitle2" gutterBottom color="text.secondary">
              변경 사항
            </Typography>
            <DiffViewer
              oldText={translatedText}
              newText={editedText}
              mode={diffMode}
              viewMode={diffViewMode}
              showDiff={showDiff}
            />
          </Grid>
        ) : (
          <>
            {/* Original Translation */}
            <Grid item xs={12} md={6}>
              <Typography variant="subtitle2" gutterBottom color="text.secondary">
                수정 전 번역
              </Typography>
              <Paper 
                variant="outlined" 
                sx={{ 
                  p: 1.5, 
                  backgroundColor: 'background.paper',
                  borderColor: 'error.main',
                  borderWidth: 2
                }}
              >
                <Typography 
                  variant="body2" 
                  sx={{ 
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word'
                  }}
                >
                  {translatedText}
                </Typography>
              </Paper>
            </Grid>
            
            {/* Edited Translation */}
            <Grid item xs={12} md={6}>
              <Typography variant="subtitle2" gutterBottom color="text.secondary">
                수정 후 번역
              </Typography>
              <Paper 
                variant="outlined" 
                sx={{ 
                  p: 1.5, 
                  backgroundColor: 'background.paper',
                  borderColor: 'success.main',
                  borderWidth: 2
                }}
              >
                <Typography 
                  variant="body2" 
                  sx={{ 
                    whiteSpace: 'pre-wrap',
                    fontWeight: 'medium'
                  }}
                >
                  {editedText}
                </Typography>
              </Paper>
            </Grid>
          </>
        )}
      </Grid>
    );
  }

  return (
    <Box sx={{ display: { xs: 'block', md: 'flex' }, gap: 2 }}>
      {/* Source Text */}
      <Box sx={{ flex: 1, mb: { xs: 2, md: 0 } }}>
        <Typography variant="subtitle2" gutterBottom color="text.secondary">
          원문
        </Typography>
        <Paper variant="outlined" sx={{ 
          p: 1.5, 
          backgroundColor: 'background.paper'
        }}>
          <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
            {sourceText}
          </Typography>
        </Paper>
      </Box>
      
      {/* Translated Text */}
      {(translatedText || editedText) && (
        <Box sx={{ flex: 1 }}>
          <Typography variant="subtitle2" gutterBottom color="text.secondary">
            번역문
          </Typography>
          <Paper variant="outlined" sx={{ 
            p: 1.5, 
            backgroundColor: 'background.paper'
          }}>
            <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
              {editedText || translatedText}
            </Typography>
          </Paper>
        </Box>
      )}
    </Box>
  );
}
