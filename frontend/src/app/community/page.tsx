"use client";

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@clerk/nextjs';
import {
  Container, Box, Typography, Card, CardContent,
  Button, Alert, CircularProgress, Chip, Divider, List, ListItem, ListItemText
} from '@mui/material';
import {
  Announcement as AnnouncementIcon,
  Lightbulb as LightbulbIcon,
  QuestionAnswer as QuestionAnswerIcon,
  Forum as ForumIcon,
  ArrowForward as ArrowForwardIcon,
  Lock as LockIcon,
  PushPin as PushPinIcon
} from '@mui/icons-material';
import theme from '../../theme';

interface Author {
  id: number;
  clerk_user_id: string;
  name: string;
  role: string;
  email: string;
}

interface PostCategory {
  id: number;
  name: string;
  display_name: string;
  description: string;
  is_admin_only: boolean;
  order: number;
  created_at: string;
}

interface PostPreview {
  id: number;
  title: string;
  author: Author;
  category: PostCategory;
  is_pinned: boolean;
  is_private: boolean;
  view_count: number;
  comment_count: number;
  created_at: string;
}

interface CategoryOverview {
  id: number;
  name: string;
  display_name: string;
  description: string;
  is_admin_only: boolean;
  order: number;
  created_at: string;
  recent_posts: PostPreview[];
  total_posts: number;
}

const categoryIcons: { [key: string]: React.ReactNode } = {
  notice: <AnnouncementIcon sx={{ fontSize: 40 }} />,
  suggestion: <LightbulbIcon sx={{ fontSize: 40 }} />,
  qna: <QuestionAnswerIcon sx={{ fontSize: 40 }} />,
  free: <ForumIcon sx={{ fontSize: 40 }} />
};

const categoryColors: { [key: string]: string } = {
  notice: theme.palette.error.main,
  suggestion: theme.palette.success.main,
  qna: theme.palette.info.main,
  free: theme.palette.primary.main
};

export default function CommunityPage() {
  const router = useRouter();
  const { isLoaded, isSignedIn, getToken } = useAuth();
  const [categories, setCategories] = useState<CategoryOverview[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  useEffect(() => {
    if (!isLoaded) return;

    if (!isSignedIn) {
      router.push('/');
      return;
    }

    fetchCategoriesOverview();
  }, [isLoaded, isSignedIn]);

  const fetchCategoriesOverview = async () => {
    try {
      console.log('Fetching categories overview from:', `${API_URL}/api/v1/community/categories/overview`);
      const token = await getToken();
      const response = await fetch(`${API_URL}/api/v1/community/categories/overview`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('Response not OK:', response.status, errorText);
        throw new Error(`Failed to fetch categories: ${response.status} ${errorText}`);
      }
      
      const data = await response.json();
      console.log('Categories fetched:', data);
      setCategories(data);
      
      if (data.length === 0) {
        setError('카테고리가 아직 생성되지 않았습니다. 관리자에게 문의해주세요.');
      }
    } catch (err) {
      console.error('Error fetching categories:', err);
      setError(err instanceof Error ? err.message : 'Unknown error occurred');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    
    if (diffHours < 1) {
      const diffMinutes = Math.floor(diffMs / (1000 * 60));
      return `${diffMinutes}분 전`;
    } else if (diffHours < 24) {
      return `${diffHours}시간 전`;
    } else {
      return date.toLocaleDateString('ko-KR', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
      });
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
      {/* Header */}
      <Box textAlign="center" mb={6}>
        <Typography variant="h1" component="h1" sx={{
          background: `linear-gradient(45deg, ${theme.palette.primary.main} 30%, ${theme.palette.secondary.main} 90%)`,
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          mb: 2
        }}>
          커뮤니티
        </Typography>
        <Typography variant="h5" color="text.secondary">
          냥번역 사용자들과 소통하고 정보를 공유하세요
        </Typography>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 4 }}>{error}</Alert>}

      {/* Category Cards with Recent Posts */}
      {categories.length === 0 ? (
        <Card sx={{ p: 4, textAlign: 'center' }}>
          <Typography variant="h6" gutterBottom>
            아직 카테고리가 생성되지 않았습니다.
          </Typography>
          <Typography color="text.secondary" mb={2}>
            관리자가 카테고리를 초기화하면 게시판을 사용할 수 있습니다.
          </Typography>
          <Typography variant="body2" color="text.secondary">
            카테고리를 초기화하려면 서버에서 다음 명령을 실행하세요:
          </Typography>
          <Typography 
            variant="body2" 
            sx={{ 
              mt: 1, 
              p: 1, 
              bgcolor: 'background.paper',
              fontFamily: 'monospace',
              borderRadius: 1
            }}
          >
            python init_categories.py
          </Typography>
        </Card>
      ) : (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          {categories.map((category) => {
            const icon = categoryIcons[category.name] || <ForumIcon sx={{ fontSize: 40 }} />;
            const color = categoryColors[category.name] || theme.palette.primary.main;

            return (
              <Card key={category.id} sx={{
                transition: 'all 0.3s ease',
                '&:hover': {
                  boxShadow: `0 8px 24px ${color}40`,
                }
              }}>
                <CardContent sx={{ p: 4 }}>
                  {/* Category Header */}
                  <Box display="flex" alignItems="center" justifyContent="space-between" mb={3}>
                    <Box display="flex" alignItems="center" gap={2}>
                      <Box
                        sx={{
                          width: 60,
                          height: 60,
                          borderRadius: '12px',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          backgroundColor: `${color}20`,
                          color: color,
                        }}
                      >
                        {icon}
                      </Box>
                      <Box>
                        <Typography variant="h5" component="h2">
                          {category.display_name}
                        </Typography>
                        <Typography color="text.secondary">
                          {category.description}
                        </Typography>
                        <Box display="flex" alignItems="center" gap={1} mt={1}>
                          <Chip 
                            label={`${category.total_posts}개 게시글`} 
                            size="small" 
                            variant="outlined"
                          />
                          {category.is_admin_only && (
                            <Chip
                              label="관리자 전용"
                              color="error"
                              size="small"
                            />
                          )}
                        </Box>
                      </Box>
                    </Box>
                    
                    <Button
                      variant="contained"
                      endIcon={<ArrowForwardIcon />}
                      onClick={() => router.push(`/community/${category.name}`)}
                      sx={{
                        backgroundColor: color,
                        '&:hover': {
                          backgroundColor: color,
                          filter: 'brightness(0.9)',
                        }
                      }}
                    >
                      전체보기
                    </Button>
                  </Box>

                  <Divider sx={{ mb: 2 }} />

                  {/* Recent Posts */}
                  {category.recent_posts.length > 0 ? (
                    <Box>
                      <Typography variant="h6" mb={2} color="text.secondary">
                        최근 게시글
                      </Typography>
                      <List sx={{ py: 0 }}>
                        {category.recent_posts.map((post) => (
                          <ListItem 
                            key={post.id} 
                            sx={{ 
                              px: 0, 
                              cursor: 'pointer',
                              '&:hover': {
                                backgroundColor: 'action.hover',
                                borderRadius: 1
                              }
                            }}
                            onClick={() => router.push(`/community/${category.name}/${post.id}`)}
                          >
                            <ListItemText
                              primary={
                                <Box display="flex" alignItems="center" gap={1}>
                                  {post.is_pinned && <PushPinIcon fontSize="small" color="error" />}
                                  {post.is_private && <LockIcon fontSize="small" color="disabled" />}
                                  <Typography 
                                    variant="body1"
                                    sx={{
                                      color: post.is_private ? 'text.secondary' : 'text.primary',
                                      fontWeight: post.is_pinned ? 'bold' : 'normal'
                                    }}
                                  >
                                    {post.title}
                                  </Typography>
                                </Box>
                              }
                              secondary={
                                <span style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '2px' }}>
                                  <Typography variant="caption" color="text.secondary">
                                    {post.author.name || '사용자'}
                                  </Typography>
                                  <Typography variant="caption" color="text.secondary">
                                    조회 {post.view_count}
                                  </Typography>
                                  <Typography variant="caption" color="text.secondary">
                                    댓글 {post.comment_count}
                                  </Typography>
                                  <Typography variant="caption" color="text.secondary">
                                    {formatDate(post.created_at)}
                                  </Typography>
                                </span>
                              }
                            />
                          </ListItem>
                        ))}
                      </List>
                    </Box>
                  ) : (
                    <Box textAlign="center" py={4}>
                      <Typography color="text.secondary">
                        아직 게시글이 없습니다.
                      </Typography>
                    </Box>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </Box>
      )}
    </Container>
  );
} 