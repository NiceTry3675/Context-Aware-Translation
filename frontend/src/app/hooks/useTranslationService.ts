import { useState, useCallback } from 'react';
import { useAuth, useClerk } from '@clerk/nextjs';
import { getCachedClerkToken } from '../utils/authToken';
import type { components } from '@/types/api';
import { StyleData, GlossaryTerm, TranslationSettings } from '../types/ui';
import type { ApiProvider } from './useApiKey';

// Type aliases for convenience
type TranslationJob = components['schemas']['TranslationJob'];
type StyleAnalysisResponse = components['schemas']['StyleAnalysisResponse'];
type GlossaryAnalysisResponse = components['schemas']['GlossaryAnalysisResponse'];
type TranslatedTerm = components['schemas']['TranslatedTerm'];

interface FileAnalysisResult {
  styleData: StyleData | null;
  glossaryData: GlossaryTerm[];
  error: string | null;
}

interface UseTranslationServiceOptions {
  apiUrl: string;
  apiProvider: ApiProvider;
  apiKey: string;
  backupApiKeys?: string[];
  requestsPerMinute?: number;
  providerConfig: string;
  selectedModel: string;
  selectedStyleModel?: string;
  selectedGlossaryModel?: string;
  onJobCreated?: (job: TranslationJob) => void;
}

export function useTranslationService({
  apiUrl,
  apiProvider,
  apiKey,
  backupApiKeys,
  requestsPerMinute,
  providerConfig,
  selectedModel,
  selectedStyleModel,
  selectedGlossaryModel,
  onJobCreated
}: UseTranslationServiceOptions) {
  const { getToken, isSignedIn, isLoaded } = useAuth();
  const { openSignIn } = useClerk();
  
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isAnalyzingGlossary, setIsAnalyzingGlossary] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const analyzeFile = useCallback(async (
    file: File,
    analyzeGlossary: boolean = true
  ): Promise<FileAnalysisResult> => {
    if (!isLoaded) {
      throw new Error("인증 정보를 불러오는 중입니다. 잠시 후 다시 시도해주세요.");
    }
    
    if (!isSignedIn) {
      openSignIn({ redirectUrl: '/' });
      throw new Error("번역을 시작하려면 먼저 로그인해주세요.");
    }
    
    const usableBackupKeys = (backupApiKeys || []).map((k) => (k || '').trim()).filter((k) => k);
    const hasAnyGeminiKey = apiKey.trim() !== '' || usableBackupKeys.length > 0;

    if (apiProvider === 'gemini' && !hasAnyGeminiKey) {
      throw new Error("Gemini API 키를 먼저 입력해주세요.");
    }
    if (apiProvider === 'openrouter' && !apiKey.trim()) {
      throw new Error("OpenRouter API 키를 먼저 입력해주세요.");
    }
    if (apiProvider === 'vertex' && !providerConfig.trim()) {
      throw new Error("Vertex 서비스 계정 JSON을 입력해주세요.");
    }

    setIsAnalyzing(true);
    setError(null);

    const result: FileAnalysisResult = {
      styleData: null,
      glossaryData: [],
      error: null
    };

    try {
      // Analyze Style
      const styleFormData = new FormData();
      styleFormData.append('file', file);
      styleFormData.append('model_name', selectedStyleModel || selectedModel);
      styleFormData.append('api_provider', apiProvider);
      if (apiProvider === 'vertex') {
        styleFormData.append('api_key', '');
        styleFormData.append('provider_config', providerConfig);
      } else {
        styleFormData.append('api_key', apiKey.trim());
        if (apiProvider === 'gemini') {
          if (usableBackupKeys.length > 0) {
            styleFormData.append('backup_api_keys', JSON.stringify(usableBackupKeys));
          }
          if (requestsPerMinute && requestsPerMinute > 0) {
            styleFormData.append('requests_per_minute', requestsPerMinute.toString());
          }
        }
      }

      const styleResponse = await fetch(`${apiUrl}/api/v1/analysis/style`, {
        method: 'POST',
        body: styleFormData,
      });

      if (!styleResponse.ok) {
        const errorData = await styleResponse.json();
        throw new Error(errorData.detail || '스타일 분석에 실패했습니다.');
      }

      const apiStyleData = await styleResponse.json() as StyleAnalysisResponse;
      
      // Convert API response to UI StyleData format
      result.styleData = {
        protagonist_name: apiStyleData.protagonist_name,
        narration_style: {
          ending_style: apiStyleData.narration_style_endings
        },
        core_tone_keywords: apiStyleData.tone_keywords?.split(',').map(s => s.trim()).filter(s => s) || [],
        golden_rule: apiStyleData.stylistic_rule
      };

      // Analyze Glossary if enabled
      if (analyzeGlossary) {
        setIsAnalyzingGlossary(true);
        const glossaryFormData = new FormData();
        glossaryFormData.append('file', file);
        glossaryFormData.append('model_name', selectedGlossaryModel || selectedModel);
        glossaryFormData.append('api_provider', apiProvider);
        if (apiProvider === 'vertex') {
          glossaryFormData.append('api_key', '');
          glossaryFormData.append('provider_config', providerConfig);
        } else {
          glossaryFormData.append('api_key', apiKey.trim());
          if (apiProvider === 'gemini') {
            if (usableBackupKeys.length > 0) {
              glossaryFormData.append('backup_api_keys', JSON.stringify(usableBackupKeys));
            }
            if (requestsPerMinute && requestsPerMinute > 0) {
              glossaryFormData.append('requests_per_minute', requestsPerMinute.toString());
            }
          }
        }

        try {
          const glossaryResponse = await fetch(`${apiUrl}/api/v1/analysis/glossary`, {
            method: 'POST',
            body: glossaryFormData,
          });

          if (glossaryResponse.ok) {
            const glossaryResult = await glossaryResponse.json() as GlossaryAnalysisResponse;
            // Convert API glossary format to UI GlossaryTerm format
            result.glossaryData = (glossaryResult.glossary || []).map((item: any) => {
              return { 
                source: item.term || '', 
                korean: item.translation || '' 
              };
            });
          } else {
            const errorData = await glossaryResponse.json();
            console.warn('Glossary analysis failed:', errorData.detail);
          }
        } catch (err) {
          console.warn('Glossary analysis error:', err);
        } finally {
          setIsAnalyzingGlossary(false);
        }
      }

      return result;
    } catch (err) {
      result.error = err instanceof Error ? err.message : "알 수 없는 오류가 발생했습니다.";
      throw err;
    } finally {
      setIsAnalyzing(false);
    }
  }, [
    apiUrl,
    apiProvider,
    apiKey,
    backupApiKeys,
    requestsPerMinute,
    providerConfig,
    selectedModel,
    selectedStyleModel,
    selectedGlossaryModel,
    isLoaded,
    isSignedIn,
    openSignIn,
  ]);

  const startTranslation = useCallback(async (
    file: File,
    styleData: StyleData,
    glossaryData: GlossaryTerm[],
    settings: TranslationSettings
  ): Promise<void> => {
    if (!isLoaded) {
      throw new Error("인증 정보를 불러오는 중입니다. 잠시 후 다시 시도해주세요.");
    }

    if (!isSignedIn) {
      openSignIn({ redirectUrl: '/' });
      throw new Error("번역을 시작하려면 먼저 로그인해주세요.");
    }
    const usableBackupKeys = (backupApiKeys || []).map((k) => (k || '').trim()).filter((k) => k);
    const hasAnyGeminiKey = apiKey.trim() !== '' || usableBackupKeys.length > 0;

    if (apiProvider === 'gemini' && !hasAnyGeminiKey) {
      throw new Error("Gemini API 키를 먼저 입력해주세요.");
    }
    if (apiProvider === 'openrouter' && !apiKey.trim()) {
      throw new Error("OpenRouter API 키를 먼저 입력해주세요.");
    }
    if (apiProvider === 'vertex' && !providerConfig.trim()) {
      throw new Error("Vertex 서비스 계정 JSON을 입력해주세요.");
    }

    setUploading(true);
    setError(null);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("model_name", selectedModel);
    if (
      settings.thinkingLevel
      && (apiProvider === 'gemini' || apiProvider === 'vertex')
      && (selectedModel.includes('gemini-3-flash') || selectedModel.includes('gemini-3-pro'))
    ) {
      formData.append("thinking_level", settings.thinkingLevel);
    }
    formData.append("api_provider", apiProvider);
    if (apiProvider === 'vertex') {
      formData.append("api_key", '');
      formData.append("provider_config", providerConfig);
    } else {
      formData.append("api_key", apiKey.trim());
      if (apiProvider === 'gemini') {
        if (usableBackupKeys.length > 0) {
          formData.append("backup_api_keys", JSON.stringify(usableBackupKeys));
        }
        if (requestsPerMinute && requestsPerMinute > 0) {
          formData.append("requests_per_minute", requestsPerMinute.toString());
        }
      }
    }
    if (selectedStyleModel && selectedStyleModel !== selectedModel) {
      formData.append("style_model_name", selectedStyleModel);
    }
    if (selectedGlossaryModel && selectedGlossaryModel !== selectedModel) {
      formData.append("glossary_model_name", selectedGlossaryModel);
    }
    // Convert UI StyleData format to API format
    const apiStyleData = {
      protagonist_name: styleData.protagonist_name || '',
      narration_style_endings: styleData.narration_style?.ending_style || '',
      tone_keywords: styleData.core_tone_keywords?.join(', ') || '',
      stylistic_rule: styleData.golden_rule || ''
    };
    formData.append("style_data", JSON.stringify(apiStyleData));
    
    if (glossaryData.length > 0) {
      // Convert UI GlossaryTerm format to API format - single dictionary
      const apiGlossaryData: Record<string, string> = {};
      glossaryData.forEach(term => {
        if (term.source && term.korean) {
          apiGlossaryData[term.source] = term.korean;
        }
      });
      formData.append("glossary_data", JSON.stringify(apiGlossaryData));
    }
    
    formData.append("segment_size", settings.segmentSize.toString());
    if (settings.turboMode) {
      formData.append("turbo_mode", "true");
    }
    
    // Add validation settings if enabled
    if (settings.enableValidation) {
      formData.append("enable_validation", "true");
      formData.append("quick_validation", settings.quickValidation.toString());
      formData.append("validation_sample_rate", (settings.validationSampleRate / 100).toString());
      if (settings.enablePostEdit) {
        formData.append("enable_post_edit", "true");
      }
    }

      try {
      const token = await getCachedClerkToken(getToken);
      if (!token) {
        throw new Error("로그인은 되었으나, 인증 토큰을 가져오지 못했습니다.");
      }
      
      const response = await fetch(`${apiUrl}/api/v1/jobs`, { 
        method: 'POST', 
        headers: { 
          'Authorization': `Bearer ${token}`
        },
        body: formData 
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: response.statusText }));
        if (response.status === 401) {
          throw new Error("인증에 실패했습니다. 다시 로그인해주세요.");
        }
        throw new Error(errorData.detail || `File upload failed: ${response.statusText}`);
      }
      
      const newJob: TranslationJob = await response.json();
      onJobCreated?.(newJob);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "An unknown error occurred.";
      setError(errorMessage);
      throw err;
    } finally {
      setUploading(false);
    }
  }, [
    apiUrl,
    apiProvider,
    apiKey,
    backupApiKeys,
    requestsPerMinute,
    providerConfig,
    selectedModel,
    selectedStyleModel,
    selectedGlossaryModel,
    isLoaded,
    isSignedIn,
    getToken,
    openSignIn,
    onJobCreated,
  ]);

  return {
    analyzeFile,
    startTranslation,
    isAnalyzing,
    isAnalyzingGlossary,
    uploading,
    error,
    setError,
  };
}
