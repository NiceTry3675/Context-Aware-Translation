"use client";

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth, useUser } from '@clerk/nextjs';
import {
  Container, Box, Typography, TextField, Button, Alert,
  CircularProgress, FormControl, InputLabel, Select, MenuItem,
  Card, CardContent, Breadcrumbs, Link, Checkbox, FormControlLabel,
  Grid, IconButton, Chip
} from '@mui/material';
import {
  Save as SaveIcon,
  Cancel as CancelIcon,
  CloudUpload as CloudUploadIcon,
  Delete as DeleteIcon,
  Image as ImageIcon
} from '@mui/icons-material';

interface PostCategory {
  id: number;
  name: string;
  display_name: string;
  description: string;
  is_admin_only: boolean;
}

interface PostFormData {
  title: string;
  content: string;
  category_id: number;
  is_pinned: boolean;
  is_private: boolean;
  images: string[];
}

export default function PostWritePage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { isLoaded, isSignedIn, getToken } = useAuth();
  const { user } = useUser();
  
  const categoryParam = searchParams.get('category');
  const editParam = searchParams.get('edit');
  const isEditMode = !!editParam;
  
  const [categories, setCategories] = useState<PostCategory[]>([]);
  const [formData, setFormData] = useState<PostFormData>({
    title: '',
    content: '',
    category_id: 0,
    is_pinned: false,
    is_private: false,
    images: []
  });
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadingImage, setUploadingImage] = useState(false);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  useEffect(() => {
    if (!isLoaded) return;

    if (!isSignedIn) {
      router.push('/');
      return;
    }

    fetchCategories();
    if (isEditMode) {
      fetchPost();
    }
  }, [isLoaded, isSignedIn]);

  const fetchCategories = async () => {
    try {
      const response = await fetch(`${API_URL}/api/v1/community/categories`);
      if (!response.ok) throw new Error('Failed to fetch categories');
      const data = await response.json();
      
      // Filter categories based on user role
      const filteredCategories = data.filter((cat: PostCategory) => {
        if (cat.is_admin_only) {
          return user?.publicMetadata?.role === 'admin';
        }
        return true;
      });
      
      setCategories(filteredCategories);
      
      // Set initial category if provided
      if (categoryParam && !isEditMode) {
        const category = filteredCategories.find((cat: PostCategory) => cat.name === categoryParam);
        if (category) {
          setFormData(prev => ({ ...prev, category_id: category.id }));
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error occurred');
    } finally {
      if (!isEditMode) {
        setLoading(false);
      }
    }
  };

  const fetchPost = async () => {
    try {
      const token = await getToken();
      const response = await fetch(`${API_URL}/api/v1/community/posts/${editParam}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (!response.ok) throw new Error('Failed to fetch post');
      const post = await response.json();
      
      console.log('Fetched post for editing:', post);
      console.log('Post images:', post.images);
      
      // Check if user can edit this post
      if (post.author.clerk_user_id !== user?.id && 
          user?.publicMetadata?.role !== 'admin') {
        throw new Error('수정 권한이 없습니다.');
      }
      
      const newFormData = {
        title: post.title,
        content: post.content,
        category_id: post.category.id,
        is_pinned: post.is_pinned,
        is_private: post.is_private || false,
        images: post.images || []
      };
      
      console.log('Setting form data:', newFormData);
      setFormData(newFormData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error occurred');
      router.push('/community');
    } finally {
      setLoading(false);
    }
  };

  const handleImageUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return;

    setUploadingImage(true);
    setError(null);

    try {
      const uploadedUrls: string[] = [];
      
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        
        // Validate file type
        if (!file.type.startsWith('image/')) {
          throw new Error(`${file.name}는 이미지 파일이 아닙니다.`);
        }
        
        // Validate file size (10MB)
        if (file.size > 10 * 1024 * 1024) {
          throw new Error(`${file.name}는 10MB보다 큽니다.`);
        }

        const formData = new FormData();
        formData.append('file', file);

        const token = await getToken();
        const response = await fetch(`${API_URL}/api/v1/community/upload-image`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`
          },
          body: formData
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || '이미지 업로드에 실패했습니다.');
        }

        const result = await response.json();
        uploadedUrls.push(result.url);
      }

      // Add uploaded images to formData
      setFormData(prev => ({
        ...prev,
        images: [...prev.images, ...uploadedUrls]
      }));
      
    } catch (err) {
      setError(err instanceof Error ? err.message : '이미지 업로드 중 오류가 발생했습니다.');
    } finally {
      setUploadingImage(false);
    }
  };

  const handleRemoveImage = (indexToRemove: number) => {
    setFormData(prev => ({
      ...prev,
      images: prev.images.filter((_, index) => index !== indexToRemove)
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!formData.title.trim() || !formData.content.trim() || !formData.category_id) {
      setError('모든 필드를 입력해주세요.');
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const token = await getToken();
      const url = isEditMode 
        ? `${API_URL}/api/v1/community/posts/${editParam}`
        : `${API_URL}/api/v1/community/posts`;
      
      const method = isEditMode ? 'PUT' : 'POST';
      
      const response = await fetch(url, {
        method,
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to save post');
      }

      const savedPost = await response.json();
      const category = categories.find(cat => cat.id === savedPost.category.id);
      
      router.push(`/community/${category?.name}/${savedPost.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : '저장에 실패했습니다.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleCancel = () => {
    if (categoryParam) {
      router.push(`/community/${categoryParam}`);
    } else {
      router.push('/community');
    }
  };

  if (!isLoaded || loading) {
    return (
      <Container maxWidth="lg" sx={{ py: 8 }}>
        <Box display="flex" justifyContent="center">
          <CircularProgress />
        </Box>
      </Container>
    );
  }

  if (!isSignedIn) {
    return null;
  }

  return (
    <Container maxWidth="lg" sx={{ py: 8 }}>
      {/* Breadcrumb Navigation */}
      <Breadcrumbs sx={{ mb: 4 }}>
        <Link
          component="button"
          variant="body1"
          onClick={() => router.push('/')}
          sx={{ cursor: 'pointer' }}
        >
          홈
        </Link>
        <Link
          component="button"
          variant="body1"
          onClick={() => router.push('/community')}
          sx={{ cursor: 'pointer' }}
        >
          커뮤니티
        </Link>
        <Typography color="text.primary">
          {isEditMode ? '글 수정' : '글쓰기'}
        </Typography>
      </Breadcrumbs>

      {/* Header */}
      <Typography variant="h3" component="h1" gutterBottom>
        {isEditMode ? '글 수정' : '새 글 작성'}
      </Typography>

      {error && <Alert severity="error" sx={{ mb: 4 }}>{error}</Alert>}

      {/* Form */}
      <Card>
        <CardContent sx={{ p: 4 }}>
          <Box component="form" onSubmit={handleSubmit}>
            <FormControl fullWidth sx={{ mb: 3 }}>
              <InputLabel>카테고리</InputLabel>
              <Select
                value={formData.category_id || ''}
                onChange={(e) => setFormData(prev => ({ ...prev, category_id: Number(e.target.value) }))}
                label="카테고리"
                disabled={isEditMode}
              >
                {categories.map((category) => (
                  <MenuItem key={category.id} value={category.id}>
                    {category.display_name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <TextField
              fullWidth
              label="제목"
              value={formData.title}
              onChange={(e) => setFormData(prev => ({ ...prev, title: e.target.value }))}
              sx={{ mb: 3 }}
              required
            />

            <TextField
              fullWidth
              label="내용"
              value={formData.content}
              onChange={(e) => setFormData(prev => ({ ...prev, content: e.target.value }))}
              multiline
              rows={15}
              sx={{ mb: 3 }}
              required
            />

            {/* Image Upload Section */}
            <Box sx={{ mb: 3 }}>
              <Typography variant="h6" gutterBottom>
                <ImageIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
                이미지 첨부
              </Typography>
              
              <input
                type="file"
                accept="image/*"
                multiple
                onChange={(e) => handleImageUpload(e.target.files)}
                style={{ display: 'none' }}
                id="image-upload-input"
                disabled={uploadingImage}
              />
              
              <label htmlFor="image-upload-input">
                <Button
                  variant="outlined"
                  component="span"
                  startIcon={uploadingImage ? <CircularProgress size={20} /> : <CloudUploadIcon />}
                  disabled={uploadingImage}
                  sx={{ mb: 2 }}
                >
                  {uploadingImage ? '업로드 중...' : '이미지 선택'}
                </Button>
              </label>

              <Typography variant="caption" display="block" color="text.secondary" sx={{ mb: 2 }}>
                최대 10MB, JPG/PNG/GIF/WebP 형식, 여러 파일 선택 가능
              </Typography>

              {/* Uploaded Images Preview */}
              {(() => {
                console.log('Render check - formData.images:', formData.images, 'Length:', formData.images.length);
                return formData.images.length > 0;
              })() && (
                <Box>
                  <Typography variant="subtitle2" gutterBottom>
                    첨부된 이미지 ({formData.images.length}개)
                  </Typography>
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
                    {formData.images.map((imageUrl, index) => (
                      <Box key={index} sx={{ width: { xs: '100%', sm: 'calc(50% - 8px)', md: 'calc(33.333% - 10.67px)' } }}>
                        <Box 
                          sx={{ 
                            position: 'relative', 
                            border: 1, 
                            borderColor: 'divider', 
                            borderRadius: 1,
                            overflow: 'hidden'
                          }}
                        >
                          <Box
                            component="img"
                            src={`${API_URL}${imageUrl}`}
                            alt={`첨부 이미지 ${index + 1}`}
                            sx={{
                              width: '100%',
                              height: 120,
                              objectFit: 'cover'
                            }}
                          />
                          <IconButton
                            size="small"
                            onClick={() => handleRemoveImage(index)}
                            sx={{
                              position: 'absolute',
                              top: 4,
                              right: 4,
                              bgcolor: 'rgba(0, 0, 0, 0.7)',
                              color: 'white',
                              border: '2px solid rgba(255, 255, 255, 0.8)',
                              boxShadow: '0 2px 8px rgba(0, 0, 0, 0.3)',
                              '&:hover': {
                                bgcolor: 'rgba(255, 0, 0, 0.8)',
                                borderColor: 'white',
                                transform: 'scale(1.1)'
                              },
                              transition: 'all 0.2s ease'
                            }}
                          >
                            <DeleteIcon fontSize="small" />
                          </IconButton>
                        </Box>
                      </Box>
                    ))}
                  </Box>
                </Box>
              )}
            </Box>

            {user?.publicMetadata?.role === 'admin' && (
              <FormControl sx={{ mb: 3 }}>
                <Box display="flex" alignItems="center" gap={1}>
                  <input
                    type="checkbox"
                    id="is_pinned"
                    checked={formData.is_pinned}
                    onChange={(e) => setFormData(prev => ({ ...prev, is_pinned: e.target.checked }))}
                  />
                  <label htmlFor="is_pinned">
                    상단 고정 (공지사항으로 표시)
                  </label>
                </Box>
              </FormControl>
            )}

            {/* 비밀글 체크박스 - 모든 사용자가 사용 가능 */}
            <FormControl sx={{ mb: 3 }}>
              <Box display="flex" alignItems="center" gap={1}>
                <input
                  type="checkbox"
                  id="is_private"
                  checked={formData.is_private}
                  onChange={(e) => setFormData(prev => ({ ...prev, is_private: e.target.checked }))}
                />
                <label htmlFor="is_private">
                  🔒 비밀글 (작성자와 관리자만 볼 수 있습니다)
                </label>
              </Box>
            </FormControl>

            <Box display="flex" justifyContent="flex-end" gap={2}>
              <Button
                variant="outlined"
                startIcon={<CancelIcon />}
                onClick={handleCancel}
                disabled={submitting}
              >
                취소
              </Button>
              <Button
                type="submit"
                variant="contained"
                startIcon={<SaveIcon />}
                disabled={submitting || !formData.title.trim() || !formData.content.trim() || !formData.category_id}
              >
                {submitting ? '저장 중...' : (isEditMode ? '수정하기' : '작성하기')}
              </Button>
            </Box>
          </Box>
        </CardContent>
      </Card>
    </Container>
  );
} 