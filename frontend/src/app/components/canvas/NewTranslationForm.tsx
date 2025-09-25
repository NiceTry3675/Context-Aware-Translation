'use client';

import React from 'react';
import {
  Box,
  Paper,
  Typography,
  IconButton,
  Card,
  CardContent,
} from '@mui/material';
import KeyboardArrowLeftIcon from '@mui/icons-material/KeyboardArrowLeft';
import ApiSetup from '../ApiConfiguration/ApiSetup';
import TaskModelOverrides, { TaskModelOverrides as TaskModelOverridesType } from '../ApiConfiguration/TaskModelOverrides';
import FileUploadSection from '../FileUpload/FileUploadSection';
import TranslationSettings from '../AdvancedSettings/TranslationSettings';
import StyleConfigForm from '../StyleConfiguration/StyleConfigForm';
import { StyleData, GlossaryTerm, TranslationSettings as TSettings } from '../../types/ui';
import type { ApiProvider } from '../../hooks/useApiKey';
import { isOpenRouterGeminiModel } from '../../utils/constants/models';

interface NewTranslationFormProps {
  jobId: string | null;
  apiProvider: ApiProvider;
  apiKey: string;
  providerConfig: string;
  selectedModel: string;
  taskModelOverrides?: TaskModelOverridesType;
  taskOverridesEnabled?: boolean;
  translationSettings: TSettings;
  showStyleForm: boolean;
  styleData: StyleData | null;
  glossaryData: GlossaryTerm[];
  isAnalyzing: boolean;
  isAnalyzingGlossary: boolean;
  uploading: boolean;
  translationError: string | null;
  glossaryAnalysisError: string;
  onProviderChange: (provider: ApiProvider) => void;
  onApiKeyChange: (key: string) => void;
  onProviderConfigChange: (value: string) => void;
  onModelChange: (model: string) => void;
  onTaskModelOverridesChange?: (overrides: TaskModelOverridesType) => void;
  onTaskOverridesEnabledChange?: (enabled: boolean) => void;
  onFileSelect: (file: File, analyzeGlossary: boolean) => Promise<any>;
  onTranslationSettingsChange: (settings: TSettings) => void;
  onStyleChange: (style: StyleData) => void;
  onGlossaryChange: (glossary: GlossaryTerm[]) => void;
  onSubmit: () => Promise<void>;
  onCancel: () => void;
  onClose: () => void;
}

export default function NewTranslationForm({
  jobId,
  apiProvider,
  apiKey,
  providerConfig,
  selectedModel,
  taskModelOverrides,
  taskOverridesEnabled,
  translationSettings,
  showStyleForm,
  styleData,
  glossaryData,
  isAnalyzing,
  isAnalyzingGlossary,
  uploading,
  translationError,
  glossaryAnalysisError,
  onProviderChange,
  onApiKeyChange,
  onProviderConfigChange,
  onModelChange,
  onTaskModelOverridesChange,
  onTaskOverridesEnabledChange,
  onFileSelect,
  onTranslationSettingsChange,
  onStyleChange,
  onGlossaryChange,
  onSubmit,
  onCancel,
  onClose
}: NewTranslationFormProps) {
  const isTurboLocked = apiProvider === 'openrouter' && !isOpenRouterGeminiModel(selectedModel);

  return (
    <Paper sx={{ p: 3, overflowY: 'auto', height: '100%' }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6">새 번역 시작</Typography>
        {jobId && (
          <IconButton onClick={onClose} size="small">
            <KeyboardArrowLeftIcon />
          </IconButton>
        )}
      </Box>
      <Card sx={{ maxWidth: '100%' }}>
        <CardContent>
          <ApiSetup
            apiProvider={apiProvider}
            apiKey={apiKey}
            providerConfig={providerConfig}
            selectedModel={selectedModel}
            onProviderChange={onProviderChange}
            onApiKeyChange={onApiKeyChange}
            onProviderConfigChange={onProviderConfigChange}
            onModelChange={onModelChange}
          />

          {onTaskModelOverridesChange && (
            <TaskModelOverrides
              apiProvider={apiProvider}
              values={taskModelOverrides || { styleModel: selectedModel, glossaryModel: selectedModel }}
              onChange={onTaskModelOverridesChange}
              enabled={!!taskOverridesEnabled}
              onEnabledChange={(en) => onTaskOverridesEnabledChange?.(en)}
            />
          )}

          <FileUploadSection
            isAnalyzing={isAnalyzing}
            isAnalyzingGlossary={isAnalyzingGlossary}
            uploading={uploading}
            error={translationError || ''}
            onFileSelect={onFileSelect}
          />
        </CardContent>

        <CardContent sx={{ borderTop: 1, borderColor: 'divider', mt: 2 }}>
          <TranslationSettings
            settings={translationSettings}
            onChange={onTranslationSettingsChange}
            isTurboLocked={isTurboLocked}
          />
        </CardContent>

        {showStyleForm && styleData && (
          <CardContent sx={{ borderTop: 1, borderColor: 'divider', mt: 2 }}>
            <StyleConfigForm
              styleData={styleData}
              glossaryData={glossaryData}
              isAnalyzingGlossary={isAnalyzingGlossary}
              glossaryAnalysisError={glossaryAnalysisError}
              uploading={uploading}
              onStyleChange={onStyleChange}
              onGlossaryChange={onGlossaryChange}
              onSubmit={onSubmit}
              onCancel={onCancel}
            />
          </CardContent>
        )}
      </Card>
    </Paper>
  );
}
