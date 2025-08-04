'use client';

import React, { useState } from 'react';
import {
  Box,
  Typography,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip,
  Paper,
  Alert,
  AlertTitle,
  Stack,
  ToggleButtonGroup,
  ToggleButton,
  Divider,
  FormControlLabel,
  Switch,
  Badge,
  Grid,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import EditIcon from '@mui/icons-material/Edit';
import CompareArrowsIcon from '@mui/icons-material/CompareArrows';
import { PostEditLog } from '../utils/api';

interface PostEditLogViewerProps {
  log: PostEditLog;
  onSegmentClick?: (segmentIndex: number) => void;
}

export default function PostEditLogViewer({ log, onSegmentClick }: PostEditLogViewerProps) {
  const [viewMode, setViewMode] = useState<'all' | 'edited' | 'unedited'>('edited');
  const [showDiff, setShowDiff] = useState(true);

  const filteredSegments = log.segments.filter(segment => {
    if (viewMode === 'edited') return segment.was_edited;
    if (viewMode === 'unedited') return !segment.was_edited;
    return true;
  });

  const getIssueChips = (issues: any) => {
    const chips = [];
    if (issues.critical?.length > 0) {
      chips.push(
        <Chip 
          key="critical" 
          size="small" 
          label={`치명적 ${issues.critical.length}`} 
          color="error" 
          variant="outlined" 
        />
      );
    }
    if (issues.missing_content?.length > 0) {
      chips.push(
        <Chip 
          key="missing" 
          size="small" 
          label={`누락 ${issues.missing_content.length}`} 
          color="warning" 
          variant="outlined" 
        />
      );
    }
    if (issues.added_content?.length > 0) {
      chips.push(
        <Chip 
          key="added" 
          size="small" 
          label={`추가 ${issues.added_content.length}`} 
          color="warning" 
          variant="outlined" 
        />
      );
    }
    if (issues.name_inconsistencies?.length > 0) {
      chips.push(
        <Chip 
          key="names" 
          size="small" 
          label={`이름 ${issues.name_inconsistencies.length}`} 
          color="info" 
          variant="outlined" 
        />
      );
    }
    return chips;
  };

  const highlightChanges = (original: string, edited: string) => {
    if (!showDiff || original === edited) return edited;
    
    // Simple diff highlighting - in production, use a proper diff library
    const words1 = original.split(' ');
    const words2 = edited.split(' ');
    
    return edited; // For now, return the edited text as-is
  };

  return (
    <Box sx={{ width: '100%' }}>
      {/* Summary Section */}
      <Paper elevation={1} sx={{ p: 2, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          포스트 에디팅 요약
        </Typography>
        
        <Grid container spacing={2} sx={{ mb: 2 }}>
          <Grid size={4}>
            <Typography variant="body2" color="text.secondary">
              전체 세그먼트
            </Typography>
            <Typography variant="h4">
              {log.summary.total_segments}
            </Typography>
          </Grid>
          <Grid size={4}>
            <Typography variant="body2" color="text.secondary">
              수정된 세그먼트
            </Typography>
            <Typography variant="h4" color="primary">
              {log.summary.segments_edited}
            </Typography>
          </Grid>
          <Grid size={4}>
            <Typography variant="body2" color="text.secondary">
              수정 비율
            </Typography>
            <Typography variant="h4" color="secondary">
              {log.summary.edit_percentage.toFixed(1)}%
            </Typography>
          </Grid>
        </Grid>

        <Divider sx={{ my: 2 }} />
        
        <Typography variant="subtitle2" gutterBottom>
          해결된 문제
        </Typography>
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
          {log.summary.issues_addressed.critical > 0 && (
            <Chip
              size="small"
              icon={<CheckCircleIcon />}
              label={`치명적 오류 ${log.summary.issues_addressed.critical}개 수정`}
              color="success"
              variant="outlined"
            />
          )}
          {log.summary.issues_addressed.missing_content > 0 && (
            <Chip
              size="small"
              icon={<CheckCircleIcon />}
              label={`누락 내용 ${log.summary.issues_addressed.missing_content}개 복원`}
              color="success"
              variant="outlined"
            />
          )}
          {log.summary.issues_addressed.added_content > 0 && (
            <Chip
              size="small"
              icon={<CheckCircleIcon />}
              label={`불필요 내용 ${log.summary.issues_addressed.added_content}개 제거`}
              color="success"
              variant="outlined"
            />
          )}
          {log.summary.issues_addressed.name_inconsistencies > 0 && (
            <Chip
              size="small"
              icon={<CheckCircleIcon />}
              label={`이름 불일치 ${log.summary.issues_addressed.name_inconsistencies}개 수정`}
              color="success"
              variant="outlined"
            />
          )}
        </Stack>
      </Paper>

      {/* Filter Controls */}
      <Paper elevation={1} sx={{ p: 2, mb: 2 }}>
        <Stack direction="row" spacing={2} alignItems="center" justifyContent="space-between">
          <ToggleButtonGroup
            value={viewMode}
            exclusive
            onChange={(e, newMode) => newMode && setViewMode(newMode)}
            size="small"
          >
            <ToggleButton value="all">
              전체 ({log.segments.length})
            </ToggleButton>
            <ToggleButton value="edited">
              <Badge badgeContent={log.summary.segments_edited} color="primary">
                <EditIcon fontSize="small" sx={{ mr: 0.5 }} />
              </Badge>
              수정됨
            </ToggleButton>
            <ToggleButton value="unedited">
              수정 안됨 ({log.summary.total_segments - log.summary.segments_edited})
            </ToggleButton>
          </ToggleButtonGroup>
          
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
      </Paper>

      {/* Segments List */}
      <Typography variant="h6" gutterBottom>
        세그먼트별 상세 내역
      </Typography>
      
      {filteredSegments.map((segment) => (
        <Accordion 
          key={segment.segment_index}
          defaultExpanded={segment.was_edited}
          sx={{ 
            mb: 1,
            backgroundColor: segment.was_edited ? 'info.50' : 'background.paper',
            '&:before': { display: 'none' },
          }}
        >
          <AccordionSummary
            expandIcon={<ExpandMoreIcon />}
            onClick={() => onSegmentClick?.(segment.segment_index)}
            sx={{ 
              '&:hover': { backgroundColor: 'action.hover' },
              cursor: 'pointer'
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', width: '100%', gap: 2 }}>
              {segment.was_edited ? (
                <EditIcon color="primary" />
              ) : (
                <CheckCircleIcon color="disabled" />
              )}
              <Typography sx={{ flexShrink: 0 }}>
                세그먼트 #{segment.segment_index + 1}
              </Typography>
              {segment.was_edited && (
                <Chip 
                  size="small" 
                  label="수정됨" 
                  color="primary" 
                  variant="filled"
                />
              )}
              <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                {getIssueChips(segment.issues)}
              </Box>
            </Box>
          </AccordionSummary>
          
          <AccordionDetails>
            <Grid container spacing={2}>
              {/* Source Text */}
              <Grid size={12}>
                <Typography variant="subtitle2" gutterBottom color="text.secondary">
                  원문
                </Typography>
                <Paper variant="outlined" sx={{ p: 1.5, backgroundColor: 'grey.50' }}>
                  <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                    {segment.source_text}
                  </Typography>
                </Paper>
              </Grid>
              
              {/* Translation Comparison */}
              {segment.was_edited ? (
                <>
                  <Grid size={{ xs: 12, md: 6 }}>
                    <Typography variant="subtitle2" gutterBottom color="text.secondary">
                      수정 전 번역
                    </Typography>
                    <Paper 
                      variant="outlined" 
                      sx={{ 
                        p: 1.5, 
                        backgroundColor: 'error.50',
                        borderColor: 'error.main'
                      }}
                    >
                      <Typography 
                        variant="body2" 
                        sx={{ 
                          whiteSpace: 'pre-wrap',
                          textDecoration: segment.was_edited ? 'line-through' : 'none',
                          opacity: 0.8
                        }}
                      >
                        {segment.original_translation}
                      </Typography>
                    </Paper>
                  </Grid>
                  
                  <Grid size={{ xs: 12, md: 6 }}>
                    <Typography variant="subtitle2" gutterBottom color="text.secondary">
                      수정 후 번역
                    </Typography>
                    <Paper 
                      variant="outlined" 
                      sx={{ 
                        p: 1.5, 
                        backgroundColor: 'success.50',
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
                        {highlightChanges(segment.original_translation, segment.edited_translation)}
                      </Typography>
                    </Paper>
                  </Grid>
                </>
              ) : (
                <Grid size={12}>
                  <Typography variant="subtitle2" gutterBottom color="text.secondary">
                    번역 (변경 없음)
                  </Typography>
                  <Paper variant="outlined" sx={{ p: 1.5, backgroundColor: 'grey.50' }}>
                    <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                      {segment.edited_translation || segment.original_translation}
                    </Typography>
                  </Paper>
                </Grid>
              )}
              
              {/* Changes Made */}
              {segment.was_edited && segment.changes_made && (
                <Grid size={12}>
                  <Typography variant="subtitle2" gutterBottom>
                    적용된 수정 사항
                  </Typography>
                  <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                    {segment.changes_made.critical_fixed && (
                      <Chip size="small" label="치명적 오류 수정" color="success" />
                    )}
                    {segment.changes_made.missing_content_fixed && (
                      <Chip size="small" label="누락 내용 복원" color="success" />
                    )}
                    {segment.changes_made.added_content_fixed && (
                      <Chip size="small" label="불필요 내용 제거" color="success" />
                    )}
                    {segment.changes_made.name_inconsistencies_fixed && (
                      <Chip size="small" label="이름 일관성 수정" color="success" />
                    )}
                  </Stack>
                </Grid>
              )}
            </Grid>
          </AccordionDetails>
        </Accordion>
      ))}
      
      {filteredSegments.length === 0 && (
        <Alert severity="info">
          <AlertTitle>표시할 세그먼트가 없습니다</AlertTitle>
          선택한 필터 조건에 맞는 세그먼트가 없습니다.
        </Alert>
      )}
    </Box>
  );
}