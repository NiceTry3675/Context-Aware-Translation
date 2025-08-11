'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Box,
  Typography,
  Paper,
  Stack,
  Divider,
  IconButton,
  Tooltip,
  Grid,
  CircularProgress,
  Button,
  Alert,
} from '@mui/material';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import { TranslationContent, TranslationSegments, PostEditLog } from '../utils/api';

interface InfiniteScrollTranslationViewerProps {
  content: TranslationContent;
  sourceText?: string;
  segments?: TranslationSegments | null;
  postEditLog?: PostEditLog | null;
  jobId: string;
  onLoadMoreSegments: (offset: number, limit: number) => Promise<{
    segments: any[];
    has_more: boolean;
    total_segments: number;
  }>;
}

export default function InfiniteScrollTranslationViewer({
  content,
  sourceText,
  segments: initialSegments,
  postEditLog,
  jobId,
  onLoadMoreSegments,
}: InfiniteScrollTranslationViewerProps) {
  const [loadedSegments, setLoadedSegments] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [totalSegments, setTotalSegments] = useState(0);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const loadMoreTriggerRef = useRef<HTMLDivElement>(null);
  
  const loadMoreSegments = useCallback(async (offset: number) => {
    setIsLoading(true);
    setError(null);
    
    console.log('Loading segments from offset:', offset);
    
    try {
      const result = await onLoadMoreSegments(offset, 3);
      
      console.log('Loaded segments:', result.segments.length, 'Has more:', result.has_more);
      
      if (offset === 0) {
        setLoadedSegments(result.segments);
      } else {
        setLoadedSegments(prev => [...prev, ...result.segments]);
      }
      
      setHasMore(result.has_more);
      setTotalSegments(result.total_segments);
    } catch (err) {
      console.error('Error loading segments:', err);
      setError(err instanceof Error ? err.message : 'Failed to load more segments');
    } finally {
      setIsLoading(false);
    }
  }, [onLoadMoreSegments]);
  
  // Initialize by loading first batch from API
  useEffect(() => {
    // Always load segments from API for dynamic loading
    // This ensures pagination works properly
    loadMoreSegments(0);
  }, [jobId]); // Only reload when job changes
  
  // Intersection Observer for infinite scrolling
  useEffect(() => {
    if (!loadMoreTriggerRef.current || !hasMore || isLoading) return;
    
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasMore && !isLoading) {
          loadMoreSegments(loadedSegments.length);
        }
      },
      {
        root: scrollContainerRef.current,
        rootMargin: '200px',
        threshold: 0.1,
      }
    );
    
    observer.observe(loadMoreTriggerRef.current);
    
    return () => observer.disconnect();
  }, [hasMore, isLoading, loadedSegments.length, loadMoreSegments]);
  
  // Merge translated text from loaded segments
  const mergedTranslatedText = React.useMemo(() => {
    if (loadedSegments.length > 0) {
      // Check if segments have post-edit data (edited_translation field)
      const firstSegment = loadedSegments[0];
      const hasPostEditData = 'edited_translation' in firstSegment || 'original_translation' in firstSegment;
      
      if (hasPostEditData) {
        return loadedSegments
          .sort((a, b) => a.segment_index - b.segment_index)
          .map(segment => segment.edited_translation || segment.original_translation || segment.translated_text)
          .join('\n');
      }
      
      return loadedSegments
        .sort((a, b) => a.segment_index - b.segment_index)
        .map(segment => segment.translated_text)
        .join('\n');
    }
    
    // Fallback to content if no segments loaded yet
    return content.content;
  }, [loadedSegments, content.content]);
  
  // Merge source text from loaded segments
  const mergedSourceText = React.useMemo(() => {
    if (sourceText) {
      // If full source text is provided, show corresponding portion
      const sourceLines = sourceText.split('\n');
      const segmentCount = loadedSegments.length;
      // Approximate portion based on loaded segments ratio
      const portionRatio = totalSegments > 0 ? segmentCount / totalSegments : 1;
      const linesToShow = Math.ceil(sourceLines.length * portionRatio);
      return sourceLines.slice(0, linesToShow).join('\n');
    }
    
    if (content.source_content) {
      const sourceLines = content.source_content.split('\n');
      const segmentCount = loadedSegments.length;
      const portionRatio = totalSegments > 0 ? segmentCount / totalSegments : 1;
      const linesToShow = Math.ceil(sourceLines.length * portionRatio);
      return sourceLines.slice(0, linesToShow).join('\n');
    }
    
    if (loadedSegments.length > 0 && loadedSegments[0].source_text !== undefined) {
      return loadedSegments
        .sort((a, b) => a.segment_index - b.segment_index)
        .map(segment => segment.source_text)
        .join('\n');
    }
    
    return undefined;
  }, [sourceText, content.source_content, loadedSegments, totalSegments]);
  
  const handleCopyContent = () => {
    navigator.clipboard.writeText(mergedTranslatedText);
  };
  
  const handleCopySource = () => {
    if (mergedSourceText) {
      navigator.clipboard.writeText(mergedSourceText);
    }
  };
  
  const handleLoadAll = async () => {
    if (totalSegments <= loadedSegments.length) return;
    
    setIsLoading(true);
    setError(null);
    
    try {
      // Load all remaining segments
      const result = await onLoadMoreSegments(loadedSegments.length, totalSegments - loadedSegments.length);
      setLoadedSegments(prev => [...prev, ...result.segments]);
      setHasMore(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load all segments');
    } finally {
      setIsLoading(false);
    }
  };
  
  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
      <Stack spacing={2} sx={{ height: '100%', minHeight: 0 }}>
        {/* Header with file info */}
        <Paper elevation={0} sx={{ p: 2, backgroundColor: 'background.default', flexShrink: 0 }}>
          <Stack direction="row" justifyContent="space-between" alignItems="center">
            <Box>
              <Typography variant="subtitle1" fontWeight="medium">
                번역된 파일
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {content.filename}
              </Typography>
              {content.completed_at && (
                <Typography variant="caption" color="text.secondary">
                  완료 시간: {new Date(content.completed_at).toLocaleString('ko-KR')}
                </Typography>
              )}
            </Box>
            {hasMore && totalSegments > 0 && (
              <Box>
                <Typography variant="caption" color="text.secondary" sx={{ mr: 2 }}>
                  {loadedSegments.length} / {totalSegments} 세그먼트 로드됨
                </Typography>
                <Button
                  variant="outlined"
                  size="small"
                  onClick={handleLoadAll}
                  disabled={isLoading}
                >
                  전체 로드
                </Button>
              </Box>
            )}
          </Stack>
        </Paper>
        
        <Divider />
        
        {/* Content display - side by side if source is available */}
        {mergedSourceText ? (
          <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            {/* Fixed headers */}
            <Grid container spacing={2} sx={{ mb: 2 }}>
              <Grid size={{ xs: 12, md: 6 }}>
                <Stack direction="row" justifyContent="space-between" alignItems="center">
                  <Typography variant="h6" color="text.secondary">
                    원문
                  </Typography>
                  <Tooltip title="원문 복사">
                    <IconButton onClick={handleCopySource} size="small">
                      <ContentCopyIcon />
                    </IconButton>
                  </Tooltip>
                </Stack>
              </Grid>
              <Grid size={{ xs: 12, md: 6 }}>
                <Stack direction="row" justifyContent="space-between" alignItems="center">
                  <Typography variant="h6" color="text.secondary">
                    번역문
                  </Typography>
                  <Tooltip title="번역문 복사">
                    <IconButton onClick={handleCopyContent} size="small">
                      <ContentCopyIcon />
                    </IconButton>
                  </Tooltip>
                </Stack>
              </Grid>
            </Grid>
            
            {/* Shared scrollable content area */}
            <Box
              ref={scrollContainerRef}
              sx={{
                flex: 1,
                overflowY: 'auto',
                border: 1,
                borderColor: 'divider',
                borderRadius: 1,
              }}
            >
              <Grid container spacing={0}>
                {/* Source content */}
                <Grid size={{ xs: 12, md: 6 }}>
                  <Paper elevation={0} sx={{ p: 3, height: '100%', borderRadius: 0, borderRight: { md: 1 }, borderColor: 'divider' }}>
                    <Typography
                      variant="body2"
                      sx={{
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word',
                      }}
                    >
                      {mergedSourceText}
                    </Typography>
                  </Paper>
                </Grid>
                
                {/* Translated content */}
                <Grid size={{ xs: 12, md: 6 }}>
                  <Paper elevation={0} sx={{ p: 3, height: '100%', borderRadius: 0 }}>
                    <Typography
                      variant="body2"
                      sx={{
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word',
                      }}
                    >
                      {mergedTranslatedText}
                    </Typography>
                  </Paper>
                </Grid>
              </Grid>
              
              {/* Loading trigger and indicator */}
              <Box ref={loadMoreTriggerRef} sx={{ p: 2, textAlign: 'center' }}>
                {isLoading && (
                  <Stack spacing={1} alignItems="center">
                    <CircularProgress size={24} />
                    <Typography variant="caption" color="text.secondary">
                      더 많은 내용을 불러오는 중...
                    </Typography>
                  </Stack>
                )}
                {error && (
                  <Alert severity="error" sx={{ mt: 2 }}>
                    {error}
                  </Alert>
                )}
                {!hasMore && !isLoading && totalSegments > 0 && (
                  <Typography variant="body2" color="text.secondary">
                    모든 내용을 불러왔습니다
                  </Typography>
                )}
              </Box>
            </Box>
          </Box>
        ) : (
          // Original single column view when no source text
          <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            <Stack direction="row" justifyContent="space-between" alignItems="center" mb={2}>
              <Typography variant="h6" color="text.secondary">
                번역문
              </Typography>
              <Tooltip title="번역문 복사">
                <IconButton onClick={handleCopyContent} size="small">
                  <ContentCopyIcon />
                </IconButton>
              </Tooltip>
            </Stack>
            <Box
              ref={scrollContainerRef}
              sx={{
                flex: 1,
                overflowY: 'auto',
                border: 1,
                borderColor: 'divider',
                borderRadius: 1,
              }}
            >
              <Paper elevation={0} sx={{ p: 3, borderRadius: 0 }}>
                <Typography
                  variant="body2"
                  sx={{
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                  }}
                >
                  {mergedTranslatedText}
                </Typography>
              </Paper>
              
              {/* Loading trigger and indicator */}
              <Box ref={loadMoreTriggerRef} sx={{ p: 2, textAlign: 'center' }}>
                {isLoading && (
                  <Stack spacing={1} alignItems="center">
                    <CircularProgress size={24} />
                    <Typography variant="caption" color="text.secondary">
                      더 많은 내용을 불러오는 중...
                    </Typography>
                  </Stack>
                )}
                {error && (
                  <Alert severity="error" sx={{ mt: 2 }}>
                    {error}
                  </Alert>
                )}
                {!hasMore && !isLoading && totalSegments > 0 && (
                  <Typography variant="body2" color="text.secondary">
                    모든 내용을 불러왔습니다
                  </Typography>
                )}
              </Box>
            </Box>
          </Box>
        )}
      </Stack>
    </Box>
  );
}