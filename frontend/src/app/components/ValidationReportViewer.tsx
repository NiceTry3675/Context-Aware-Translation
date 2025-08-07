'use client';

import React from 'react';
import {
  Box,
  Typography,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip,
  List,
  ListItem,
  ListItemText,
  Alert,
  AlertTitle,
  Checkbox,
  ListItemIcon,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import { ValidationReport } from '../utils/api';
import { SummaryStatistics } from './shared/SummaryStatistics';
import { ValidationTextSegmentDisplay } from './shared/ValidationTextSegmentDisplay';

interface ValidationReportViewerProps {
  report: ValidationReport;
  selectedIssues?: {
    [segmentIndex: number]: {
      [issueType: string]: boolean[]
    }
  };
  onIssueSelectionChange?: (
    segmentIndex: number,
    issueType: string,
    issueIndex: number,
    selected: boolean
  ) => void;
  onSegmentClick?: (segmentIndex: number) => void;
}

export default function ValidationReportViewer({ 
  report, 
  selectedIssues, 
  onIssueSelectionChange, 
  onSegmentClick 
}: ValidationReportViewerProps) {
  const getSeverityColor = (issueType: string): 'error' | 'warning' | 'info' | 'default' => {
    if (issueType === 'critical') return 'error';
    if (issueType === 'missing_content' || issueType === 'added_content') return 'warning';
    if (issueType === 'name_inconsistencies') return 'info';
    return 'default';
  };

  const formatIssueType = (type: string): string => {
    const typeMap: { [key: string]: string } = {
      'critical': '치명적 오류',
      'missing_content': '누락된 내용',
      'added_content': '추가된 내용',
      'name_inconsistencies': '이름 불일치',
      'minor': '경미한 문제',
    };
    return typeMap[type] || type;
  };

  // Deduplicate validation errors - sometimes LLM produces duplicates
  const deduplicateIssues = (issues: string[]): string[] => {
    // Create a Set to remove exact duplicates
    const uniqueIssues = new Set(issues);
    
    // Further deduplicate by checking for similar messages (removing whitespace differences)
    const deduped: string[] = [];
    const normalizedMessages = new Set<string>();
    
    for (const issue of uniqueIssues) {
      // Normalize the message for comparison (lowercase, trim, collapse whitespace)
      const normalized = issue.toLowerCase().replace(/\s+/g, ' ').trim();
      
      if (!normalizedMessages.has(normalized)) {
        normalizedMessages.add(normalized);
        deduped.push(issue);
      }
    }
    
    return deduped;
  };

  // Calculate selected issue counts
  const calculateSelectedCounts = () => {
    let critical = 0;
    let missingContent = 0;
    let addedContent = 0;
    let nameInconsistencies = 0;

    report.detailed_results.forEach((result) => {
      const segmentSelection = selectedIssues?.[result.segment_index];
      
      if (segmentSelection) {
        critical += segmentSelection.critical?.filter(selected => selected).length || 0;
        missingContent += segmentSelection.missing_content?.filter(selected => selected).length || 0;
        addedContent += segmentSelection.added_content?.filter(selected => selected).length || 0;
        nameInconsistencies += segmentSelection.name_inconsistencies?.filter(selected => selected).length || 0;
      } else {
        // If no selection state exists, count all issues as selected (default behavior)
        critical += result.critical_issues.length;
        missingContent += result.missing_content.length;
        addedContent += result.added_content.length;
        nameInconsistencies += result.name_inconsistencies.length;
      }
    });

    return {
      critical,
      missingContent,
      addedContent,
      nameInconsistencies,
      total: critical + missingContent + addedContent + nameInconsistencies
    };
  };

  const selectedCounts = calculateSelectedCounts();

  // Collect all issues with selection capability
  const allIssuesWithSelection = React.useMemo(() => {
    const issues: Array<{
      segmentIndex: number;
      issueType: string;
      typeIndex: number;
      message: string;
      isSelected: boolean;
    }> = [];

    report.detailed_results.forEach((result) => {
      const dedupedCritical = deduplicateIssues(result.critical_issues);
      const dedupedMissing = deduplicateIssues(result.missing_content);
      const dedupedAdded = deduplicateIssues(result.added_content);
      const dedupedNames = deduplicateIssues(result.name_inconsistencies);

      const issuesByType = {
        critical: dedupedCritical,
        missing_content: dedupedMissing,
        added_content: dedupedAdded,
        name_inconsistencies: dedupedNames,
      };

      Object.entries(issuesByType).forEach(([type, typeIssues]) => {
        typeIssues.forEach((message, index) => {
          const isSelected = selectedIssues?.[result.segment_index]?.[type]?.[index] ?? true;
          if (isSelected) {
            issues.push({
              segmentIndex: result.segment_index,
              issueType: type,
              typeIndex: index,
              message,
              isSelected,
            });
          }
        });
      });
    });

    // Sort by segment index for easier navigation
    return issues.sort((a, b) => a.segmentIndex - b.segmentIndex);
  }, [report, selectedIssues]);

  return (
    <Box sx={{ width: '100%', position: 'relative' }}>
      {/* Summary Section */}
      <SummaryStatistics
        title="검증 요약"
        stats={[
          { label: '전체 세그먼트', value: report.summary.total_segments },
          { label: '검증된 세그먼트', value: report.summary.validated_segments }
        ]}
        progressBar={{
          value: report.summary.pass_rate,
          label: '통과율'
        }}
        passFailStats={{
          passed: report.summary.passed,
          failed: report.summary.failed
        }}
        issueStats={[
          { 
            type: 'critical', 
            count: report.summary.total_critical_issues, 
            label: onIssueSelectionChange && selectedCounts.critical < report.summary.total_critical_issues 
              ? `치명적 (${selectedCounts.critical}/${report.summary.total_critical_issues})` 
              : '치명적' 
          },
          { 
            type: 'missing_content', 
            count: report.summary.total_missing_content, 
            label: onIssueSelectionChange && selectedCounts.missingContent < report.summary.total_missing_content 
              ? `누락 (${selectedCounts.missingContent}/${report.summary.total_missing_content})` 
              : '누락' 
          },
          { 
            type: 'added_content', 
            count: report.summary.total_added_content, 
            label: onIssueSelectionChange && selectedCounts.addedContent < report.summary.total_added_content 
              ? `추가 (${selectedCounts.addedContent}/${report.summary.total_added_content})` 
              : '추가' 
          },
          { 
            type: 'name_inconsistencies', 
            count: report.summary.total_name_inconsistencies, 
            label: onIssueSelectionChange && selectedCounts.nameInconsistencies < report.summary.total_name_inconsistencies 
              ? `이름 불일치 (${selectedCounts.nameInconsistencies}/${report.summary.total_name_inconsistencies})` 
              : '이름 불일치' 
          }
        ]}
      />

      {/* Sticky Selected Issues Box */}
      {onIssueSelectionChange && allIssuesWithSelection.length > 0 && (
        <Box
          sx={{
            position: 'sticky',
            top: 0, // Positioned right at the top of the scrollable area
            zIndex: 100,
            bgcolor: 'background.paper',
            borderRadius: 1,
            boxShadow: 2,
            mb: 2,
            border: '1px solid',
            borderColor: 'divider',
            maxHeight: '40vh',
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
              발견된 문제 상세 ({allIssuesWithSelection.length}개 선택됨)
            </Typography>
          </Box>
          <Box sx={{ overflow: 'auto', p: 2 }}>
            <List dense>
              {allIssuesWithSelection.slice(0, 20).map((issue, idx) => (
                <ListItem key={`${issue.segmentIndex}-${issue.issueType}-${issue.typeIndex}`} sx={{ py: 0.5 }}>
                  <ListItemText
                    primary={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography variant="caption" color="text.secondary">
                          세그먼트 #{issue.segmentIndex + 1}
                        </Typography>
                        <Chip
                          label={formatIssueType(issue.issueType)}
                          size="small"
                          color={getSeverityColor(issue.issueType)}
                          sx={{ height: '18px' }}
                        />
                        <Typography variant="body2" sx={{ flex: 1 }}>
                          {issue.message.length > 50 
                            ? issue.message.substring(0, 50) + '...' 
                            : issue.message}
                        </Typography>
                      </Box>
                    }
                  />
                </ListItem>
              ))}
              {allIssuesWithSelection.length > 20 && (
                <ListItem>
                  <ListItemText
                    primary={
                      <Typography variant="caption" color="text.secondary">
                        ...그 외 {allIssuesWithSelection.length - 20}개 문제
                      </Typography>
                    }
                  />
                </ListItem>
              )}
            </List>
          </Box>
        </Box>
      )}

      {/* Detailed Results */}
      <Typography variant="h6" gutterBottom>
        세그먼트별 상세 결과
      </Typography>
      
      {report.detailed_results.map((result) => {
        const hasIssues = result.status === 'FAIL';
        
        // Deduplicate issues for each type
        const dedupedCritical = deduplicateIssues(result.critical_issues);
        const dedupedMissing = deduplicateIssues(result.missing_content);
        const dedupedAdded = deduplicateIssues(result.added_content);
        const dedupedNames = deduplicateIssues(result.name_inconsistencies);
        const dedupedMinor = deduplicateIssues(result.minor_issues);
        
        const allIssues = [
          ...dedupedCritical.map(issue => ({ type: 'critical', message: issue })),
          ...dedupedMissing.map(issue => ({ type: 'missing_content', message: issue })),
          ...dedupedAdded.map(issue => ({ type: 'added_content', message: issue })),
          ...dedupedNames.map(issue => ({ type: 'name_inconsistencies', message: issue })),
          ...dedupedMinor.map(issue => ({ type: 'minor', message: issue })),
        ];

        return (
          <Accordion 
            key={result.segment_index}
            defaultExpanded={hasIssues}
            sx={{ 
              mb: 1,
              backgroundColor: hasIssues ? 'rgba(244, 67, 54, 0.08)' : 'rgba(76, 175, 80, 0.08)',
              '&:before': { display: 'none' },
            }}
          >
            <AccordionSummary
              expandIcon={<ExpandMoreIcon />}
              onClick={() => onSegmentClick?.(result.segment_index)}
              sx={{ 
                '&:hover': { backgroundColor: 'action.hover' },
                cursor: 'pointer'
              }}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', width: '100%', gap: 2 }}>
                {result.status === 'PASS' ? (
                  <CheckCircleIcon color="success" />
                ) : (
                  <ErrorIcon color="error" />
                )}
                <Typography sx={{ flexShrink: 0 }}>
                  세그먼트 #{result.segment_index + 1}
                </Typography>
                <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                  {allIssues.length > 0 && (
                    <>
                      {dedupedCritical.length > 0 && (
                        <Chip size="small" label={`${dedupedCritical.length}`} color="error" />
                      )}
                      {dedupedMissing.length > 0 && (
                        <Chip size="small" label={`누락 ${dedupedMissing.length}`} color="warning" />
                      )}
                      {dedupedAdded.length > 0 && (
                        <Chip size="small" label={`추가 ${dedupedAdded.length}`} color="warning" />
                      )}
                      {dedupedNames.length > 0 && (
                        <Chip size="small" label={`이름 ${dedupedNames.length}`} color="info" />
                      )}
                    </>
                  )}
                </Box>
              </Box>
            </AccordionSummary>
            
            <AccordionDetails>
              <ValidationTextSegmentDisplay
                sourceText={result.source_preview}
                translatedText={result.translated_preview}
                issues={allIssues}
                status={result.status}
              />
              
              {/* Selection checkboxes for post-edit with sticky error display */}
              {onIssueSelectionChange && allIssues.length > 0 && (
                <Box sx={{ 
                  mt: 2
                }}>
                  <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1 }}>
                    발견된 문제 상세
                  </Typography>
                  <List dense sx={{ pl: 1 }}>
                    {(() => {
                      // Track indices for each issue type
                      const typeIndices: { [key: string]: number } = {
                        critical: 0,
                        missing_content: 0,
                        added_content: 0,
                        name_inconsistencies: 0,
                        minor: 0,
                      };
                      
                      return allIssues.map((issue, idx) => {
                        const typeIndex = typeIndices[issue.type];
                        typeIndices[issue.type]++;
                        
                        const isSelected = selectedIssues?.[result.segment_index]?.[issue.type]?.[typeIndex] ?? true;
                        
                        return (
                          <ListItem 
                            key={idx} 
                            sx={{ 
                              py: 1, 
                              pl: 0,
                              borderRadius: 1,
                              mb: 1,
                              bgcolor: isSelected ? 'action.selected' : 'transparent',
                              '&:hover': {
                                bgcolor: 'action.hover'
                              }
                            }}
                          >
                            <ListItemIcon sx={{ minWidth: 'auto', mr: 1 }}>
                              <Checkbox
                                edge="start"
                                checked={isSelected}
                                onChange={(e) => onIssueSelectionChange?.(
                                  result.segment_index,
                                  issue.type,
                                  typeIndex,
                                  e.target.checked
                                )}
                                size="small"
                              />
                            </ListItemIcon>
                            <ListItemText
                              primary={
                                <Box>
                                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                                    <Chip 
                                      label={formatIssueType(issue.type)} 
                                      size="small" 
                                      color={getSeverityColor(issue.type)}
                                      variant="filled"
                                      sx={{ height: '20px' }}
                                    />
                                    <Typography variant="caption" color="text.secondary">
                                      #{typeIndex + 1}
                                    </Typography>
                                  </Box>
                                  <Typography 
                                    variant="body2" 
                                    sx={{ 
                                      ml: 1,
                                      color: 'text.primary',
                                      fontSize: '0.875rem',
                                      lineHeight: 1.5
                                    }}
                                  >
                                    {issue.message}
                                  </Typography>
                                </Box>
                              }
                              primaryTypographyProps={{
                                component: 'div'
                              }}
                            />
                          </ListItem>
                        );
                      });
                    })()}
                  </List>
                </Box>
              )}
            </AccordionDetails>
          </Accordion>
        );
      })}
      
      {report.detailed_results.length === 0 && (
        <Alert severity="info">
          <AlertTitle>검증 결과 없음</AlertTitle>
          아직 검증된 세그먼트가 없습니다.
        </Alert>
      )}
    </Box>
  );
}