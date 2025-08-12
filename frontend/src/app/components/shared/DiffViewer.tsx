'use client';

import React, { useMemo } from 'react';
import { Box, Typography } from '@mui/material';
import * as Diff from 'diff';

export type DiffMode = 'word' | 'character' | 'line';
export type ViewMode = 'unified' | 'side-by-side';

interface DiffViewerProps {
  oldText: string;
  newText: string;
  mode?: DiffMode;
  viewMode?: ViewMode;
  showDiff?: boolean;
}

interface DiffPart {
  value: string;
  added?: boolean;
  removed?: boolean;
}

export function DiffViewer({ 
  oldText, 
  newText, 
  mode = 'word',
  viewMode = 'unified',
  showDiff = true 
}: DiffViewerProps) {
  const diffs = useMemo(() => {
    if (!showDiff) return [];
    
    switch (mode) {
      case 'character':
        return Diff.diffChars(oldText, newText);
      case 'line':
        return Diff.diffLines(oldText, newText);
      case 'word':
      default:
        return Diff.diffWords(oldText, newText);
    }
  }, [oldText, newText, mode, showDiff]);

  const renderDiffPart = (part: DiffPart, index: number) => {
    const getStyles = () => {
      if (part.added) {
        return {
          backgroundColor: 'rgba(76, 175, 80, 0.2)',
          color: 'success.dark',
          textDecoration: 'none',
          fontWeight: 500,
        };
      }
      if (part.removed) {
        return {
          backgroundColor: 'rgba(244, 67, 54, 0.2)',
          color: 'error.dark',
          textDecoration: 'line-through',
          opacity: 0.8,
        };
      }
      return {};
    };

    return (
      <Typography
        key={index}
        component="span"
        sx={{
          ...getStyles(),
          transition: 'all 0.2s ease',
          whiteSpace: 'pre-wrap',
        }}
      >
        {part.value}
      </Typography>
    );
  };

  const renderUnifiedDiff = () => {
    return (
      <Box sx={{ 
        p: 2, 
        backgroundColor: 'background.paper',
        borderRadius: 1,
        border: '1px solid',
        borderColor: 'divider',
        fontFamily: 'monospace',
        fontSize: '0.9rem',
        lineHeight: 1.6,
      }}>
        {diffs.map((part, index) => renderDiffPart(part, index))}
      </Box>
    );
  };

  const renderSideBySideDiff = () => {
    const oldParts: DiffPart[] = [];
    const newParts: DiffPart[] = [];

    diffs.forEach(part => {
      if (part.removed) {
        oldParts.push(part);
      } else if (part.added) {
        newParts.push(part);
      } else {
        oldParts.push(part);
        newParts.push(part);
      }
    });

    return (
      <Box sx={{ display: 'flex', gap: 2 }}>
        <Box sx={{ 
          flex: 1,
          p: 2,
          backgroundColor: 'rgba(244, 67, 54, 0.05)',
          borderRadius: 1,
          border: '1px solid',
          borderColor: 'error.main',
          fontFamily: 'monospace',
          fontSize: '0.9rem',
          lineHeight: 1.6,
        }}>
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
            수정 전
          </Typography>
          {oldParts.map((part, index) => (
            <Typography
              key={index}
              component="span"
              sx={{
                backgroundColor: part.removed ? 'rgba(244, 67, 54, 0.2)' : 'transparent',
                color: part.removed ? 'error.dark' : 'text.primary',
                textDecoration: part.removed ? 'line-through' : 'none',
                whiteSpace: 'pre-wrap',
              }}
            >
              {part.value}
            </Typography>
          ))}
        </Box>

        <Box sx={{ 
          flex: 1,
          p: 2,
          backgroundColor: 'rgba(76, 175, 80, 0.05)',
          borderRadius: 1,
          border: '1px solid',
          borderColor: 'success.main',
          fontFamily: 'monospace',
          fontSize: '0.9rem',
          lineHeight: 1.6,
        }}>
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
            수정 후
          </Typography>
          {newParts.map((part, index) => (
            <Typography
              key={index}
              component="span"
              sx={{
                backgroundColor: part.added ? 'rgba(76, 175, 80, 0.2)' : 'transparent',
                color: part.added ? 'success.dark' : 'text.primary',
                fontWeight: part.added ? 500 : 400,
                whiteSpace: 'pre-wrap',
              }}
            >
              {part.value}
            </Typography>
          ))}
        </Box>
      </Box>
    );
  };

  if (!showDiff) {
    return (
      <Box sx={{ 
        p: 2, 
        backgroundColor: 'background.paper',
        borderRadius: 1,
        border: '1px solid',
        borderColor: 'divider',
      }}>
        <Typography sx={{ whiteSpace: 'pre-wrap' }}>
          {newText}
        </Typography>
      </Box>
    );
  }

  return viewMode === 'unified' ? renderUnifiedDiff() : renderSideBySideDiff();
}