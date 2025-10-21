'use client';

import React, { Suspense, useRef, useEffect } from 'react';
import { Box, Container, CircularProgress } from '@mui/material';
import { useCanvasState } from './hooks/useCanvasState';
import { regenerateIllustration } from './utils/api';
import { getCachedClerkToken } from './utils/authToken';
import JobSidebar from './components/canvas/JobSidebar';
import CanvasHeader from './components/canvas/CanvasHeader';
import NewTranslationForm from './components/canvas/NewTranslationForm';
import ResultsView from './components/canvas/ResultsView';
import ValidationDialog from './components/TranslationSidebar/ValidationDialog';
import PostEditDialog from './components/TranslationSidebar/PostEditDialog';
import IllustrationDialog from './components/TranslationSidebar/IllustrationDialog';
import { ensureOpenRouterGeminiModel } from './utils/constants/models';

function CanvasContent() {
  const mainContainerRef = useRef<HTMLDivElement>(null);
  const state = useCanvasState();
  const editTimersRef = useRef<Record<string, any>>({});
  const [mobileDrawerOpen, setMobileDrawerOpen] = React.useState(false);
  const resolveDialogModel = (model: string) => (
    state.apiProvider === 'openrouter'
      ? ensureOpenRouterGeminiModel(model)
      : model
  );
  const validationDialogModel = resolveDialogModel(state.validationModelName || state.selectedModel);
  const postEditDialogModel = resolveDialogModel(state.postEditModelName || state.selectedModel);

  const handleDrawerToggle = () => {
    setMobileDrawerOpen(!mobileDrawerOpen);
  };
  
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
          onJobSelect={(jobId) => {
            state.handleJobChange(jobId);
            setMobileDrawerOpen(false); // Close drawer on mobile after selection
          }}
          onJobDelete={state.handleJobDelete}
          onNewTranslation={() => {
            state.handleNewTranslation();
            setMobileDrawerOpen(false); // Close drawer on mobile after action
          }}
          onRefreshJobs={state.refreshJobPublic}
          loading={state.dataLoading}
          apiProvider={state.apiProvider}
          defaultModelName={state.selectedModel}
          apiKey={state.apiKey}
          providerConfig={state.providerConfig}
          mobileOpen={mobileDrawerOpen}
          onMobileClose={handleDrawerToggle}
        />

        <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
          <CanvasHeader
            selectedJob={state.selectedJob}
            fullscreen={state.fullscreen}
            onToggleFullscreen={handleToggleFullscreen}
            onMenuClick={handleDrawerToggle}
            onRefresh={() => {
              // Refresh the selected job metadata (public GET) and reload sidebar data
              if (state.jobId) {
                state.refreshJobPublic(state.jobId);
              }
              state.loadData();
            }}
          />

          <Container
            maxWidth={false}
            sx={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              py: { xs: 1, sm: 2 },
              px: { xs: 1, sm: 2, md: 3 },
              gap: 2,
              overflow: 'auto'
            }}
          >
            {state.showNewTranslation ? (
              <NewTranslationForm
                jobId={state.jobId}
                apiProvider={state.apiProvider}
                apiKey={state.apiKey}
                providerConfig={state.providerConfig}
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
                onProviderConfigChange={state.setProviderConfig}
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
                apiProvider={state.apiProvider}
                providerConfig={state.providerConfig}
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
                onRegenerateIllustration={async (segmentIndex: number, customPrompt?: string) => {
                  try {
                    const token = await getCachedClerkToken(state.getToken);
                    await regenerateIllustration({
                      jobId: state.jobId || '',
                      segmentIndex,
                      token: token || undefined,
                      customPrompt,
                      apiProvider: state.apiProvider,
                      apiKey: state.apiKey,
                      providerConfig: state.providerConfig,
                    });

                    // Refresh data after regeneration
                    setTimeout(() => {
                      if (state.jobId) {
                        state.refreshJobPublic(state.jobId);
                      }
                    }, 2000);

                    console.log('Successfully regenerated illustration for segment', segmentIndex, 'with custom prompt:', !!customPrompt);
                  } catch (error) {
                    console.error('Failed to regenerate illustration:', error);
                    // TODO: Show error notification to user
                  }
                }}
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
        modelName={validationDialogModel}
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
        modelName={postEditDialogModel}
        onModelNameChange={state.setPostEditModelName}
        selectedCases={state.selectedCases}
        setSelectedCases={state.setSelectedCases}
      />

      <IllustrationDialog
        open={state.illustrationDialogOpen}
        onClose={() => state.setIllustrationDialogOpen(false)}
        onConfirm={state.onConfirmIllustration}
        style={state.illustrationStyle}
        onStyleChange={state.setIllustrationStyle}
        styleHints={state.illustrationStyleHints}
        onStyleHintsChange={state.setIllustrationStyleHints}
        promptModelName={state.illustrationPromptModel}
        onPromptModelNameChange={state.setIllustrationPromptModel}
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
