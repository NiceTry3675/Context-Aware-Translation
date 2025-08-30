'use client';

import React, { useState, useEffect } from 'react';
import {
  Box,
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
  illustration_path?: string;
  prompt: string;
  success: boolean;
  type?: string;  // 'image' or 'prompt'
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
  const [loadedPrompts, setLoadedPrompts] = useState<{ [key: number]: any }>({});

  // Load illustrations from API
  useEffect(() => {
    if (jobId && illustrations.length > 0) {
      loadIllustrations();
    }
  }, [jobId, illustrations]);

  const loadIllustrations = async () => {
    const illustrationPromises = illustrations.map(async (ill) => {
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
            // Check if response is image or JSON
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('image')) {
              // It's an image
              const blob = await response.blob();
              const url = URL.createObjectURL(blob);
              return { index: ill.segment_index, type: 'image', data: url };
            } else {
              // It's JSON (prompt)
              const data = await response.json();
              return { index: ill.segment_index, type: 'prompt', data };
            }
          }
        } catch (error) {
          console.error(`Failed to load illustration ${ill.segment_index}:`, error);
        }
      }
      return null;
    });

    const results = await Promise.all(illustrationPromises);
    const imageMap: { [key: number]: string } = {};
    const promptMap: { [key: number]: any } = {};
    
    results.forEach((result) => {
      if (result) {
        if (result.type === 'image') {
          imageMap[result.index] = result.data;
        } else {
          promptMap[result.index] = result.data;
        }
      }
    });
    
    setLoadedImages(imageMap);
    setLoadedPrompts(promptMap);
  };

  const handleDownload = (illustration: Illustration) => {
    // Check if we have an image first
    const imageUrl = loadedImages[illustration.segment_index];
    if (imageUrl) {
      const link = document.createElement('a');
      link.href = imageUrl;
      link.download = `segment_${illustration.segment_index}_illustration.png`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } else {
      // Fall back to prompt download
      const promptData = loadedPrompts[illustration.segment_index];
      if (promptData) {
        const blob = new Blob([JSON.stringify(promptData, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `segment_${illustration.segment_index}_prompt.json`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
      }
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
      // Remove from loaded images and prompts
      const newLoadedImages = { ...loadedImages };
      delete newLoadedImages[segmentIndex];
      setLoadedImages(newLoadedImages);
      
      const newLoadedPrompts = { ...loadedPrompts };
      delete newLoadedPrompts[segmentIndex];
      setLoadedPrompts(newLoadedPrompts);
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

      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)', md: 'repeat(3, 1fr)', lg: 'repeat(4, 1fr)' }, gap: 3 }}>
        {illustrations.map((illustration) => (
          <Card key={illustration.segment_index} sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
              {loadedImages[illustration.segment_index] ? (
                <CardMedia
                  component="img"
                  height="200"
                  image={loadedImages[illustration.segment_index]}
                  alt={`Segment ${illustration.segment_index} illustration`}
                  sx={{ cursor: 'pointer', objectFit: 'cover' }}
                  onClick={() => handleImageClick(illustration)}
                />
              ) : loadedPrompts[illustration.segment_index] ? (
                <Box
                  sx={{
                    height: 200,
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    bgcolor: 'grey.100',
                    p: 2,
                    cursor: 'pointer',
                    border: '1px solid',
                    borderColor: 'grey.300',
                    '&:hover': {
                      bgcolor: 'grey.200',
                    },
                  }}
                  onClick={() => handleImageClick(illustration)}
                >
                  <Typography variant="h3" color="primary" sx={{ mb: 1 }}>📝</Typography>
                  <Typography variant="body2" color="text.secondary">
                    프롬프트만 생성됨
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    (이미지 생성 실패)
                  </Typography>
                </Box>
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
                  {loadedImages[illustration.segment_index] ? (
                    <Chip label="이미지 생성 완료" color="success" size="small" />
                  ) : illustration.success ? (
                    <Chip label="프롬프트만 생성됨" color="warning" size="small" />
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
        ))}
      </Box>

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
              {loadedImages[selectedImage.segment_index] ? (
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
              ) : (
                <Box sx={{ p: 2 }}>
                  <Typography variant="h6" gutterBottom>
                    생성된 프롬프트
                  </Typography>
                  <Box
                    sx={{
                      p: 2,
                      bgcolor: 'grey.50',
                      borderRadius: 1,
                      border: '1px solid',
                      borderColor: 'grey.300',
                      mb: 2,
                    }}
                  >
                    <Typography
                      variant="body1"
                      sx={{
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word',
                      }}
                    >
                      {selectedImage.prompt}
                    </Typography>
                  </Box>
                  {loadedPrompts[selectedImage.segment_index] && (
                    <Box>
                      <Typography variant="subtitle2" gutterBottom>
                        프롬프트 세부 정보
                      </Typography>
                      <Box
                        sx={{
                          p: 2,
                          bgcolor: 'grey.100',
                          borderRadius: 1,
                          fontFamily: 'monospace',
                          fontSize: '0.85rem',
                          whiteSpace: 'pre-wrap',
                          overflowX: 'auto',
                        }}
                      >
                        {JSON.stringify(loadedPrompts[selectedImage.segment_index], null, 2)}
                      </Box>
                    </Box>
                  )}
                  <Alert severity="warning" sx={{ mt: 2 }}>
                    이미지 생성에 실패했습니다. 이 프롬프트를 다른 이미지 생성 서비스에서 사용할 수 있습니다.
                  </Alert>
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