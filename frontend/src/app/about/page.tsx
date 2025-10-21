"use client";

import { Suspense } from 'react';
import { useAuth } from '@clerk/nextjs';
import { useRouter } from 'next/navigation';
import {
  Container, Box, Button
} from '@mui/material';
import { Forum as ForumIcon } from '@mui/icons-material';
import theme from '../../theme';

// Components
import AuthButtons from '../components/AuthButtons';
import HeroSection from '../components/sections/HeroSection';
import FeatureSection from '../components/sections/FeatureSection';
import Footer from '../components/sections/Footer';

function HomeContent() {
  const { isSignedIn } = useAuth();
  const router = useRouter();
  
  

  return (
    <Container maxWidth="lg" sx={{ py: { xs: 2, sm: 4 } }}>
      {/* Top Navigation */}
      <Box
        sx={{
          position: 'fixed',
          top: { xs: 16, sm: 32 },
          right: { xs: 16, sm: 32 },
          zIndex: 1000,
          display: 'flex',
          flexDirection: { xs: 'column', sm: 'row' },
          gap: { xs: 1, sm: 2 },
          alignItems: { xs: 'flex-end', sm: 'center' }
        }}
      >
        {isSignedIn && (
          <>
            <Button
              variant="contained"
              onClick={() => router.push('/')}
              size="small"
              sx={{ fontSize: { xs: '0.75rem', sm: '0.875rem' } }}
            >
              작업 공간으로 돌아가기
            </Button>
            <Button
              variant="outlined"
              startIcon={<ForumIcon sx={{ display: { xs: 'none', sm: 'block' } }} />}
              onClick={() => router.push('/community')}
              size="small"
              sx={{
                borderColor: theme.palette.primary.main,
                color: theme.palette.primary.main,
                fontSize: { xs: '0.75rem', sm: '0.875rem' },
                '&:hover': {
                  borderColor: theme.palette.primary.dark,
                  backgroundColor: `${theme.palette.primary.main}10`,
                }
              }}
            >
              커뮤니티
            </Button>
          </>
        )}
        <AuthButtons />
      </Box>

      {/* Hero Section */}
      <HeroSection />

      {/* Feature Section */}
      <FeatureSection />

      {/* Footer */}
      <Footer />
    </Container>
  );
}

export default function AboutPage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <HomeContent />
    </Suspense>
  );
}
