'use client';

import React, { useMemo, useState } from 'react';
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
  IconButton,
  Tooltip,
  Grid,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import EditIcon from '@mui/icons-material/Edit';
import CompareIcon from '@mui/icons-material/Compare';
import ViewColumnIcon from '@mui/icons-material/ViewColumn';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
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
  const [displayMode, setDisplayMode] = useState<'changes' | 'final'>('changes');

  // Guard against malformed or partial data
  const segments = useMemo(() => log.segments || [], [log.segments]);
  const summary = log.summary || {
    total_segments: segments.length,
    segments_edited: segments.filter(s => s.was_edited).length,
    edit_percentage: 0,
  };

  const filteredSegments = segments.filter(segment => {
    if (viewMode === 'edited') return segment.was_edited;
    if (viewMode === 'unedited') return !segment.was_edited;
    return true;
  });

  const sortedSegments = useMemo(() => {
    return segments.slice().sort((a, b) => a.segment_index - b.segment_index);
  }, [segments]);

  const finalSourceText = useMemo(() => {
    return sortedSegments
      .map((segment) => segment.source_text)
      .filter((text): text is string => Boolean(text))
      .join('\n');
  }, [sortedSegments]);

  const finalEditedText = useMemo(() => {
    return sortedSegments
      .map((segment) => segment.edited_translation || segment.original_translation || '')
      .join('\n');
  }, [sortedSegments]);

  const handleCopyFinal = (text: string) => {
    if (!text) return;
    navigator.clipboard.writeText(text);
  };

  return (
    <Box sx={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', overflow: 'auto' }}>
      {/* Summary Section */}
      <SummaryStatistics
        title="포스트 에디팅 요약"
        stats={[
          { label: '전체 세그먼트', value: summary.total_segments || 0 },
          { label: '수정된 세그먼트', value: summary.segments_edited || 0, color: 'primary' },
          { label: '수정 비율', value: `${Number(summary.edit_percentage || 0).toFixed(1)}%`, color: 'secondary' }
        ]}
      />

      {/* Filter Controls */}
      <Paper elevation={1} sx={{ p: { xs: 1.5, sm: 2 }, mb: 2 }}>
        <Stack spacing={2}>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} alignItems={{ xs: 'stretch', sm: 'center' }} justifyContent="space-between">
            <ToggleButtonGroup
              value={displayMode}
              exclusive
              onChange={(e, mode) => mode && setDisplayMode(mode)}
              size="small"
              fullWidth={false}
              sx={{ width: { xs: '100%', sm: 'auto' } }}
            >
              <ToggleButton value="changes" sx={{ flex: { xs: 1, sm: 'initial' } }}>
                변경 내역
              </ToggleButton>
              <ToggleButton value="final" sx={{ flex: { xs: 1, sm: 'initial' } }}>
                최종 결과
              </ToggleButton>
            </ToggleButtonGroup>
            {displayMode === 'changes' && (
              <FormControlLabel
                control={(
                  <Switch
                    checked={showDiff}
                    onChange={(e) => setShowDiff(e.target.checked)}
                  />
                )}
                label="변경 사항 강조"
                sx={{ ml: { xs: 0, sm: 2 } }}
              />
            )}
          </Stack>

          {displayMode === 'changes' ? (
            <>
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} alignItems={{ xs: 'stretch', sm: 'center' }}>
                <ToggleButtonGroup
                  value={viewMode}
                  exclusive
                  onChange={(e, newMode) => newMode && setViewMode(newMode)}
                  size="small"
                  fullWidth={false}
                  sx={{ width: { xs: '100%', sm: 'auto' } }}
                >
                  <ToggleButton value="all" sx={{ flex: { xs: 1, sm: 'initial' } }}>
                    전체 ({segments.length})
                  </ToggleButton>
                  <ToggleButton value="edited" sx={{ flex: { xs: 1, sm: 'initial' } }}>
                    <Badge badgeContent={summary.segments_edited || 0} color="primary">
                      <EditIcon fontSize="small" sx={{ mr: 0.5 }} />
                    </Badge>
                    수정됨
                  </ToggleButton>
                  <ToggleButton value="unedited" sx={{ flex: { xs: 1, sm: 'initial' }, fontSize: { xs: '0.7rem', sm: '0.875rem' } }}>
                    수정 안됨 ({(summary.total_segments || 0) - (summary.segments_edited || 0)})
                  </ToggleButton>
                </ToggleButtonGroup>
              </Stack>

              {/* Diff View Controls - only show when diff is enabled */}
              {showDiff && (
                <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} alignItems={{ xs: 'stretch', sm: 'center' }}>
                  <ToggleButtonGroup
                    value={diffViewMode}
                    exclusive
                    onChange={(e, newMode) => newMode && setDiffViewMode(newMode)}
                    size="small"
                    fullWidth={false}
                    sx={{ width: { xs: '100%', sm: 'auto' } }}
                  >
                    <ToggleButton value="unified" sx={{ flex: { xs: 1, sm: 'initial' } }}>
                      <CompareIcon fontSize="small" sx={{ mr: 0.5 }} />
                      통합 보기
                    </ToggleButton>
                    <ToggleButton value="side-by-side" sx={{ flex: { xs: 1, sm: 'initial' } }}>
                      <ViewColumnIcon fontSize="small" sx={{ mr: 0.5 }} />
                      나란히 보기
                    </ToggleButton>
                  </ToggleButtonGroup>

                  <FormControl size="small" sx={{ minWidth: { xs: '100%', sm: 120 } }}>
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
            </>
          ) : (
            <Typography variant="body2" color="text.secondary">
              포스트 에디팅을 통해 생성된 최종 번역문을 확인할 수 있습니다.
            </Typography>
          )}
        </Stack>
      </Paper>

      {displayMode === 'final' ? (
        finalEditedText ? (
          <Paper elevation={0} sx={{ p: 3, border: 1, borderColor: 'divider' }}>
            <Stack spacing={3}>
              <Typography variant="h6">최종 결과</Typography>
              <Grid container spacing={2}>
                {finalSourceText && (
                  <Grid size={{ xs: 12, md: 6 }}>
                    <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 1 }}>
                      <Typography variant="subtitle2" color="text.secondary">
                        원문
                      </Typography>
                      <Tooltip title="원문 복사">
                        <IconButton size="small" onClick={() => handleCopyFinal(finalSourceText)}>
                          <ContentCopyIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </Stack>
                    <Paper variant="outlined" sx={{ p: 2, backgroundColor: 'background.paper' }}>
                      <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                        {finalSourceText}
                      </Typography>
                    </Paper>
                  </Grid>
                )}
                <Grid size={{ xs: 12, md: finalSourceText ? 6 : 12 }}>
                  <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 1 }}>
                    <Typography variant="subtitle2" color="text.secondary">
                      번역문
                    </Typography>
                    <Tooltip title="번역문 복사">
                      <IconButton size="small" onClick={() => handleCopyFinal(finalEditedText)}>
                        <ContentCopyIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </Stack>
                  <Paper variant="outlined" sx={{ p: 2, backgroundColor: 'background.paper' }}>
                    <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                      {finalEditedText}
                    </Typography>
                  </Paper>
                </Grid>
              </Grid>
            </Stack>
          </Paper>
        ) : (
          <Alert severity="info">
            <AlertTitle>최종 결과를 불러올 수 없습니다</AlertTitle>
            포스트 에디팅 결과가 비어 있습니다.
          </Alert>
        )
      ) : (
        <>
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
                    {(segment as any).structured_cases && (segment as any).structured_cases.length > 0 && (
                      <IssueChip key="cases" type="critical" label={`케이스 ${(segment as any).structured_cases.length}`} />
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

                  {/* Changes Made (structured-only) */}
                  {segment.was_edited && segment.changes_made && (
                    <Box>
                      <Typography variant="subtitle2" gutterBottom>
                        적용된 수정 사항
                      </Typography>
                      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                        {segment.changes_made.text_changed && (
                          <Chip size="small" label="내용 수정됨" color="success" />
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
        </>
      )}
    </Box>
  );
}
