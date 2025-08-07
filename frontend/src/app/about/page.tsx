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
    <Container maxWidth="lg" sx={{ py: 4 }}>
      {/* Top Navigation */}
      <Box sx={{ position: 'fixed', top: 32, right: 32, zIndex: 1000, display: 'flex', gap: 2 }}>
        {isSignedIn && (
          <>
            <Button
              variant="contained"
              onClick={() => router.push('/')}
            >
              작업 공간으로 돌아가기
            </Button>
            <Button
              variant="outlined"
              startIcon={<ForumIcon />}
              onClick={() => router.push('/community')}
              sx={{
                borderColor: theme.palette.primary.main,
                color: theme.palette.primary.main,
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
