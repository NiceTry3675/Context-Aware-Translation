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
import { ValidationTextSegmentDisplay } from '../shared/ValidationTextSegmentDisplay';
import { DiffMode, ViewMode } from '../shared/DiffViewer';
import { ValidationReport, PostEditLog, TranslationSegments } from '../../utils/api';

interface ErrorFilters {
  critical: boolean;
  missingContent: boolean;
  addedContent: boolean;
  nameInconsistencies: boolean;
}

interface SegmentViewerProps {
  mode: 'translation' | 'validation' | 'post-edit';
  currentSegmentIndex: number;
  validationReport?: ValidationReport | null;
  postEditLog?: PostEditLog | null;
  translationContent?: string | null;
  translationSegments?: TranslationSegments | null;
  errorFilters?: ErrorFilters;
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
            issues: segment.issues,
            changes: segment.changes_made,
          };
        }
        // For other modes, use the full text from post-edit log
        return {
          sourceText: segment.source_text,
          translatedText: segment.edited_translation || segment.original_translation,
          issues: segment.issues,
        };
      }
    }

    // Second, try to use translation segments from the new segments API (has full text)
    if (translationSegments?.segments && translationSegments.segments.length > 0) {
      const segment = translationSegments.segments.find((s) => s.segment_index === currentSegmentIndex);
      if (segment) {
        // Get issues from validation report if available
        let issues = undefined;
        if (validationReport?.detailed_results) {
          const validationResult = validationReport.detailed_results.find((r) => r.segment_index === currentSegmentIndex);
          if (validationResult) {
            issues = {
              critical: validationResult.critical_issues,
              missingContent: validationResult.missing_content,
              addedContent: validationResult.added_content,
              nameInconsistencies: validationResult.name_inconsistencies,
              minor: validationResult.minor_issues,
            };
          }
        }
        
        return {
          sourceText: segment.source_text,
          translatedText: segment.translated_text,
          issues,
        };
      }
    }

    // If segments are not available, use validation report (only has preview)
    if (validationReport?.detailed_results) {
      const result = validationReport.detailed_results.find((r) => r.segment_index === currentSegmentIndex);
      if (result) {
        // Note: validation report only has preview text, not full text
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

  // Check if we're showing preview text (from validation report) vs full text
  const isShowingPreview = !postEditLog && !translationSegments && validationReport;

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
      {/* Segment Header - Only show in validation mode */}
      {mode === 'validation' && (isShowingPreview || segmentData.issues) && (
        <Stack direction="row" justifyContent="flex-end" alignItems="center" mb={2}>
          <Stack direction="row" spacing={1}>
            {isShowingPreview && (
            <Chip 
              label="미리보기" 
              color="info" 
              size="small" 
              variant="outlined"
              title="전체 텍스트를 보려면 포스트 에디팅을 실행하세요"
            />
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
      )}

      {/* Notice for preview mode - only in validation mode */}
      {mode === 'validation' && isShowingPreview && (
        <Alert severity="info" sx={{ mb: 2 }}>
          현재 텍스트 미리보기만 표시됩니다. 전체 세그먼트 내용을 보려면 포스트 에디팅을 실행하세요.
        </Alert>
      )}

      {/* Text Display - Use ValidationTextSegmentDisplay when issues exist for consistent tabs interface */}
      {mode === 'validation' && segmentData.issues ? (
        (() => {
          // Filter issues based on errorFilters
          const filteredIssues: typeof segmentData.issues = {
            critical: errorFilters.critical ? segmentData.issues.critical : [],
            missingContent: errorFilters.missingContent ? (segmentData.issues.missingContent || segmentData.issues.missing_content || []) : [],
            addedContent: errorFilters.addedContent ? (segmentData.issues.addedContent || segmentData.issues.added_content || []) : [],
            nameInconsistencies: errorFilters.nameInconsistencies ? (segmentData.issues.nameInconsistencies || segmentData.issues.name_inconsistencies || []) : [],
            missing_content: errorFilters.missingContent ? (segmentData.issues.missing_content || segmentData.issues.missingContent || []) : [],
            added_content: errorFilters.addedContent ? (segmentData.issues.added_content || segmentData.issues.addedContent || []) : [],
            name_inconsistencies: errorFilters.nameInconsistencies ? (segmentData.issues.name_inconsistencies || segmentData.issues.nameInconsistencies || []) : [],
            minor: segmentData.issues.minor || [],
          };
          
          // Check if there are any filtered issues to show
          const hasFilteredIssues = 
            filteredIssues.critical.length > 0 ||
            (filteredIssues.missingContent || filteredIssues.missing_content || []).length > 0 ||
            (filteredIssues.addedContent || filteredIssues.added_content || []).length > 0 ||
            (filteredIssues.nameInconsistencies || filteredIssues.name_inconsistencies || []).length > 0;
          
          if (!hasFilteredIssues) {
            // Show that issues exist but are filtered out
            return (
              <Box>
                <Alert severity="info" sx={{ mb: 2 }}>
                  이 세그먼트에는 문제가 있지만 현재 필터 설정으로 숨겨져 있습니다.
                </Alert>
                <TextSegmentDisplay
                  sourceText={segmentData.sourceText}
                  translatedText={segmentData.translatedText}
                />
              </Box>
            );
          }
          
          return (
            <ValidationTextSegmentDisplay
              sourceText={segmentData.sourceText}
              translatedText={segmentData.translatedText}
              issues={(() => {
                // Convert filtered issues to the format expected by ValidationTextSegmentDisplay
                const allIssues: { type: string; message: string; }[] = [];
                
                if (filteredIssues.critical) {
                  filteredIssues.critical.forEach(msg => allIssues.push({ type: 'critical', message: msg }));
                }
                if (filteredIssues.missingContent || filteredIssues.missing_content) {
                  const missingContent = filteredIssues.missingContent || filteredIssues.missing_content || [];
                  missingContent.forEach(msg => allIssues.push({ type: 'missing_content', message: msg }));
                }
                if (filteredIssues.addedContent || filteredIssues.added_content) {
                  const addedContent = filteredIssues.addedContent || filteredIssues.added_content || [];
                  addedContent.forEach(msg => allIssues.push({ type: 'added_content', message: msg }));
                }
                if (filteredIssues.nameInconsistencies || filteredIssues.name_inconsistencies) {
                  const nameInconsistencies = filteredIssues.nameInconsistencies || filteredIssues.name_inconsistencies || [];
                  nameInconsistencies.forEach(msg => allIssues.push({ type: 'name_inconsistencies', message: msg }));
                }
                if (filteredIssues.minor) {
                  filteredIssues.minor.forEach(msg => allIssues.push({ type: 'minor', message: msg }));
                }
                
                return allIssues;
              })()}
              status={hasFilteredIssues ? 'FAIL' : 'PASS'}
            />
          );
        })()
      ) : mode === 'post-edit' && segmentData.issues && !segmentData.wasEdited ? (
        // For post-edit mode showing unedited segments with issues - hide source text
        <TextSegmentDisplay
          sourceText={segmentData.sourceText}
          translatedText={segmentData.translatedText}
          showComparison={false}
          hideSource={true}
        />
      ) : mode === 'post-edit' ? (
        // For post-edit mode, only show original vs edited translation (no source text)
        <TextSegmentDisplay
          sourceText={segmentData.sourceText}
          translatedText={segmentData.translatedText}
          editedText={segmentData.editedText || segmentData.translatedText}
          showComparison={true}
          hideSource={true}
          showDiff={showDiff && segmentData.wasEdited}
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