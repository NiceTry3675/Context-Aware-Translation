'use client';

import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Card,
  CardMedia,
  CardContent,
  Typography,
  IconButton,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  CircularProgress,
  Alert,
  Tooltip,
  Chip,
  Stack,
} from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import DeleteIcon from '@mui/icons-material/Delete';
import DownloadIcon from '@mui/icons-material/Download';
import ZoomInIcon from '@mui/icons-material/ZoomIn';
import AddPhotoAlternateIcon from '@mui/icons-material/AddPhotoAlternate';

interface Illustration {
  segment_index: number;
  illustration_path: string;
  prompt: string;
  success: boolean;
}

interface IllustrationViewerProps {
  jobId: string;
  illustrations?: Illustration[];
  status?: string;
  count?: number;
  onGenerateIllustrations?: () => void;
  onRegenerateIllustration?: (segmentIndex: number) => void;
  onDeleteIllustration?: (segmentIndex: number) => void;
}

export default function IllustrationViewer({
  jobId,
  illustrations = [],
  status,
  count = 0,
  onGenerateIllustrations,
  onRegenerateIllustration,
  onDeleteIllustration,
}: IllustrationViewerProps) {
  const [selectedImage, setSelectedImage] = useState<Illustration | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadedImages, setLoadedImages] = useState<{ [key: number]: string }>({});

  // Load illustrations from API
  useEffect(() => {
    if (jobId && illustrations.length > 0) {
      loadIllustrationImages();
    }
  }, [jobId, illustrations]);

  const loadIllustrationImages = async () => {
    const imagePromises = illustrations.map(async (ill) => {
      if (ill.success) {
        try {
          const response = await fetch(
            `/api/v1/illustrations/${jobId}/illustration/${ill.segment_index}`,
            {
              headers: {
                Authorization: `Bearer ${localStorage.getItem('token')}`,
              },
            }
          );
          if (response.ok) {
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            return { index: ill.segment_index, url };
          }
        } catch (error) {
          console.error(`Failed to load illustration ${ill.segment_index}:`, error);
        }
      }
      return null;
    });

    const results = await Promise.all(imagePromises);
    const imageMap: { [key: number]: string } = {};
    results.forEach((result) => {
      if (result) {
        imageMap[result.index] = result.url;
      }
    });
    setLoadedImages(imageMap);
  };

  const handleDownload = (illustration: Illustration) => {
    const imageUrl = loadedImages[illustration.segment_index];
    if (imageUrl) {
      const link = document.createElement('a');
      link.href = imageUrl;
      link.download = `segment_${illustration.segment_index}_illustration.png`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  };

  const handleRegenerate = async (segmentIndex: number) => {
    if (onRegenerateIllustration) {
      setLoading(true);
      await onRegenerateIllustration(segmentIndex);
      setLoading(false);
    }
  };

  const handleDelete = async (segmentIndex: number) => {
    if (onDeleteIllustration) {
      await onDeleteIllustration(segmentIndex);
      // Remove from loaded images
      const newLoadedImages = { ...loadedImages };
      delete newLoadedImages[segmentIndex];
      setLoadedImages(newLoadedImages);
    }
  };

  const handleImageClick = (illustration: Illustration) => {
    setSelectedImage(illustration);
  };

  const handleCloseDialog = () => {
    setSelectedImage(null);
  };

  if (status === 'NOT_STARTED' || !status) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="info" sx={{ mb: 2 }}>
          삽화가 아직 생성되지 않았습니다.
        </Alert>
        {onGenerateIllustrations && (
          <Button
            variant="contained"
            startIcon={<AddPhotoAlternateIcon />}
            onClick={onGenerateIllustrations}
            color="primary"
          >
            삽화 생성 시작
          </Button>
        )}
      </Box>
    );
  }

  if (status === 'IN_PROGRESS') {
    return (
      <Box sx={{ p: 3, display: 'flex', alignItems: 'center', gap: 2 }}>
        <CircularProgress />
        <Typography>삽화 생성 중입니다...</Typography>
      </Box>
    );
  }

  if (status === 'FAILED') {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error" sx={{ mb: 2 }}>
          삽화 생성 중 오류가 발생했습니다.
        </Alert>
        {onGenerateIllustrations && (
          <Button
            variant="contained"
            startIcon={<RefreshIcon />}
            onClick={onGenerateIllustrations}
            color="primary"
          >
            다시 시도
          </Button>
        )}
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 3 }}>
        <Typography variant="h6">
          생성된 삽화 ({count}개)
        </Typography>
        {onGenerateIllustrations && (
          <Button
            variant="outlined"
            startIcon={<AddPhotoAlternateIcon />}
            onClick={onGenerateIllustrations}
            size="small"
          >
            추가 생성
          </Button>
        )}
      </Stack>

      <Grid container spacing={3}>
        {illustrations.map((illustration) => (
          <Grid key={illustration.segment_index} size={{ xs: 12, sm: 6, md: 4, lg: 3 }}>
            <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
              {loadedImages[illustration.segment_index] ? (
                <CardMedia
                  component="img"
                  height="200"
                  image={loadedImages[illustration.segment_index]}
                  alt={`Segment ${illustration.segment_index} illustration`}
                  sx={{ cursor: 'pointer', objectFit: 'cover' }}
                  onClick={() => handleImageClick(illustration)}
                />
              ) : (
                <Box
                  sx={{
                    height: 200,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    bgcolor: 'grey.200',
                  }}
                >
                  {illustration.success ? (
                    <CircularProgress />
                  ) : (
                    <Typography color="text.secondary">생성 실패</Typography>
                  )}
                </Box>
              )}
              <CardContent sx={{ flexGrow: 1 }}>
                <Stack spacing={1}>
                  <Typography variant="subtitle2" gutterBottom>
                    세그먼트 {illustration.segment_index}
                  </Typography>
                  {illustration.success ? (
                    <Chip label="생성 완료" color="success" size="small" />
                  ) : (
                    <Chip label="생성 실패" color="error" size="small" />
                  )}
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      display: '-webkit-box',
                      WebkitLineClamp: 2,
                      WebkitBoxOrient: 'vertical',
                    }}
                  >
                    {illustration.prompt}
                  </Typography>
                </Stack>
              </CardContent>
              <Box sx={{ p: 1, display: 'flex', justifyContent: 'flex-end', gap: 1 }}>
                <Tooltip title="확대">
                  <IconButton
                    size="small"
                    onClick={() => handleImageClick(illustration)}
                    disabled={!illustration.success}
                  >
                    <ZoomInIcon />
                  </IconButton>
                </Tooltip>
                <Tooltip title="다운로드">
                  <IconButton
                    size="small"
                    onClick={() => handleDownload(illustration)}
                    disabled={!illustration.success}
                  >
                    <DownloadIcon />
                  </IconButton>
                </Tooltip>
                {onRegenerateIllustration && (
                  <Tooltip title="재생성">
                    <IconButton
                      size="small"
                      onClick={() => handleRegenerate(illustration.segment_index)}
                      disabled={loading}
                    >
                      <RefreshIcon />
                    </IconButton>
                  </Tooltip>
                )}
                {onDeleteIllustration && (
                  <Tooltip title="삭제">
                    <IconButton
                      size="small"
                      onClick={() => handleDelete(illustration.segment_index)}
                      color="error"
                    >
                      <DeleteIcon />
                    </IconButton>
                  </Tooltip>
                )}
              </Box>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Image Dialog */}
      <Dialog
        open={!!selectedImage}
        onClose={handleCloseDialog}
        maxWidth="lg"
        fullWidth
      >
        {selectedImage && (
          <>
            <DialogTitle>
              세그먼트 {selectedImage.segment_index} 삽화
            </DialogTitle>
            <DialogContent>
              {loadedImages[selectedImage.segment_index] && (
                <Box sx={{ textAlign: 'center' }}>
                  <img
                    src={loadedImages[selectedImage.segment_index]}
                    alt={`Segment ${selectedImage.segment_index}`}
                    style={{
                      maxWidth: '100%',
                      maxHeight: '70vh',
                      objectFit: 'contain',
                    }}
                  />
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{ mt: 2, p: 2, bgcolor: 'grey.100', borderRadius: 1 }}
                  >
                    프롬프트: {selectedImage.prompt}
                  </Typography>
                </Box>
              )}
            </DialogContent>
            <DialogActions>
              <Button onClick={() => handleDownload(selectedImage)}>다운로드</Button>
              <Button onClick={handleCloseDialog}>닫기</Button>
            </DialogActions>
          </>
        )}
      </Dialog>
    </Box>
  );
}