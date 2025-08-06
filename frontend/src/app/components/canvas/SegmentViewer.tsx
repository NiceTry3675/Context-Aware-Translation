'use client';

import React, { useMemo } from 'react';
import {
  Box,
  Paper,
  Typography,
  Chip,
  Stack,
  Alert,
  AlertTitle,
  Divider,
  List,
  ListItem,
  ListItemText,
} from '@mui/material';
import { TextSegmentDisplay } from '../shared/TextSegmentDisplay';
import { ValidationReport, PostEditLog } from '../../utils/api';

interface SegmentViewerProps {
  mode: 'translation' | 'validation' | 'post-edit';
  currentSegmentIndex: number;
  validationReport?: ValidationReport | null;
  postEditLog?: PostEditLog | null;
  translationContent?: string | null;
}

interface SegmentData {
  sourceText: string;
  translatedText: string;
  editedText?: string;
  issues?: {
    critical: string[];
    missingContent?: string[];
    addedContent?: string[];
    nameInconsistencies?: string[];
    missing_content?: string[];
    added_content?: string[];
    name_inconsistencies?: string[];
    minor?: string[];
  };
  wasEdited?: boolean;
  changes?: {
    text_changed?: boolean;
    critical_fixed?: boolean;
    missing_content_fixed?: boolean;
    added_content_fixed?: boolean;
    name_inconsistencies_fixed?: boolean;
  };
}

export default function SegmentViewer({
  mode,
  currentSegmentIndex,
  validationReport,
  postEditLog,
  translationContent,
}: SegmentViewerProps) {
  // Extract segment data based on mode and available data
  const segmentData: SegmentData | null = useMemo(() => {
    // For post-edit mode, use post-edit log data
    if (mode === 'post-edit' && postEditLog?.segments) {
      const segment = postEditLog.segments.find((s) => s.segment_index === currentSegmentIndex);
      if (segment) {
        return {
          sourceText: segment.source_text,
          translatedText: segment.original_translation,
          editedText: segment.edited_translation,
          wasEdited: segment.was_edited,
          issues: segment.issues,
          changes: segment.changes_made,
        };
      }
    }

    // For validation mode or when post-edit data isn't available, use validation report
    if (validationReport?.detailed_results) {
      const result = validationReport.detailed_results.find((r) => r.segment_index === currentSegmentIndex);
      if (result) {
        return {
          sourceText: result.source_preview,
          translatedText: result.translated_preview,
          issues: {
            critical: result.critical_issues,
            missingContent: result.missing_content,
            addedContent: result.added_content,
            nameInconsistencies: result.name_inconsistencies,
            minor: result.minor_issues,
          },
        };
      }
    }

    // For translation mode with post-edit data available
    if (mode === 'translation' && postEditLog?.segments) {
      const segment = postEditLog.segments.find((s) => s.segment_index === currentSegmentIndex);
      if (segment) {
        return {
          sourceText: segment.source_text,
          translatedText: segment.edited_translation || segment.original_translation,
        };
      }
    }

    // Fallback: if we only have translation content (no segmentation available)
    if (mode === 'translation' && translationContent) {
      // We can't segment the content properly without segment boundaries
      // This is a limitation that needs backend support
      return {
        sourceText: 'Original source text not available in segment view. Please use validation or post-edit to see segmented content.',
        translatedText: translationContent,
      };
    }

    return null;
  }, [mode, currentSegmentIndex, validationReport, postEditLog, translationContent]);

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

  // Render issues if available
  const renderIssues = () => {
    if (!segmentData.issues) return null;

    // Handle both field name formats
    const missingContent = segmentData.issues.missingContent || segmentData.issues.missing_content || [];
    const addedContent = segmentData.issues.addedContent || segmentData.issues.added_content || [];
    const nameInconsistencies = segmentData.issues.nameInconsistencies || segmentData.issues.name_inconsistencies || [];
    const minor = segmentData.issues.minor || [];

    const hasIssues = 
      segmentData.issues.critical.length > 0 ||
      missingContent.length > 0 ||
      addedContent.length > 0 ||
      nameInconsistencies.length > 0 ||
      minor.length > 0;

    if (!hasIssues) return null;

    return (
      <Box sx={{ mt: 3 }}>
        <Typography variant="h6" gutterBottom>
          검증 이슈
        </Typography>
        <Stack spacing={2}>
          {segmentData.issues.critical.length > 0 && (
            <Box>
              <Chip label="치명적 오류" color="error" size="small" sx={{ mb: 1 }} />
              <List dense>
                {segmentData.issues.critical.map((issue, idx) => (
                  <ListItem key={idx}>
                    <ListItemText primary={issue} />
                  </ListItem>
                ))}
              </List>
            </Box>
          )}

          {missingContent.length > 0 && (
            <Box>
              <Chip label="누락된 내용" color="warning" size="small" sx={{ mb: 1 }} />
              <List dense>
                {missingContent.map((issue, idx) => (
                  <ListItem key={idx}>
                    <ListItemText primary={issue} />
                  </ListItem>
                ))}
              </List>
            </Box>
          )}

          {addedContent.length > 0 && (
            <Box>
              <Chip label="추가된 내용" color="info" size="small" sx={{ mb: 1 }} />
              <List dense>
                {addedContent.map((issue, idx) => (
                  <ListItem key={idx}>
                    <ListItemText primary={issue} />
                  </ListItem>
                ))}
              </List>
            </Box>
          )}

          {nameInconsistencies.length > 0 && (
            <Box>
              <Chip label="이름 불일치" color="secondary" size="small" sx={{ mb: 1 }} />
              <List dense>
                {nameInconsistencies.map((issue, idx) => (
                  <ListItem key={idx}>
                    <ListItemText primary={issue} />
                  </ListItem>
                ))}
              </List>
            </Box>
          )}

          {minor.length > 0 && (
            <Box>
              <Chip label="경미한 문제" color="default" size="small" sx={{ mb: 1 }} />
              <List dense>
                {minor.map((issue, idx) => (
                  <ListItem key={idx}>
                    <ListItemText primary={issue} />
                  </ListItem>
                ))}
              </List>
            </Box>
          )}
        </Stack>
      </Box>
    );
  };

  // Render changes if available (for post-edit mode)
  const renderChanges = () => {
    if (!segmentData.changes || !segmentData.wasEdited) return null;

    const fixedIssues = [];
    if (segmentData.changes.critical_fixed) fixedIssues.push('치명적 오류');
    if (segmentData.changes.missing_content_fixed) fixedIssues.push('누락된 내용');
    if (segmentData.changes.added_content_fixed) fixedIssues.push('추가된 내용');
    if (segmentData.changes.name_inconsistencies_fixed) fixedIssues.push('이름 불일치');

    return (
      <Box sx={{ mt: 3 }}>
        <Typography variant="h6" gutterBottom>
          수정 내역
        </Typography>
        <Stack spacing={1}>
          {segmentData.changes.text_changed && (
            <Chip label="내용 수정됨" color="success" size="small" />
          )}
          {fixedIssues.length > 0 && (
            <Box>
              <Chip label="해결된 문제" color="success" size="small" sx={{ mb: 1 }} />
              <Typography variant="body2" color="text.secondary">
                {fixedIssues.join(', ')}
              </Typography>
            </Box>
          )}
        </Stack>
      </Box>
    );
  };

  return (
    <Paper sx={{ p: 3 }}>
      {/* Segment Header */}
      <Stack direction="row" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h6">
          세그먼트 {currentSegmentIndex + 1}
        </Typography>
        <Stack direction="row" spacing={1}>
          {mode === 'post-edit' && segmentData.wasEdited && (
            <Chip label="수정됨" color="success" size="small" />
          )}
          {segmentData.issues && (
            <Chip 
              label={`${(segmentData.issues.critical.length + 
                         (segmentData.issues.missingContent || segmentData.issues.missing_content || []).length + 
                         (segmentData.issues.addedContent || segmentData.issues.added_content || []).length + 
                         (segmentData.issues.nameInconsistencies || segmentData.issues.name_inconsistencies || []).length)} 이슈`}
              color="warning" 
              size="small" 
            />
          )}
        </Stack>
      </Stack>

      <Divider sx={{ mb: 3 }} />

      {/* Text Display */}
      <TextSegmentDisplay
        sourceText={segmentData.sourceText}
        translatedText={segmentData.translatedText}
        editedText={segmentData.editedText}
        showComparison={mode === 'post-edit' && segmentData.wasEdited}
      />

      {/* Issues (for validation mode) */}
      {(mode === 'validation' || mode === 'post-edit') && renderIssues()}

      {/* Changes (for post-edit mode) */}
      {mode === 'post-edit' && renderChanges()}
    </Paper>
  );
}