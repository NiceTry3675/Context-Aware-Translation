'use client';

import React, { Suspense, useRef, useEffect } from 'react';
import { Box, Container, CircularProgress } from '@mui/material';
import { useCanvasState } from './hooks/useCanvasState';
import JobSidebar from './components/canvas/JobSidebar';
import CanvasHeader from './components/canvas/CanvasHeader';
import NewTranslationForm from './components/canvas/NewTranslationForm';
import ResultsView from './components/canvas/ResultsView';
import ValidationDialog from './components/TranslationSidebar/ValidationDialog';
import PostEditDialog from './components/TranslationSidebar/PostEditDialog';

function CanvasContent() {
  const mainContainerRef = useRef<HTMLDivElement>(null);
  const state = useCanvasState();
  
  const handleToggleFullscreen = () => {
    if (!document.fullscreenElement) {
      mainContainerRef.current?.requestFullscreen().catch(err => {
        console.error(`Error attempting to enable full-screen mode: ${err.message} (${err.name})`);
      });
    } else {
      document.exitFullscreen();
    }
  };

  useEffect(() => {
    const handleFullscreenChange = () => {
      state.setFullscreen(!!document.fullscreenElement);
    };
    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
    };
  }, [state]);

  useEffect(() => {
    if (state.isSignedIn === false) {
      state.router.push('/about');
    }
  }, [state.isSignedIn, state.router]);

  if (!state.isSignedIn) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <>
      <Box 
        sx={{ 
          height: '100vh', 
          display: 'flex', 
          backgroundColor: 'background.default' 
        }}
        ref={mainContainerRef}
      >
        <JobSidebar
          jobs={state.jobs}
          selectedJobId={state.jobId}
          onJobSelect={state.handleJobChange}
          onJobDelete={state.handleJobDelete}
          onNewTranslation={state.handleNewTranslation}
          onRefreshJobs={state.refreshJobPublic}
          loading={state.dataLoading}
          apiProvider={state.apiProvider}
          defaultModelName={state.selectedModel}
        />
        
        <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          <CanvasHeader
            selectedJob={state.selectedJob}
            fullscreen={state.fullscreen}
            onToggleFullscreen={handleToggleFullscreen}
          />

          <Container maxWidth={false} sx={{ flex: 1, display: 'flex', flexDirection: 'column', py: 2, gap: 2, overflow: 'auto' }}>
            {state.showNewTranslation ? (
              <NewTranslationForm
                jobId={state.jobId}
                apiProvider={state.apiProvider}
                apiKey={state.apiKey}
                selectedModel={state.selectedModel}
                taskModelOverrides={state.taskModelOverrides}
                taskOverridesEnabled={state.taskOverridesEnabled}
                translationSettings={state.translationSettings}
                showStyleForm={state.showStyleForm}
                styleData={state.styleData}
                glossaryData={state.glossaryData}
                isAnalyzing={state.isAnalyzing}
                isAnalyzingGlossary={state.isAnalyzingGlossary}
                uploading={state.uploading}
                translationError={state.translationError || null}
                glossaryAnalysisError={state.glossaryAnalysisError}
                onProviderChange={state.setApiProvider}
                onApiKeyChange={state.setApiKey}
                onModelChange={state.setSelectedModel}
                onTaskModelOverridesChange={state.setTaskModelOverrides}
                onTaskOverridesEnabledChange={state.setTaskOverridesEnabled}
                onFileSelect={state.handleFileSelect}
                onTranslationSettingsChange={state.setTranslationSettings}
                onStyleChange={state.setStyleData}
                onGlossaryChange={state.setGlossaryData}
                onSubmit={state.handleStartTranslation}
                onCancel={state.handleCancelStyleEdit}
                onClose={() => state.setShowNewTranslation(false)}
              />
            ) : (
              <ResultsView
                jobId={state.jobId}
                selectedJob={state.selectedJob}
                tabValue={state.tabValue}
                viewMode={state.viewMode}
                errorFilters={state.errorFilters}
                isPolling={state.isPolling}
                dataLoading={state.dataLoading}
                error={state.error || ''}
                loading={state.loading}
                validationReport={state.validationReport}
                postEditLog={state.postEditLog}
                translationContent={state.translationContent}
                translationSegments={state.translationSegments}
                fullSourceText={state.fullSourceText}
                selectedIssues={state.selectedIssues}
                segmentNav={state.segmentNav}
                onTabChange={state.handleTabChange}
                onViewModeChange={state.setViewMode}
                onErrorFiltersChange={state.setErrorFilters}
                onShowNewTranslation={state.handleNewTranslation}
                onLoadData={state.loadData}
                onLoadMoreSegments={state.loadMoreSegments}
                onIssueSelectionChange={() => { /* structured-only: legacy issue selection not used */ }}
                onSegmentClick={(index) => {
                  state.setViewMode('segment');
                  state.segmentNav.goToSegment(index);
                }}
                selectedCases={state.selectedCases}
                onCaseSelectionChange={(segmentIndex, caseIndex, selected, totalCases) => {
                  state.setSelectedCases(prev => {
                    const next = { ...prev } as Record<number, boolean[]>;
                    const arr = next[segmentIndex] ? next[segmentIndex].slice() : new Array(totalCases).fill(true);
                    arr[caseIndex] = selected;
                    next[segmentIndex] = arr;
                    return next;
                  });
                }}
                onOpenValidationDialog={() => state.setValidationDialogOpen(true)}
                onOpenPostEditDialog={() => state.setPostEditDialogOpen(true)}
              />
            )}
          </Container>
        </Box>
      </Box>

      <ValidationDialog
        open={state.validationDialogOpen}
        onClose={() => state.setValidationDialogOpen(false)}
        onConfirm={state.onConfirmValidation}
        quickValidation={state.quickValidation}
        onQuickValidationChange={state.setQuickValidation}
        validationSampleRate={state.validationSampleRate}
        onValidationSampleRateChange={state.setValidationSampleRate}
        loading={state.loading}
        apiProvider={state.apiProvider}
        modelName={state.validationModelName || state.selectedModel}
        onModelNameChange={state.setValidationModelName}
      />

      <PostEditDialog
        open={state.postEditDialogOpen}
        onClose={() => state.setPostEditDialogOpen(false)}
        onConfirm={state.onConfirmPostEdit}
        validationReport={state.validationReport}
        loading={state.loading}
        selectedCounts={{ total: Object.values(state.selectedCases).reduce((acc, arr) => acc + (arr?.filter(Boolean).length || 0), 0) }}
        apiProvider={state.apiProvider}
        modelName={state.postEditModelName || state.selectedModel}
        onModelNameChange={state.setPostEditModelName}
      />
    </>
  );
}

export default function CanvasPage() {
  return (
    <Suspense fallback={
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <CircularProgress />
      </Box>
    }>
      <CanvasContent />
    </Suspense>
  );
}
