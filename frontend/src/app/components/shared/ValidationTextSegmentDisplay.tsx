'use client';

import React from 'react';
import { 
  Box, 
  Typography, 
  Paper,
  Chip,
  Alert,
  Stack,
  Divider,
  useTheme,
  alpha
} from '@mui/material';
import ErrorIcon from '@mui/icons-material/Error';
import WarningIcon from '@mui/icons-material/Warning';
import InfoIcon from '@mui/icons-material/Info';
import ReportProblemIcon from '@mui/icons-material/ReportProblem';

interface Issue {
  type: string;
  message: string;
}

interface ValidationTextSegmentDisplayProps {
  sourceText: string;
  translatedText?: string;
  issues?: Issue[];
  status: 'PASS' | 'FAIL';
}

export function ValidationTextSegmentDisplay({ 
  sourceText, 
  translatedText,
  issues = [],
  status
}: ValidationTextSegmentDisplayProps) {
  const theme = useTheme();

  const getSeverityColor = (issueType: string) => {
    switch(issueType) {
      case 'critical': return theme.palette.error.main;
      case 'missing_content': return theme.palette.warning.main;
      case 'added_content': return theme.palette.warning.dark;
      case 'name_inconsistencies': return theme.palette.info.main;
      default: return theme.palette.grey[600];
    }
  };

  const getSeverityBgColor = (issueType: string) => {
    switch(issueType) {
      case 'critical': return alpha(theme.palette.error.main, 0.1);
      case 'missing_content': return alpha(theme.palette.warning.main, 0.1);
      case 'added_content': return alpha(theme.palette.warning.dark, 0.1);
      case 'name_inconsistencies': return alpha(theme.palette.info.main, 0.1);
      default: return alpha(theme.palette.grey[600], 0.1);
    }
  };

  const getSeverityIcon = (issueType: string) => {
    switch(issueType) {
      case 'critical': return <ErrorIcon fontSize="small" />;
      case 'missing_content': return <WarningIcon fontSize="small" />;
      case 'added_content': return <ReportProblemIcon fontSize="small" />;
      case 'name_inconsistencies': return <InfoIcon fontSize="small" />;
      default: return null;
    }
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

  // Group issues by type for better organization
  const groupedIssues = issues.reduce((acc, issue) => {
    if (!acc[issue.type]) {
      acc[issue.type] = [];
    }
    acc[issue.type].push(issue.message);
    return acc;
  }, {} as Record<string, string[]>);

  // Priority order for issue types
  const issuePriority = ['critical', 'missing_content', 'added_content', 'name_inconsistencies', 'minor'];
  const sortedIssueTypes = Object.keys(groupedIssues).sort(
    (a, b) => issuePriority.indexOf(a) - issuePriority.indexOf(b)
  );

  return (
    <Stack spacing={2}>
      <Box sx={{ display: { xs: 'block', md: 'flex' }, gap: 2 }}>
        {/* Source Text */}
        <Box sx={{ flex: 1, mb: { xs: 2, md: 0 } }}>
          <Typography variant="subtitle2" gutterBottom color="text.secondary">
            원문
          </Typography>
          <Paper 
            variant="outlined" 
            sx={{ 
              p: 2, 
              backgroundColor: 'background.paper',
              minHeight: '120px'
            }}
          >
            <Typography 
              variant="body2" 
              sx={{ 
                whiteSpace: 'pre-wrap', 
                wordBreak: 'break-word',
                lineHeight: 1.8
              }}
            >
              {sourceText}
            </Typography>
          </Paper>
        </Box>
        
        {/* Translated Text with Issue Indicators */}
        <Box sx={{ flex: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
            <Typography variant="subtitle2" color="text.secondary">
              번역문
            </Typography>
            {status === 'FAIL' && (
              <Chip 
                size="small" 
                label={`${issues.length}개 문제`}
                color="error"
                variant="outlined"
                icon={<ErrorIcon />}
              />
            )}
          </Box>
          <Paper 
            variant="outlined" 
            sx={{ 
              p: 2, 
              backgroundColor: status === 'FAIL' 
                ? alpha(theme.palette.error.main, 0.05)
                : 'background.paper',
              borderColor: status === 'FAIL' 
                ? theme.palette.error.main 
                : theme.palette.divider,
              minHeight: '120px',
              position: 'relative'
            }}
          >
            <Typography 
              variant="body2" 
              sx={{ 
                whiteSpace: 'pre-wrap', 
                wordBreak: 'break-word',
                lineHeight: 1.8
              }}
            >
              {translatedText}
            </Typography>
          </Paper>
        </Box>
      </Box>

      {/* Issues Section - Displayed below both texts */}
      {issues.length > 0 && (
        <Paper 
          sx={{ 
            p: 2, 
            backgroundColor: alpha(theme.palette.warning.main, 0.05),
            borderLeft: `4px solid ${theme.palette.warning.main}`
          }}
        >
          <Stack spacing={2}>
            <Typography 
              variant="subtitle2" 
              sx={{ 
                display: 'flex', 
                alignItems: 'center', 
                gap: 1,
                fontWeight: 'bold'
              }}
            >
              <WarningIcon color="warning" fontSize="small" />
              검증 결과: {issues.length}개 문제 발견
            </Typography>
            
            <Stack spacing={1.5}>
              {sortedIssueTypes.map((issueType) => (
                <Box key={issueType}>
                  <Box 
                    sx={{ 
                      p: 1.5,
                      backgroundColor: getSeverityBgColor(issueType),
                      borderRadius: 1,
                      border: `1px solid ${getSeverityColor(issueType)}`,
                    }}
                  >
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                      {getSeverityIcon(issueType)}
                      <Chip 
                        label={formatIssueType(issueType)} 
                        size="small" 
                        sx={{ 
                          backgroundColor: getSeverityColor(issueType),
                          color: 'white',
                          fontWeight: 'bold'
                        }}
                      />
                      <Typography variant="caption" color="text.secondary">
                        ({groupedIssues[issueType].length}개)
                      </Typography>
                    </Box>
                    
                    <Stack spacing={0.5} sx={{ ml: 3 }}>
                      {groupedIssues[issueType].map((message, idx) => (
                        <Box 
                          key={idx}
                          sx={{ 
                            display: 'flex',
                            alignItems: 'flex-start',
                            gap: 1
                          }}
                        >
                          <Typography 
                            variant="caption" 
                            sx={{ 
                              color: getSeverityColor(issueType),
                              fontWeight: 'bold',
                              minWidth: '20px'
                            }}
                          >
                            •
                          </Typography>
                          <Typography 
                            variant="body2" 
                            sx={{ 
                              flex: 1,
                              color: theme.palette.text.primary,
                              lineHeight: 1.6
                            }}
                          >
                            {message}
                          </Typography>
                        </Box>
                      ))}
                    </Stack>
                  </Box>
                </Box>
              ))}
            </Stack>

            {/* Additional context for understanding issues */}
            <Divider sx={{ my: 1 }} />
            <Alert severity="info" variant="outlined" sx={{ py: 1 }}>
              <Typography variant="caption">
                💡 <strong>문제 해결 가이드:</strong> 
                {groupedIssues['critical'] && ' 치명적 오류는 즉시 수정이 필요합니다.'}
                {groupedIssues['missing_content'] && ' 누락된 내용은 원문을 다시 확인하세요.'}
                {groupedIssues['added_content'] && ' 추가된 내용은 원문에 없는 내용입니다.'}
                {groupedIssues['name_inconsistencies'] && ' 이름 불일치는 용어집을 확인하세요.'}
              </Typography>
            </Alert>
          </Stack>
        </Paper>
      )}
    </Stack>
  );
}