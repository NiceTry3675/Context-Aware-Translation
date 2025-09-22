"use client";

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@clerk/nextjs';
import { endpoints } from '@/lib/api';
import UserDisplayName from '../components/UserDisplayName';
import {
  Container, Box, Typography, Card, CardContent,
  Button, Alert, CircularProgress, Chip, Divider, List, ListItem, ListItemText, IconButton
} from '@mui/material';
import {
  Announcement as AnnouncementIcon,
  Lightbulb as LightbulbIcon,
  QuestionAnswer as QuestionAnswerIcon,
  Forum as ForumIcon,
  ArrowForward as ArrowForwardIcon,
  Lock as LockIcon,
  PushPin as PushPinIcon,
  Home as HomeIcon
} from '@mui/icons-material';
import theme from '../../theme';
import type { CategoryOverview } from '@/lib/api';

const categoryIcons: { [key: string]: React.ReactNode } = {
  notice: <AnnouncementIcon sx={{ fontSize: 40 }} />,
  announcement: <AnnouncementIcon sx={{ fontSize: 40 }} />,
  suggestion: <LightbulbIcon sx={{ fontSize: 40 }} />,
  qna: <QuestionAnswerIcon sx={{ fontSize: 40 }} />,
  free: <ForumIcon sx={{ fontSize: 40 }} />
};

const categoryColors: { [key: string]: string } = {
  notice: theme.palette.error.main,
  announcement: theme.palette.error.main,
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

  useEffect(() => {
    if (!isLoaded) return;

    fetchCategoriesOverview();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoaded, isSignedIn]);

  const fetchCategoriesOverview = async () => {
    try {
      const token = await getToken();
      const { data, error } = await endpoints.getCategoriesOverview(token || undefined);

      if (error) {
        throw new Error('Failed to fetch categories');
      }

      console.log('Categories fetched:', categories);
      setCategories(categories);

      if (categories.length === 0) {
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
      <Box sx={{ mb: 4 }}>
        <IconButton onClick={() => router.push('/')} color="primary">
          <HomeIcon />
          <Typography variant="button" sx={{ ml: 1 }}>홈으로</Typography>
        </IconButton>
      </Box>

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
                  {(category.recent_posts?.length ?? 0) > 0 ? (
                    <Box>
                      <Typography variant="h6" mb={2} color="text.secondary">
                        최근 게시글
                      </Typography>
                      <List sx={{ py: 0 }}>
                        {(category.recent_posts || []).map((post) => (
                          <ListItem 
                            key={post.id} 
                            sx={{ 
                              px: 0, 
                              cursor: post.is_private ? 'not-allowed' : 'pointer',
                              '&:hover': {
                                backgroundColor: post.is_private ? 'transparent' : 'action.hover',
                                borderRadius: 1
                              }
                            }}
                            onClick={() => {
                              if (!post.is_private) {
                                router.push(`/community/${category.name}/${post.id}`)
                              }
                            }}
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
                                    <UserDisplayName author={post.author} variant="short" />
                                  </Typography>
                                  <Typography variant="caption" color="text.secondary">
                                    조회 {post.view_count}
                                  </Typography>
                                  <Typography variant="caption" color="text.secondary">
                                    댓글 {post.comment_count ?? 0}
                                  </Typography>
                                  <Typography variant="caption" color="text.secondary">
                                    {formatDate(post.created_at)}
                                  </Typography>
                                </span>
                              }
                              secondaryTypographyProps={{
                                component: 'div'
                              }}
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
