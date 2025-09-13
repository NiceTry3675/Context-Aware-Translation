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
import IllustrationDialog from './components/TranslationSidebar/IllustrationDialog';

function CanvasContent() {
  const mainContainerRef = useRef<HTMLDivElement>(null);
  const state = useCanvasState();
  const editTimersRef = useRef<Record<string, any>>({});
  
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
            onRefresh={state.loadData}
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
                apiKey={state.apiKey}
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
                segmentNav={state.segmentNav}
                onTabChange={state.handleTabChange}
                onViewModeChange={state.setViewMode}
                onErrorFiltersChange={state.setErrorFilters}
                onShowNewTranslation={state.handleNewTranslation}
                onLoadData={state.loadData}
                onLoadMoreSegments={state.loadMoreSegments}
                
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
                onOpenIllustrationDialog={() => state.setIllustrationDialogOpen(true)}
                modifiedCases={state.modifiedCases}
                onCaseEditChange={(segmentIndex, caseIndex, patch) => {
                  const key = `${segmentIndex}:${caseIndex}`;
                  if (editTimersRef.current[key]) clearTimeout(editTimersRef.current[key]);
                  editTimersRef.current[key] = setTimeout(() => {
                    state.setModifiedCases(prev => {
                      const next = { ...prev } as Record<number, Array<{ reason?: string; recommend_korean_sentence?: string }>>;
                      const arr = next[segmentIndex] ? next[segmentIndex].slice() : [];
                      while (arr.length <= caseIndex) arr.push({});
                      const current = { ...(arr[caseIndex] || {}) };
                      arr[caseIndex] = { ...current, ...patch };
                      next[segmentIndex] = arr;
                      return next;
                    });
                  }, 250);
                }}
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
        onClose={() => {
          state.setPostEditDialogOpen(false);
          // Keep selection state; do not reset to avoid losing user choices
        }}
        onConfirm={state.onConfirmPostEdit}
        validationReport={state.validationReport}
        loading={state.loading}
        selectedCounts={{
          total: (() => {
            const results = state.validationReport?.detailed_results || [];
            if (!results || results.length === 0) return 0;
            let sum = 0;
            for (const seg of results as any[]) {
              const idx = seg.segment_index as number;
              const cases: any[] = Array.isArray(seg.structured_cases) ? seg.structured_cases : [];
              if (!cases.length) continue; // exclude segments without cases
              const sel = (state.selectedCases as Record<number, boolean[]>)[idx];
              if (Array.isArray(sel)) {
                sum += sel.filter(Boolean).length;
              } else {
                // default-select-all semantics when no entry exists
                sum += cases.length;
              }
            }
            return sum;
          })()
        }}
        apiProvider={state.apiProvider}
        modelName={state.postEditModelName || state.selectedModel}
        onModelNameChange={state.setPostEditModelName}
      />

      <IllustrationDialog
        open={state.illustrationDialogOpen}
        onClose={() => state.setIllustrationDialogOpen(false)}
        onConfirm={state.onConfirmIllustration}
        style={state.illustrationStyle}
        onStyleChange={state.setIllustrationStyle}
        styleHints={state.illustrationStyleHints}
        onStyleHintsChange={state.setIllustrationStyleHints}
        minSegmentLength={state.illustrationMinSegmentLength}
        onMinSegmentLengthChange={state.setIllustrationMinSegmentLength}
        skipDialogueHeavy={state.illustrationSkipDialogueHeavy}
        onSkipDialogueHeavyChange={state.setIllustrationSkipDialogueHeavy}
        maxIllustrations={state.illustrationMaxCount}
        onMaxIllustrationsChange={state.setIllustrationMaxCount}
        loading={state.loading}
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
