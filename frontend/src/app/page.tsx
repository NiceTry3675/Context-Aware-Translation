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
          onRefreshJobs={state.refreshJobs}
          loading={state.dataLoading}
        />
        
        <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          <CanvasHeader
            selectedJob={state.selectedJob}
            fullscreen={state.fullscreen}
            onToggleFullscreen={handleToggleFullscreen}
          />

          <Container maxWidth={false} sx={{ flex: 1, display: 'flex', flexDirection: 'column', py: 2, gap: 2, overflow: 'hidden' }}>
            {state.showNewTranslation ? (
              <NewTranslationForm
                jobId={state.jobId}
                apiProvider={state.apiProvider}
                apiKey={state.apiKey}
                selectedModel={state.selectedModel}
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
                onIssueSelectionChange={(segmentIndex, issueType, issueIndex, selected) => {
                  state.setSelectedIssues(prev => {
                    const newState = { ...prev };
                    
                    if (!newState[segmentIndex]) {
                      const segment = state.validationReport?.detailed_results.find(r => r.segment_index === segmentIndex);
                      if (!segment) return prev;
                      
                      newState[segmentIndex] = {
                        critical: new Array(segment.critical_issues.length).fill(true),
                        missing_content: new Array(segment.missing_content.length).fill(true),
                        added_content: new Array(segment.added_content.length).fill(true),
                        name_inconsistencies: new Array(segment.name_inconsistencies.length).fill(true),
                        minor: new Array(segment.minor_issues.length).fill(true),
                      };
                    }
                    
                    if (!newState[segmentIndex][issueType]) {
                      return prev;
                    }
                    
                    newState[segmentIndex] = {
                      ...newState[segmentIndex],
                      [issueType]: newState[segmentIndex][issueType].map((val, idx) => 
                        idx === issueIndex ? selected : val
                      )
                    };
                    
                    return newState;
                  });
                }}
                onSegmentClick={(index) => {
                  state.setViewMode('segment');
                  state.segmentNav.goToSegment(index);
                }}
              />
            )}
          </Container>
        </Box>
      </Box>

      <ValidationDialog
        open={state.validation.validationDialogOpen}
        onClose={() => state.validation.setValidationDialogOpen(false)}
        onConfirm={state.validation.handleTriggerValidation}
        quickValidation={state.validation.quickValidation}
        onQuickValidationChange={state.validation.setQuickValidation}
        validationSampleRate={state.validation.validationSampleRate}
        onValidationSampleRateChange={state.validation.setValidationSampleRate}
        loading={state.validation.loading}
      />

      <PostEditDialog
        open={state.postEdit.postEditDialogOpen}
        onClose={() => state.postEdit.setPostEditDialogOpen(false)}
        onConfirm={state.postEdit.handleTriggerPostEdit}
        selectedIssueTypes={state.postEdit.selectedIssueTypes}
        onIssueTypeChange={(issueType, checked) => 
          state.postEdit.setSelectedIssueTypes({ ...state.postEdit.selectedIssueTypes, [issueType]: checked })
        }
        validationReport={state.validationReport}
        loading={state.postEdit.loading}
        selectedCounts={state.selectedCounts}
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