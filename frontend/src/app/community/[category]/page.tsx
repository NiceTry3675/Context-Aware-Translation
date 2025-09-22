"use client";

import { useEffect, useState, Suspense } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { useAuth, useUser } from '@clerk/nextjs';
import { buildAuthHeader } from '../../utils/authToken';
import UserDisplayName from '../../components/UserDisplayName';
import {
  Container, Box, Typography, Button, Alert,
  CircularProgress, Chip, IconButton, TextField, InputAdornment,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Paper, TablePagination, Breadcrumbs, Link
} from '@mui/material';
import {
  Add as AddIcon,
  Search as SearchIcon,
  PushPin as PushPinIcon,
  Person as PersonIcon,
  Comment as CommentIcon,
  Visibility as VisibilityIcon,
  CalendarToday as CalendarTodayIcon,
  ArrowBack as ArrowBackIcon
} from '@mui/icons-material';
import theme from '../../../theme';
import type { components } from '@/types/api';

// Type aliases for convenience
type PostCategory = components['schemas']['PostCategory'];
type Post = components['schemas']['Post'];
type User = components['schemas']['User'];

function CategoryPostsPageContent() {
  const router = useRouter();
  const params = useParams();
  const categoryName = params.category as string;
  const { isLoaded, isSignedIn, getToken } = useAuth();
  const { user } = useUser();
  
  const [posts, setPosts] = useState<Post[]>([]);
  const [category, setCategory] = useState<PostCategory | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(20);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  useEffect(() => {
    if (!isLoaded) return;

    // 먼저 카테고리 정보를 가져온 다음 게시글을 가져옴
    fetchCategoryInfo();
    fetchPosts();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoaded, isSignedIn, categoryName, page, rowsPerPage]);

  const fetchCategoryInfo = async () => {
    try {
      const response = await fetch(`${API_URL}/api/v1/community/categories`);
      if (!response.ok) throw new Error('Failed to fetch categories');
      const categories = await response.json();
      const currentCategory = categories.find((cat: PostCategory) => cat.name === categoryName);
      if (currentCategory) {
        console.log('Category found:', currentCategory);
        setCategory(currentCategory);
      }
    } catch (err) {
      console.error('Failed to fetch category info:', err);
    }
  };

  const fetchPosts = async () => {
    try {
      console.log('Fetching posts for category:', categoryName);
      const response = await fetch(
        `${API_URL}/api/v1/community/posts?category=${categoryName}&skip=${page * rowsPerPage}&limit=${rowsPerPage}${searchTerm ? `&search=${searchTerm}` : ''}`,
        {
          headers: await buildAuthHeader(getToken)
        }
      );
      if (!response.ok) throw new Error('Failed to fetch posts');
      const data = await response.json();
      console.log('Posts fetched:', data);
      
      if (data.length > 0 && data[0].category) {
        console.log('Setting category from posts:', data[0].category);
        setCategory(data[0].category);
      } else {
        // 게시글이 없어도 카테고리 정보를 가져와야 함
        console.log('No posts found, fetching category info separately');
        await fetchCategoryInfo();
      }
      
      setPosts(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error occurred');
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(0);
    fetchPosts();
  };

  const handleChangePage = (_: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const canCreatePost = () => {
    console.log('Checking canCreatePost:', { category, user: user?.publicMetadata });
    
    if (!category) {
      console.log('No category loaded yet');
      return false;
    }
    
    if (category.is_admin_only) {
      // Admin role check - check both publicMetadata and unsafeMetadata
      const isAdmin = user?.publicMetadata?.role === 'admin' || 
                     user?.unsafeMetadata?.role === 'admin';
      console.log('Admin-only category, user is admin:', isAdmin);
      return isAdmin;
    }
    
    console.log('Regular category, allowing post creation');
    return true;
  };

  const formatDate = (dateString: string) => {
    // 백엔드에서 이미 한국 시간으로 변환된 시간을 받음
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    
    if (diffHours < 1) {
      const diffMinutes = Math.floor(diffMs / (1000 * 60));
      return `${diffMinutes}분 전`;
    } else if (diffHours < 24) {
      return `${diffHours}시간 전`;
    } else if (diffHours < 48) {
      return '어제';
    } else {
      // 절대 시간 표시
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
        <Typography color="text.primary">{category?.display_name || categoryName}</Typography>
      </Breadcrumbs>

      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={4}>
        <Box>
          <Typography variant="h3" component="h1" gutterBottom>
            {category?.display_name || categoryName}
          </Typography>
          {category?.description && (
            <Typography color="text.secondary">{category.description}</Typography>
          )}
        </Box>
        
        <Box display="flex" gap={2}>
          <IconButton onClick={() => router.push('/community')}>
            <ArrowBackIcon />
          </IconButton>
          {!loading && canCreatePost() && (
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={() => router.push(`/community/write?category=${categoryName}`)}
              sx={{
                background: `linear-gradient(45deg, ${theme.palette.primary.main} 30%, ${theme.palette.secondary.main} 90%)`,
              }}
            >
              글쓰기
            </Button>
          )}
        </Box>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 4 }}>{error}</Alert>}

      {/* Search Bar */}
      <Box component="form" onSubmit={handleSearch} mb={4}>
        <TextField
          fullWidth
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          placeholder="제목이나 내용으로 검색..."
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon />
              </InputAdornment>
            ),
          }}
        />
      </Box>

      {/* Posts Table */}
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell width="70%">제목</TableCell>
              <TableCell align="center">작성자</TableCell>
              <TableCell align="center">조회</TableCell>
              <TableCell align="center">댓글</TableCell>
              <TableCell align="center">작성일</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {posts.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} align="center" sx={{ py: 8 }}>
                  <Typography color="text.secondary">
                    아직 작성된 글이 없습니다.
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              posts.map((post) => (
                <TableRow
                  key={post.id}
                  hover
                  onClick={() => router.push(`/community/${categoryName}/${post.id}`)}
                  sx={{ cursor: 'pointer' }}
                >
                  <TableCell>
                    <Box display="flex" alignItems="center" gap={1}>
                      {post.is_pinned && (
                        <Chip
                          icon={<PushPinIcon />}
                          label="공지"
                          color="error"
                          size="small"
                        />
                      )}
                      {post.is_private && (
                        <span title="비밀글">🔒</span>
                      )}
                      <Typography 
                        variant="body1" 
                        sx={{ 
                          color: post.is_private ? 'text.secondary' : 'text.primary',
                          fontStyle: post.is_private ? 'italic' : 'normal'
                        }}
                      >
                        {post.is_private && user?.publicMetadata?.role !== 'admin'
                          ? '🔒 비밀글입니다'
                          : post.title
                        }
                      </Typography>
                    </Box>
                  </TableCell>
                  <TableCell align="center">
                    <Box display="flex" alignItems="center" justifyContent="center" gap={0.5}>
                      <PersonIcon fontSize="small" color="action" />
                      <Typography variant="body2">
                        <UserDisplayName author={post.author} variant="short" showRole />
                      </Typography>
                    </Box>
                  </TableCell>
                  <TableCell align="center">
                    <Box display="flex" alignItems="center" justifyContent="center" gap={0.5}>
                      <VisibilityIcon fontSize="small" color="action" />
                      {post.view_count}
                    </Box>
                  </TableCell>
                  <TableCell align="center">
                    <Box display="flex" alignItems="center" justifyContent="center" gap={0.5}>
                      <CommentIcon fontSize="small" color="action" />
                      {post.comments?.length || 0}
                    </Box>
                  </TableCell>
                  <TableCell align="center">
                    <Box display="flex" alignItems="center" justifyContent="center" gap={0.5}>
                      <CalendarTodayIcon fontSize="small" color="action" />
                      <Typography variant="body2">
                        {formatDate(post.created_at)}
                      </Typography>
                    </Box>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
        <TablePagination
          rowsPerPageOptions={[10, 20, 50]}
          component="div"
          count={-1} // We don't have total count from API, could add this later
          rowsPerPage={rowsPerPage}
          page={page}
          onPageChange={handleChangePage}
          onRowsPerPageChange={handleChangeRowsPerPage}
          labelRowsPerPage="페이지당 행:"
        />
      </TableContainer>
    </Container>
  );
}

export default function CategoryPostsPage() {
  return (
    <Suspense fallback={
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Box display="flex" justifyContent="center" alignItems="center" minHeight="50vh">
          <CircularProgress />
        </Box>
      </Container>
    }>
      <CategoryPostsPageContent />
    </Suspense>
  );
} 