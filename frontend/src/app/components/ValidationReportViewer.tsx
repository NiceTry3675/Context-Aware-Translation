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
  Stack,
  Checkbox,
  ListItemIcon,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import WarningIcon from '@mui/icons-material/Warning';
import InfoIcon from '@mui/icons-material/Info';
import { ValidationReport } from '../utils/api';
import { SummaryStatistics } from './shared/SummaryStatistics';
import { TextSegmentDisplay } from './shared/TextSegmentDisplay';

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

  const getSeverityIcon = (issueType: string) => {
    if (issueType === 'critical') return <ErrorIcon fontSize="small" />;
    if (issueType === 'missing_content' || issueType === 'added_content') return <WarningIcon fontSize="small" />;
    if (issueType === 'name_inconsistencies') return <InfoIcon fontSize="small" />;
    return null;
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

  return (
    <Box sx={{ width: '100%' }}>
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

      {/* Detailed Results */}
      <Typography variant="h6" gutterBottom>
        세그먼트별 상세 결과
      </Typography>
      
      {report.detailed_results.map((result) => {
        const hasIssues = result.status === 'FAIL';
        const allIssues = [
          ...result.critical_issues.map(issue => ({ type: 'critical', message: issue })),
          ...result.missing_content.map(issue => ({ type: 'missing_content', message: issue })),
          ...result.added_content.map(issue => ({ type: 'added_content', message: issue })),
          ...result.name_inconsistencies.map(issue => ({ type: 'name_inconsistencies', message: issue })),
          ...result.minor_issues.map(issue => ({ type: 'minor', message: issue })),
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
                      {result.critical_issues.length > 0 && (
                        <Chip size="small" label={`${result.critical_issues.length}`} color="error" />
                      )}
                      {result.missing_content.length > 0 && (
                        <Chip size="small" label={`누락 ${result.missing_content.length}`} color="warning" />
                      )}
                      {result.added_content.length > 0 && (
                        <Chip size="small" label={`추가 ${result.added_content.length}`} color="warning" />
                      )}
                      {result.name_inconsistencies.length > 0 && (
                        <Chip size="small" label={`이름 ${result.name_inconsistencies.length}`} color="info" />
                      )}
                    </>
                  )}
                </Box>
              </Box>
            </AccordionSummary>
            
            <AccordionDetails>
              <Stack spacing={2}>
                <TextSegmentDisplay
                  sourceText={result.source_preview}
                  translatedText={result.translated_preview}
                />
                
                {/* Issues List */}
                {allIssues.length > 0 && (
                  <Box>
                    <Typography variant="subtitle2" gutterBottom>
                      발견된 문제
                    </Typography>
                    <List dense sx={{ bgcolor: 'background.paper', borderRadius: 1 }}>
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
                            <ListItem key={idx} sx={{ py: 0.5 }}>
                              {onIssueSelectionChange && (
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
                              )}
                              <ListItemText
                                primary={
                                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                    {getSeverityIcon(issue.type)}
                                    <Chip 
                                      label={formatIssueType(issue.type)} 
                                      size="small" 
                                      color={getSeverityColor(issue.type)}
                                      variant="outlined"
                                    />
                                    <Typography variant="body2">
                                      {issue.message}
                                    </Typography>
                                  </Box>
                                }
                              />
                            </ListItem>
                          );
                        });
                      })()}
                    </List>
                  </Box>
                )}
              </Stack>
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