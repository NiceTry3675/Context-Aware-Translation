'use client';

import React from 'react';
import { Box, Typography, Paper, Grid } from '@mui/material';

interface TextSegmentDisplayProps {
  sourceText: string;
  translatedText?: string;
  editedText?: string;
  showComparison?: boolean;
}

export function TextSegmentDisplay({ 
  sourceText, 
  translatedText, 
  editedText,
  showComparison = false 
}: TextSegmentDisplayProps) {
  if (showComparison && translatedText && editedText) {
    return (
      <Grid container spacing={2}>
        {/* Source Text */}
        <Grid size={12}>
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
        
        {/* Original Translation */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Typography variant="subtitle2" gutterBottom color="text.secondary">
            수정 전 번역
          </Typography>
          <Paper 
            variant="outlined" 
            sx={{ 
              p: 1.5, 
              backgroundColor: 'rgba(244, 67, 54, 0.08)',
              borderColor: 'error.main'
            }}
          >
            <Typography 
              variant="body2" 
              sx={{ 
                whiteSpace: 'pre-wrap',
                textDecoration: 'line-through',
                opacity: 0.8
              }}
            >
              {translatedText}
            </Typography>
          </Paper>
        </Grid>
        
        {/* Edited Translation */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Typography variant="subtitle2" gutterBottom color="text.secondary">
            수정 후 번역
          </Typography>
          <Paper 
            variant="outlined" 
            sx={{ 
              p: 1.5, 
              backgroundColor: 'rgba(76, 175, 80, 0.08)',
              borderColor: 'success.main'
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