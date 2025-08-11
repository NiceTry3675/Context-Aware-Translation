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
  FormControlLabel,
  Switch,
  Badge,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import EditIcon from '@mui/icons-material/Edit';
import CompareIcon from '@mui/icons-material/Compare';
import ViewColumnIcon from '@mui/icons-material/ViewColumn';
import { PostEditLog } from '../utils/api';
import { SummaryStatistics } from './shared/SummaryStatistics';
import { TextSegmentDisplay } from './shared/TextSegmentDisplay';
import { IssueChip } from './shared/IssueChip';
import { DiffMode, ViewMode } from './shared/DiffViewer';

interface PostEditLogViewerProps {
  log: PostEditLog;
  onSegmentClick?: (segmentIndex: number) => void;
}

export default function PostEditLogViewer({ log, onSegmentClick }: PostEditLogViewerProps) {
  const [viewMode, setViewMode] = useState<'all' | 'edited' | 'unedited'>('edited');
  const [showDiff, setShowDiff] = useState(true);
  const [diffMode, setDiffMode] = useState<DiffMode>('word');
  const [diffViewMode, setDiffViewMode] = useState<ViewMode>('unified');

  const filteredSegments = log.segments.filter(segment => {
    if (viewMode === 'edited') return segment.was_edited;
    if (viewMode === 'unedited') return !segment.was_edited;
    return true;
  });

  return (
    <Box sx={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', overflow: 'auto' }}>
      {/* Summary Section */}
      <SummaryStatistics
        title="포스트 에디팅 요약"
        stats={[
          { label: '전체 세그먼트', value: log.summary.total_segments },
          { label: '수정된 세그먼트', value: log.summary.segments_edited, color: 'primary' },
          { label: '수정 비율', value: `${log.summary.edit_percentage.toFixed(1)}%`, color: 'secondary' }
        ]}
        issueStats={[
          { type: 'success', count: log.summary.issues_addressed.critical, label: '치명적 오류 수정' },
          { type: 'success', count: log.summary.issues_addressed.missing_content, label: '누락 내용 복원' },
          { type: 'success', count: log.summary.issues_addressed.added_content, label: '불필요 내용 제거' },
          { type: 'success', count: log.summary.issues_addressed.name_inconsistencies, label: '이름 불일치 수정' }
        ]}
      />

      {/* Filter Controls */}
      <Paper elevation={1} sx={{ p: 2, mb: 2 }}>
        <Stack spacing={2}>
          {/* View Mode Selection */}
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

          {/* Diff View Controls - only show when diff is enabled */}
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
            backgroundColor: 'background.paper',
            borderLeft: segment.was_edited ? '4px solid' : 'none',
            borderLeftColor: segment.was_edited ? 'primary.main' : 'transparent',
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
                {segment.issues.critical && segment.issues.critical.length > 0 && (
                  <IssueChip
                    key="critical"
                    type="critical"
                    label={`치명적 ${segment.issues.critical.length}`}
                  />
                )}
                {segment.issues.missing_content && segment.issues.missing_content.length > 0 && (
                  <IssueChip
                    key="missing"
                    type="missing_content"
                    label={`누락 ${segment.issues.missing_content.length}`}
                  />
                )}
                {segment.issues.added_content && segment.issues.added_content.length > 0 && (
                  <IssueChip
                    key="added"
                    type="added_content"
                    label={`추가 ${segment.issues.added_content.length}`}
                  />
                )}
                {segment.issues.name_inconsistencies && segment.issues.name_inconsistencies.length > 0 && (
                  <IssueChip
                    key="names"
                    type="name_inconsistencies"
                    label={`이름 ${segment.issues.name_inconsistencies.length}`}
                  />
                )}
              </Box>
            </Box>
          </AccordionSummary>
          
          <AccordionDetails>
            <Stack spacing={2}>
              <TextSegmentDisplay
                sourceText={segment.source_text}
                translatedText={segment.original_translation}
                editedText={segment.edited_translation}
                showComparison={true}
                hideSource={true}
                showDiff={showDiff && segment.was_edited}
                diffMode={diffMode}
                diffViewMode={diffViewMode}
              />
              
              {/* Changes Made */}
              {segment.was_edited && segment.changes_made && (
                <Box>
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
                </Box>
              )}
            </Stack>
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