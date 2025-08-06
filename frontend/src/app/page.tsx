"use client";

import { useState, useEffect, Suspense } from 'react';
import { useAuth } from '@clerk/nextjs';
import { useRouter, useSearchParams } from 'next/navigation';
import {
  Container, Box, Button, Card, CardContent
} from '@mui/material';
import { Forum as ForumIcon } from '@mui/icons-material';
import theme from '../theme';

// Components
import AuthButtons from './components/AuthButtons';
import HeroSection from './components/sections/HeroSection';
import FeatureSection from './components/sections/FeatureSection';
import Footer from './components/sections/Footer';
import JobsTable from './components/jobs/JobsTable';
import ApiSetup from './components/ApiConfiguration/ApiSetup';
import FileUploadSection from './components/FileUpload/FileUploadSection';
import TranslationSettings from './components/AdvancedSettings/TranslationSettings';
import StyleConfigForm from './components/StyleConfiguration/StyleConfigForm';

// Hooks
import { useTranslationJobs } from './hooks/useTranslationJobs';
import { useApiKey } from './hooks/useApiKey';
import { useTranslationService } from './hooks/useTranslationService';
import { useJobActions } from './hooks/useJobActions';

// Types
import { 
  StyleData, 
  GlossaryTerm, 
  TranslationSettings as TSettings 
} from './types/translation';

function HomeContent() {
  const { isSignedIn, isLoaded } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const action = searchParams.get('action');
  
  // Use custom hooks
  const { apiKey, setApiKey, apiProvider, setApiProvider, selectedModel, setSelectedModel } = useApiKey();
  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const { jobs, addJob, deleteJob, refreshJobs } = useTranslationJobs({ apiUrl: API_URL });
  
  // File & style states
  const [file, setFile] = useState<File | null>(null);
  const [styleData, setStyleData] = useState<StyleData | null>(null);
  const [showStyleForm, setShowStyleForm] = useState<boolean>(false);
  const [glossaryData, setGlossaryData] = useState<GlossaryTerm[]>([]);
  const [glossaryAnalysisError, setGlossaryAnalysisError] = useState<string>('');
  
  // Translation settings
  const [translationSettings, setTranslationSettings] = useState<TSettings>({
    segmentSize: 15000,
    enableValidation: false,
    quickValidation: false,
    validationSampleRate: 100,
    enablePostEdit: false
  });
  
  // Dev mode
  const [devMode, setDevMode] = useState<boolean>(false);
  
  // Translation service hook
  const {
    analyzeFile,
    startTranslation,
    isAnalyzing,
    isAnalyzingGlossary,
    uploading,
    error,
    setError
  } = useTranslationService({
    apiUrl: API_URL,
    apiKey,
    selectedModel,
    onJobCreated: (job) => {
      addJob(job);
      setFile(null);
      setStyleData(null);
      setGlossaryData([]);
      setShowStyleForm(false);
      // Navigate to canvas after job creation
      router.push(`/canvas?jobId=${job.id}`);
    }
  });
  
  // Job actions hook
  const jobActions = useJobActions({
    apiUrl: API_URL,
    onError: setError,
    onSuccess: refreshJobs
  });

  // Load dev mode setting
  useEffect(() => {
    setDevMode(localStorage.getItem('devMode') === 'true');
  }, []);
  
  // Redirect logged-in users to canvas (unless they're creating a new translation)
  useEffect(() => {
    if (isLoaded && isSignedIn && action !== 'new') {
      router.push('/canvas');
    }
  }, [isLoaded, isSignedIn, action, router]);

  // File analysis handler
  const handleFileSelect = async (selectedFile: File, analyzeGlossary: boolean) => {
    setFile(selectedFile);
    setGlossaryAnalysisError('');
    
    const result = await analyzeFile(selectedFile, analyzeGlossary);
    
    if (result.styleData) {
      setStyleData(result.styleData);
      setGlossaryData(result.glossaryData);
      setShowStyleForm(true);
    }
    
    if (result.error) {
      setGlossaryAnalysisError(result.error);
    }
    
    return result;
  };

  // Start translation handler
  const handleStartTranslation = async () => {
    if (!file || !styleData) {
      setError("번역을 시작할 파일과 스타일 정보가 필요합니다.");
      return;
    }

    await startTranslation(file, styleData, glossaryData, translationSettings);
  };

  const handleCancelStyleEdit = () => {
    setShowStyleForm(false);
    setFile(null);
    setStyleData(null);
    setGlossaryData([]);
    const fileInput = document.getElementById('file-upload-input') as HTMLInputElement;
    if (fileInput) fileInput.value = '';
  };

  // Wrapper functions for job actions
  const handleTriggerValidation = (jobId: number) => {
    return jobActions.handleTriggerValidation(
      jobId,
      translationSettings.quickValidation,
      translationSettings.validationSampleRate
    );
  };

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      {/* Top Navigation */}
      <Box sx={{ position: 'fixed', top: 32, right: 32, zIndex: 1000, display: 'flex', gap: 2 }}>
        {isSignedIn && (
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
        )}
        <AuthButtons />
      </Box>

      {/* Hero Section */}
      <HeroSection />

      {/* Feature Section */}
      <FeatureSection />

      {/* Main Translation Card */}
      <Card sx={{ p: { xs: 2, md: 4 }, mb: 8 }}>
        <CardContent>
          {/* API Configuration */}
          <ApiSetup
            apiProvider={apiProvider}
            apiKey={apiKey}
            selectedModel={selectedModel}
            onProviderChange={setApiProvider}
            onApiKeyChange={setApiKey}
            onModelChange={setSelectedModel}
          />

          {/* File Upload */}
          <FileUploadSection
            isAnalyzing={isAnalyzing}
            isAnalyzingGlossary={isAnalyzingGlossary}
            uploading={uploading}
            error={error}
            onFileSelect={handleFileSelect}
          />
        </CardContent>

        {/* Advanced Settings */}
        <CardContent sx={{ borderTop: 1, borderColor: 'divider', mt: 2 }}>
          <TranslationSettings
            settings={translationSettings}
            onChange={setTranslationSettings}
          />
        </CardContent>

        {/* Style & Glossary Configuration */}
        {showStyleForm && styleData && (
          <CardContent sx={{ borderTop: 1, borderColor: 'divider', mt: 2 }}>
            <StyleConfigForm
              styleData={styleData}
              glossaryData={glossaryData}
              isAnalyzingGlossary={isAnalyzingGlossary}
              glossaryAnalysisError={glossaryAnalysisError}
              uploading={uploading}
              onStyleChange={setStyleData}
              onGlossaryChange={setGlossaryData}
              onSubmit={handleStartTranslation}
              onCancel={handleCancelStyleEdit}
            />
          </CardContent>
        )}
      </Card>

      {/* Jobs Table */}
      <JobsTable
        jobs={jobs}
        onDelete={deleteJob}
        onDownload={jobActions.handleDownload}
        onTriggerValidation={handleTriggerValidation}
        onTriggerPostEdit={jobActions.handleTriggerPostEdit}
        onDownloadValidationReport={jobActions.handleDownloadValidationReport}
        onDownloadPostEditLog={jobActions.handleDownloadPostEditLog}
        devMode={devMode}
        apiUrl={API_URL}
      />

      {/* Footer */}
      <Footer />
    </Container>
  );
}

export default function Home() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <HomeContent />
    </Suspense>
  );
}