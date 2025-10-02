'use client';

import React, { useMemo, useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Chip,
  Stack,
  Alert,
  AlertTitle,
  FormControlLabel,
  Switch,
  ToggleButtonGroup,
  ToggleButton,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
} from '@mui/material';
import CompareIcon from '@mui/icons-material/Compare';
import ViewColumnIcon from '@mui/icons-material/ViewColumn';
import { TextSegmentDisplay } from '../shared/TextSegmentDisplay';
import { DiffMode, ViewMode } from '../shared/DiffViewer';
import { ValidationReport, PostEditLog, TranslationSegments } from '../../utils/api';

interface ErrorFilters {
  critical: boolean;
  missingContent: boolean;
  addedContent: boolean;
  nameInconsistencies: boolean;
}

interface SegmentViewerProps {
  mode: 'translation' | 'post-edit';
  currentSegmentIndex: number;
  validationReport?: ValidationReport | null; // kept only for post-edit context join
  postEditLog?: PostEditLog | null;
  translationContent?: string | null;
  translationSegments?: TranslationSegments | null;
  errorFilters?: ErrorFilters; // unused in structured-only flow
}

interface SegmentData {
  sourceText: string;
  translatedText: string;
  editedText?: string;
  wasEdited?: boolean;
  changes?: {
    text_changed?: boolean;
  };
}

export default function SegmentViewer({
  mode,
  currentSegmentIndex,
  validationReport,
  postEditLog,
  translationContent,
  translationSegments,
  errorFilters = {
    critical: true,
    missingContent: true,
    addedContent: true,
    nameInconsistencies: true,
  },
}: SegmentViewerProps) {
  // State for diff view settings (only for post-edit mode)
  const [showDiff, setShowDiff] = useState(true);
  const [diffMode, setDiffMode] = useState<DiffMode>('word');
  const [diffViewMode, setDiffViewMode] = useState<ViewMode>('unified');
  
  // Simplified UI: sticky issue summary removed

  // Extract segment data based on mode and available data
  const segmentData: SegmentData | null = useMemo(() => {
    // First, try to get full text from post-edit log if available (has full source_text)
    if (postEditLog?.segments) {
      const segment = postEditLog.segments.find((s) => s.segment_index === currentSegmentIndex);
      if (segment) {
        // For post-edit mode, show the editing comparison
        if (mode === 'post-edit') {
          return {
            sourceText: segment.source_text,
            translatedText: segment.original_translation,
            editedText: segment.edited_translation,
            wasEdited: segment.was_edited,
            changes: segment.changes_made,
          };
        }
        // For other modes, use the full text from post-edit log
        return {
          sourceText: segment.source_text,
          translatedText: segment.edited_translation || segment.original_translation,
        };
      }
    }

    // Second, try to use translation segments from the new segments API (has full text)
    if (translationSegments?.segments && translationSegments.segments.length > 0) {
      const segment = translationSegments.segments.find((s) => s.segment_index === currentSegmentIndex);
      if (segment) {
        return {
          sourceText: segment.source_text,
          translatedText: segment.translated_text,
        };
      }
    }

    // In structured-only flow, we do not render validation-only segment previews

    // Fallback: if we only have translation content (no segmentation available)
    if (mode === 'translation' && translationContent) {
      // We can't segment the content properly without segment boundaries
      // This is a limitation that needs backend support
      return {
        sourceText: 'Original source text not available in segment view. Please run validation to see segmented content.',
        translatedText: translationContent,
      };
    }

    return null;
  }, [mode, currentSegmentIndex, validationReport, postEditLog, translationContent, translationSegments]);

  if (!segmentData) {
    return (
      <Paper sx={{ p: 3 }}>
        <Alert severity="info">
          <AlertTitle>세그먼트 데이터 없음</AlertTitle>
          선택된 세그먼트에 대한 데이터를 찾을 수 없습니다.
        </Alert>
      </Paper>
    );
  }


  // Render changes if available (for post-edit mode)
  const renderChanges = () => {
    if (!segmentData.changes || !segmentData.wasEdited) return null;

    return (
      <Box sx={{ mt: 3 }}>
        <Typography variant="h6" gutterBottom>
          수정 내역
        </Typography>
        <Stack spacing={1}>
          {segmentData.changes.text_changed && (
            <Chip label="내용 수정됨" color="success" size="small" />
          )}
        </Stack>
      </Box>
    );
  };

  // Check if we're showing preview text (from validation report) vs full text
  const isShowingPreview = false;

  return (
    <Box sx={{ width: '100%' }}>
      {/* Sticky issue summary removed to minimize visual obstruction */}

      {/* Diff View Controls for Post-Edit Mode */}
      {mode === 'post-edit' && segmentData?.wasEdited && (
        <Paper sx={{ p: 2, mb: 2 }}>
          <Stack spacing={2}>
            <Stack direction="row" spacing={2} alignItems="center" justifyContent="space-between">
              <Typography variant="body2" fontWeight="medium">
                비교 보기 설정
              </Typography>
              <FormControlLabel
                control={
                  <Switch 
                    checked={showDiff} 
                    onChange={(e) => setShowDiff(e.target.checked)}
                  />
                }
                label="변경 사항 강조"
              />
            </Stack>

            {showDiff && (
              <Stack direction="row" spacing={2} alignItems="center">
                <ToggleButtonGroup
                  value={diffViewMode}
                  exclusive
                  onChange={(e, newMode) => newMode && setDiffViewMode(newMode)}
                  size="small"
                >
                  <ToggleButton value="unified">
                    <CompareIcon fontSize="small" sx={{ mr: 0.5 }} />
                    통합 보기
                  </ToggleButton>
                  <ToggleButton value="side-by-side">
                    <ViewColumnIcon fontSize="small" sx={{ mr: 0.5 }} />
                    나란히 보기
                  </ToggleButton>
                </ToggleButtonGroup>

                <FormControl size="small" sx={{ minWidth: 120 }}>
                  <InputLabel>비교 단위</InputLabel>
                  <Select
                    value={diffMode}
                    label="비교 단위"
                    onChange={(e) => setDiffMode(e.target.value as DiffMode)}
                  >
                    <MenuItem value="word">단어</MenuItem>
                    <MenuItem value="character">문자</MenuItem>
                    <MenuItem value="line">줄</MenuItem>
                  </Select>
                </FormControl>
              </Stack>
            )}
          </Stack>
        </Paper>
      )}

      <Paper sx={{ p: 3 }}>
      {/* Validation mode removed in structured-only flow */}
      {mode === 'post-edit' ? (
        // For post-edit mode, only show original vs edited translation (no source text)
        <TextSegmentDisplay
          sourceText={segmentData.sourceText}
          translatedText={segmentData.translatedText}
          editedText={segmentData.editedText || segmentData.translatedText}
          showComparison={!!segmentData.wasEdited}
          hideSource={true}
          showDiff={showDiff && !!segmentData.wasEdited}
          diffMode={diffMode}
          diffViewMode={diffViewMode}
        />
      ) : (
        // Use regular TextSegmentDisplay for other cases
        <TextSegmentDisplay
          sourceText={segmentData.sourceText}
          translatedText={segmentData.translatedText}
          editedText={segmentData.editedText}
          showComparison={false}
        />
      )}

      {/* Changes (for post-edit mode) - Only show when edited */}
      {mode === 'post-edit' && segmentData.wasEdited && renderChanges()}
    </Paper>
    </Box>
  );
}