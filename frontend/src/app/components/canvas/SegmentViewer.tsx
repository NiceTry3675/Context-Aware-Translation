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
import { ValidationTextSegmentDisplay } from '../shared/ValidationTextSegmentDisplay';
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
  // Collect issues for the current segment only
  const currentSegmentIssues = useMemo(() => {
    if (!validationReport?.detailed_results || mode !== 'validation') return [];

    const issues: Array<{
      issueType: string;
      message: string;
    }> = [];

    // Find the current segment's validation result
    const currentResult = validationReport.detailed_results.find(
      result => result.segment_index === currentSegmentIndex
    );

    if (!currentResult) return [];

    // Add filtered issues for the current segment
    if (errorFilters.critical) {
      currentResult.critical_issues.forEach(msg => 
        issues.push({ issueType: 'critical', message: msg })
      );
    }
    if (errorFilters.missingContent) {
      currentResult.missing_content.forEach(msg => 
        issues.push({ issueType: 'missing_content', message: msg })
      );
    }
    if (errorFilters.addedContent) {
      currentResult.added_content.forEach(msg => 
        issues.push({ issueType: 'added_content', message: msg })
      );
    }
    if (errorFilters.nameInconsistencies) {
      currentResult.name_inconsistencies.forEach(msg => 
        issues.push({ issueType: 'name_inconsistencies', message: msg })
      );
    }

    return issues;
  }, [validationReport, mode, errorFilters, currentSegmentIndex]);

  // Helper functions for issue formatting
  const getSeverityColor = (issueType: string): 'error' | 'warning' | 'info' | 'default' => {
    if (issueType === 'critical') return 'error';
    if (issueType === 'missing_content' || issueType === 'added_content') return 'warning';
    if (issueType === 'name_inconsistencies') return 'info';
    return 'default';
  };

  const formatIssueType = (type: string): string => {
    const typeMap: { [key: string]: string } = {
      'critical': '치명적',
      'missing_content': '누락',
      'added_content': '추가',
      'name_inconsistencies': '이름',
      'minor': '경미',
    };
    return typeMap[type] || type;
  };

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
      {/* Sticky Selected Issues Box for validation mode */}
      {mode === 'validation' && currentSegmentIssues.length > 0 && (
        <Box
          sx={{
            position: 'sticky',
            top: 0,
            zIndex: 100,
            bgcolor: 'background.paper',
            borderRadius: 1,
            boxShadow: 2,
            mb: 2,
            border: '1px solid',
            borderColor: 'divider',
            maxHeight: '30vh',
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column'
          }}
        >
          <Box
            sx={{
              p: 2,
              borderBottom: '1px solid',
              borderColor: 'divider',
              bgcolor: 'grey.800',
            }}
          >
            <Typography variant="subtitle1" sx={{ fontWeight: 'bold', color: 'white' }}>
              세그먼트 #{currentSegmentIndex + 1} 문제 상세 ({currentSegmentIssues.length}개)
            </Typography>
          </Box>
          <Box sx={{ overflow: 'auto', p: 2 }}>
            <List dense>
              {currentSegmentIssues.map((issue, idx) => (
                <ListItem 
                  key={`${issue.issueType}-${idx}`} 
                  sx={{ py: 0.5 }}
                >
                  <ListItemText
                    primary={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Chip
                          label={formatIssueType(issue.issueType)}
                          size="small"
                          color={getSeverityColor(issue.issueType)}
                          sx={{ height: '18px', minWidth: '45px' }}
                        />
                        <Typography variant="body2" sx={{ flex: 1 }}>
                          {issue.message}
                        </Typography>
                      </Box>
                    }
                  />
                </ListItem>
              ))}
            </List>
          </Box>
        </Box>
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
        // For post-edit mode showing unedited segments with issues
        <ValidationTextSegmentDisplay
          sourceText={segmentData.sourceText}
          translatedText={segmentData.translatedText}
          issues={(() => {
            const allIssues: { type: string; message: string; }[] = [];
            const issues = segmentData.issues;
            
            if (issues.critical) {
              issues.critical.forEach(msg => allIssues.push({ type: 'critical', message: msg }));
            }
            if (issues.missingContent || issues.missing_content) {
              const missingContent = issues.missingContent || issues.missing_content || [];
              missingContent.forEach(msg => allIssues.push({ type: 'missing_content', message: msg }));
            }
            if (issues.addedContent || issues.added_content) {
              const addedContent = issues.addedContent || issues.added_content || [];
              addedContent.forEach(msg => allIssues.push({ type: 'added_content', message: msg }));
            }
            if (issues.nameInconsistencies || issues.name_inconsistencies) {
              const nameInconsistencies = issues.nameInconsistencies || issues.name_inconsistencies || [];
              nameInconsistencies.forEach(msg => allIssues.push({ type: 'name_inconsistencies', message: msg }));
            }
            if (issues.minor) {
              issues.minor.forEach(msg => allIssues.push({ type: 'minor', message: msg }));
            }
            
            return allIssues;
          })()}
          status='FAIL'
        />
      ) : mode === 'post-edit' ? (
        // For post-edit mode, only show original vs edited translation (no source text)
        <TextSegmentDisplay
          sourceText=""
          translatedText={segmentData.translatedText}
          editedText={segmentData.editedText || segmentData.translatedText}
          showComparison={true}
          hideSource={true}
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