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
  LinearProgress,
  Paper,
  Divider,
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

  return (
    <Box sx={{ width: '100%' }}>
      {/* Summary Section */}
      <Paper elevation={1} sx={{ p: 2, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          검증 요약
        </Typography>
        
        <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
          <Box sx={{ flex: 1 }}>
            <Typography variant="body2" color="text.secondary">
              전체 세그먼트
            </Typography>
            <Typography variant="h4">
              {report.summary.total_segments}
            </Typography>
          </Box>
          <Box sx={{ flex: 1 }}>
            <Typography variant="body2" color="text.secondary">
              검증된 세그먼트
            </Typography>
            <Typography variant="h4">
              {report.summary.validated_segments}
            </Typography>
          </Box>
        </Box>

        <Box sx={{ mb: 2 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
            <Typography variant="body2">
              통과율
            </Typography>
            <Typography variant="body2" fontWeight="bold">
              {report.summary.pass_rate.toFixed(1)}%
            </Typography>
          </Box>
          <LinearProgress 
            variant="determinate" 
            value={report.summary.pass_rate} 
            color={report.summary.pass_rate >= 80 ? 'success' : report.summary.pass_rate >= 60 ? 'warning' : 'error'}
            sx={{ height: 8, borderRadius: 1 }}
          />
        </Box>

        <Box sx={{ display: 'flex', gap: 1 }}>
          <Box sx={{ flex: 1 }}>
            <Stack direction="row" spacing={1} alignItems="center">
              <CheckCircleIcon color="success" fontSize="small" />
              <Typography variant="body2">
                통과: {report.summary.passed}
              </Typography>
            </Stack>
          </Box>
          <Box sx={{ flex: 1 }}>
            <Stack direction="row" spacing={1} alignItems="center">
              <ErrorIcon color="error" fontSize="small" />
              <Typography variant="body2">
                실패: {report.summary.failed}
              </Typography>
            </Stack>
          </Box>
        </Box>

        {/* Issue Statistics */}
        <Divider sx={{ my: 2 }} />
        <Typography variant="subtitle2" gutterBottom>
          발견된 문제
        </Typography>
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
          {report.summary.total_critical_issues > 0 && (
            <Chip
              size="small"
              icon={<ErrorIcon />}
              label={`치명적: ${report.summary.total_critical_issues}`}
              color="error"
              variant="outlined"
            />
          )}
          {report.summary.total_missing_content > 0 && (
            <Chip
              size="small"
              icon={<WarningIcon />}
              label={`누락: ${report.summary.total_missing_content}`}
              color="warning"
              variant="outlined"
            />
          )}
          {report.summary.total_added_content > 0 && (
            <Chip
              size="small"
              icon={<WarningIcon />}
              label={`추가: ${report.summary.total_added_content}`}
              color="warning"
              variant="outlined"
            />
          )}
          {report.summary.total_name_inconsistencies > 0 && (
            <Chip
              size="small"
              icon={<InfoIcon />}
              label={`이름 불일치: ${report.summary.total_name_inconsistencies}`}
              color="info"
              variant="outlined"
            />
          )}
        </Stack>
      </Paper>

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
              backgroundColor: hasIssues ? 'error.50' : 'success.50',
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
                <Box sx={{ display: { xs: 'block', md: 'flex' }, gap: 2 }}>
                  {/* Source Text */}
                  <Box sx={{ flex: 1, mb: { xs: 2, md: 0 } }}>
                    <Typography variant="subtitle2" gutterBottom color="text.secondary">
                      원문
                    </Typography>
                    <Paper variant="outlined" sx={{ p: 1.5, backgroundColor: 'grey.50' }}>
                      <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                        {result.source_preview}
                      </Typography>
                    </Paper>
                  </Box>
                  
                  {/* Translated Text */}
                  <Box sx={{ flex: 1 }}>
                    <Typography variant="subtitle2" gutterBottom color="text.secondary">
                      번역문
                    </Typography>
                    <Paper variant="outlined" sx={{ p: 1.5, backgroundColor: 'grey.50' }}>
                      <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                        {result.translated_preview}
                      </Typography>
                    </Paper>
                  </Box>
                </Box>
                
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
                                    onChange={(e) => onIssueSelectionChange(
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