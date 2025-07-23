"use client";

import { useEffect, useState, Suspense, useCallback } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { useAuth, useUser } from '@clerk/nextjs';
import UserDisplayName from '../../../components/UserDisplayName';
import {
  Container, Box, Typography, Card, CardContent, Button, Alert,
  CircularProgress, IconButton, TextField, Divider,
  Breadcrumbs, Link, Avatar, Paper
} from '@mui/material';
import {
  ArrowBack as ArrowBackIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Person as PersonIcon,
  CalendarToday as CalendarTodayIcon,
  Visibility as VisibilityIcon,
  Comment as CommentIcon,
  Send as SendIcon
} from '@mui/icons-material';

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
}

interface Post {
  id: number;
  title: string;
  content: string;
  author: Author;
  category: PostCategory;
  is_pinned: boolean;
  is_private: boolean;
  view_count: number;
  images: string[];
  created_at: string;
  updated_at: string | null;
}

interface Comment {
  id: number;
  content: string;
  author: Author;
  post_id: number;
  parent_id: number | null;
  is_private: boolean;
  created_at: string;
  updated_at: string | null;
  replies: Comment[];
}

function PostDetailPageContent() {
  const router = useRouter();
  const params = useParams();
  const categoryName = params.category as string;
  const postId = params.postId as string;
  const { isLoaded, isSignedIn, getToken } = useAuth();
  const { user } = useUser();
  
  const [post, setPost] = useState<Post | null>(null);
  const [comments, setComments] = useState<Comment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [commentContent, setCommentContent] = useState('');
  const [commentIsPrivate, setCommentIsPrivate] = useState(false);
  const [submittingComment, setSubmittingComment] = useState(false);
  
  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const [editingCommentId, setEditingCommentId] = useState<number | null>(null);
  const [editingCommentContent, setEditingCommentContent] = useState('');

  const fetchPost = useCallback(async () => {
    try {
      const token = await getToken();
      const response = await fetch(`${API_URL}/api/v1/community/posts/${postId}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (response.status === 403) {
        setError('🔒 이 게시글은 비밀글입니다. 작성자와 관리자만 볼 수 있습니다.');
        return;
      }
      
      if (!response.ok) throw new Error('Failed to fetch post');
      const data = await response.json();
      setPost(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error occurred');
    } finally {
      setLoading(false);
    }
  }, [getToken, postId, API_URL]);

  const fetchComments = useCallback(async () => {
    try {
      const token = await getToken();
      const response = await fetch(`${API_URL}/api/v1/community/posts/${postId}/comments`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (!response.ok) throw new Error('Failed to fetch comments');
      const data = await response.json();
      setComments(data);
    } catch (err) {
      console.error('Failed to fetch comments:', err);
    }
  }, [getToken, postId, API_URL]);

  const incrementViewCount = useCallback(async () => {
    try {
      const token = await getToken();
      await fetch(`${API_URL}/api/v1/community/posts/${postId}/view`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      // No need to refetch here, view count is not critical to be real-time
    } catch (err) {
      console.warn('Failed to increment view count:', err);
    }
  }, [getToken, postId, API_URL]);

  useEffect(() => {
    if (!isLoaded) return;

    if (!isSignedIn) {
      router.push('/');
      return;
    }

    fetchPost();
    fetchComments();
    incrementViewCount();
  }, [isLoaded, isSignedIn, router, fetchPost, fetchComments, incrementViewCount]);

  const handleDeletePost = async () => {
    if (!confirm('정말로 이 게시글을 삭제하시겠습니까?')) return;

    try {
      const token = await getToken();
      const response = await fetch(`${API_URL}/api/v1/community/posts/${postId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) throw new Error('Failed to delete post');
      
      router.push(`/community/${categoryName}`);
    } catch (err) {
      alert(err instanceof Error ? err.message : '삭제에 실패했습니다.');
    }
  };

  const handleSubmitComment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!commentContent.trim()) return;

    setSubmittingComment(true);
    try {
      const token = await getToken();
      const response = await fetch(`${API_URL}/api/v1/community/posts/${postId}/comments`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          content: commentContent,
          post_id: parseInt(postId),
          is_private: commentIsPrivate
        })
      });

      if (!response.ok) throw new Error('Failed to submit comment');
      
      setCommentContent('');
      setCommentIsPrivate(false);
      fetchComments();
    } catch (err) {
      alert(err instanceof Error ? err.message : '댓글 작성에 실패했습니다.');
    } finally {
      setSubmittingComment(false);
    }
  };

  const handleUpdateComment = async (commentId: number) => {
    if (!editingCommentContent.trim()) return;

    try {
      const token = await getToken();
      const response = await fetch(`${API_URL}/api/v1/community/comments/${commentId}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          content: editingCommentContent
        })
      });

      if (!response.ok) throw new Error('Failed to update comment');
      
      setEditingCommentId(null);
      setEditingCommentContent('');
      fetchComments();
    } catch (err) {
      alert(err instanceof Error ? err.message : '댓글 수정에 실패했습니다.');
    }
  };

  const handleDeleteComment = async (commentId: number) => {
    if (!confirm('정말로 이 댓글을 삭제하시겠습니까?')) return;

    try {
      const token = await getToken();
      const response = await fetch(`${API_URL}/api/v1/community/comments/${commentId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) throw new Error('Failed to delete comment');
      
      fetchComments();
    } catch (err) {
      alert(err instanceof Error ? err.message : '댓글 삭제에 실패했습니다.');
    }
  };

  const canModifyPost = () => {
    if (!post || !user) return false;
    
    // Clerk user ID 기반으로 권한 확인
    return post.author.clerk_user_id === user.id || 
           user.publicMetadata?.role === 'admin';
  };

  const canModifyComment = (comment: Comment) => {
    if (!user) return false;
    
    // Clerk user ID 기반으로 권한 확인
    return comment.author.clerk_user_id === user.id || 
           user.publicMetadata?.role === 'admin';
  };

  const formatDate = (dateString: string) => {
    // 백엔드에서 이미 한국 시간으로 변환된 시간을 받으므로 단순하게 처리
    return new Date(dateString).toLocaleString('ko-KR', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
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

  if (!isSignedIn || !post) {
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
        <Link
          component="button"
          variant="body1"
          onClick={() => router.push(`/community/${categoryName}`)}
          sx={{ cursor: 'pointer' }}
        >
          {post.category.display_name}
        </Link>
        <Typography color="text.primary">{post.title}</Typography>
      </Breadcrumbs>

      {error && <Alert severity="error" sx={{ mb: 4 }}>{error}</Alert>}

      {/* Post Content */}
      <Card sx={{ mb: 4 }}>
        <CardContent sx={{ p: 4 }}>
          {/* Post Header */}
          <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={3}>
            <Box flex={1}>
              <Box display="flex" alignItems="center" gap={1} mb={2}>
                {post.is_private && (
                  <span title="비밀글" style={{ fontSize: '1.5rem' }}>🔒</span>
                )}
                <Typography 
                  variant="h3" 
                  component="h1" 
                  sx={{ 
                    color: post.is_private ? 'text.secondary' : 'text.primary',
                    fontStyle: post.is_private ? 'italic' : 'normal'
                  }}
                >
                  {post.title}
                </Typography>
              </Box>
              <Box display="flex" alignItems="center" gap={2} flexWrap="wrap">
                <Box display="flex" alignItems="center" gap={0.5}>
                  <PersonIcon fontSize="small" color="action" />
                  <Typography variant="body2">
                    <UserDisplayName author={post.author} showRole />
                  </Typography>
                </Box>
                <Box display="flex" alignItems="center" gap={0.5}>
                  <CalendarTodayIcon fontSize="small" color="action" />
                  <Typography variant="body2">
                    {formatDate(post.created_at)}
                  </Typography>
                </Box>
                <Box display="flex" alignItems="center" gap={0.5}>
                  <VisibilityIcon fontSize="small" color="action" />
                  <Typography variant="body2">
                    조회 {post.view_count}
                  </Typography>
                </Box>
              </Box>
            </Box>
            
            <Box display="flex" gap={1}>
              <IconButton onClick={() => router.push(`/community/${categoryName}`)}>
                <ArrowBackIcon />
              </IconButton>
              {canModifyPost() && (
                <>
                  <IconButton onClick={() => router.push(`/community/write?edit=${postId}`)}>
                    <EditIcon />
                  </IconButton>
                  <IconButton onClick={handleDeletePost} color="error">
                    <DeleteIcon />
                  </IconButton>
                </>
              )}
            </Box>
          </Box>

          <Divider sx={{ mb: 3 }} />

          {/* Post Body */}
          <Typography 
            variant="body1" 
            sx={{ 
              whiteSpace: 'pre-wrap',
              minHeight: '200px',
              lineHeight: 1.8,
              mb: post.images?.length > 0 ? 3 : 0
            }}
          >
            {post.content}
          </Typography>

          {/* Image Gallery */}
          {post.images && post.images.length > 0 && (
            <Box sx={{ mb: 2 }}>
              <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <VisibilityIcon />
                첨부된 이미지 ({post.images.length}개)
              </Typography>
              <Box sx={{ 
                display: 'grid',
                gridTemplateColumns: {
                  xs: '1fr',
                  sm: 'repeat(auto-fit, minmax(300px, 1fr))',
                  md: 'repeat(auto-fit, minmax(350px, 1fr))'
                },
                gap: 2
              }}>
                {post.images.map((imageUrl, index) => (
                  <Card key={index} sx={{ overflow: 'hidden' }}>
                    <Box
                      component="img"
                      src={`${API_URL}${imageUrl}`}
                      alt={`첨부 이미지 ${index + 1}`}
                      sx={{
                        width: '100%',
                        height: 'auto',
                        maxHeight: 400,
                        objectFit: 'contain',
                        cursor: 'pointer',
                        transition: 'transform 0.2s',
                        '&:hover': {
                          transform: 'scale(1.02)'
                        }
                      }}
                      onClick={() => {
                        // Open image in new window for full size viewing
                        window.open(`${API_URL}${imageUrl}`, '_blank');
                      }}
                    />
                  </Card>
                ))}
              </Box>
            </Box>
          )}
        </CardContent>
      </Card>

      {/* Comments Section */}
      <Card>
        <CardContent sx={{ p: 4 }}>
          <Box display="flex" alignItems="center" gap={1} mb={3}>
            <CommentIcon />
            <Typography variant="h5" component="h2">
              댓글 {comments.length}개
            </Typography>
          </Box>

          {/* Comment Form */}
          <Box component="form" onSubmit={handleSubmitComment} mb={4}>
            <TextField
              fullWidth
              multiline
              rows={3}
              value={commentContent}
              onChange={(e) => setCommentContent(e.target.value)}
              placeholder="댓글을 작성해주세요..."
              variant="outlined"
              disabled={submittingComment}
            />
            {/* 비밀댓글 체크박스 */}
            <Box display="flex" alignItems="center" gap={1} mt={1}>
              <input
                type="checkbox"
                id="comment_is_private"
                checked={commentIsPrivate}
                onChange={(e) => setCommentIsPrivate(e.target.checked)}
                disabled={submittingComment}
              />
              <label htmlFor="comment_is_private">
                🔒 비밀댓글 (작성자와 관리자만 볼 수 있습니다)
              </label>
            </Box>
            <Box display="flex" justifyContent="flex-end" mt={2}>
              <Button
                type="submit"
                variant="contained"
                startIcon={<SendIcon />}
                disabled={!commentContent.trim() || submittingComment}
              >
                댓글 작성
              </Button>
            </Box>
          </Box>

          {/* Comments List */}
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {comments.map((comment) => (
              <Paper key={comment.id} sx={{ p: 3 }} variant="outlined">
                <Box display="flex" justifyContent="space-between" alignItems="flex-start">
                  <Box flex={1}>
                    <Box display="flex" alignItems="center" gap={1} mb={1}>
                      <Avatar sx={{ width: 32, height: 32 }}>
                        {(comment.author.name || comment.author.email || '사용자')?.[0] || '?'}
                      </Avatar>
                      {comment.is_private && (
                        <span title="비밀댓글">🔒</span>
                      )}
                      <Typography 
                        variant="subtitle2"
                        sx={{ 
                          color: comment.is_private ? 'text.secondary' : 'text.primary',
                          fontStyle: comment.is_private ? 'italic' : 'normal'
                        }}
                      >
                        <UserDisplayName author={comment.author} showRole />
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {formatDate(comment.created_at)}
                      </Typography>
                    </Box>
                    
                    {editingCommentId === comment.id ? (
                      <Box>
                        <TextField
                          fullWidth
                          multiline
                          rows={2}
                          value={editingCommentContent}
                          onChange={(e) => setEditingCommentContent(e.target.value)}
                          sx={{ mb: 1 }}
                        />
                        <Box display="flex" gap={1}>
                          <Button
                            size="small"
                            variant="contained"
                            onClick={() => handleUpdateComment(comment.id)}
                          >
                            저장
                          </Button>
                          <Button
                            size="small"
                            onClick={() => {
                              setEditingCommentId(null);
                              setEditingCommentContent('');
                            }}
                          >
                            취소
                          </Button>
                        </Box>
                      </Box>
                    ) : (
                      <Typography 
                        variant="body2" 
                        sx={{ 
                          whiteSpace: 'pre-wrap',
                          color: comment.is_private ? 'text.secondary' : 'text.primary',
                          fontStyle: comment.is_private ? 'italic' : 'normal'
                        }}
                      >
                        {comment.content}
                      </Typography>
                    )}
                  </Box>
                  
                  {canModifyComment(comment) && editingCommentId !== comment.id && (
                    <Box>
                      <IconButton
                        size="small"
                        onClick={() => {
                          setEditingCommentId(comment.id);
                          setEditingCommentContent(comment.content);
                        }}
                      >
                        <EditIcon fontSize="small" />
                      </IconButton>
                      <IconButton
                        size="small"
                        color="error"
                        onClick={() => handleDeleteComment(comment.id)}
                      >
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </Box>
                  )}
                </Box>
              </Paper>
            ))}
          </Box>
        </CardContent>
      </Card>
    </Container>
  );
}

export default function PostDetailPage() {
  return (
    <Suspense fallback={
      <Container maxWidth="md" sx={{ py: 4 }}>
        <Box display="flex" justifyContent="center" alignItems="center" minHeight="50vh">
          <CircularProgress />
        </Box>
      </Container>
    }>
      <PostDetailPageContent />
    </Suspense>
  );
} 