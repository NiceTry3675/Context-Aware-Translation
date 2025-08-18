import { useState, useCallback } from 'react';
import { useAuth, useClerk } from '@clerk/nextjs';
import { getCachedClerkToken } from '../utils/authToken';
import type { components } from '@/types/api';
import { StyleData, GlossaryTerm, TranslationSettings } from '../types/ui';

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
  apiKey: string;
  selectedModel: string;
  onJobCreated?: (job: TranslationJob) => void;
}

export function useTranslationService({
  apiUrl,
  apiKey,
  selectedModel,
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
    
    if (!apiKey) {
      throw new Error("API 키를 먼저 입력해주세요.");
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
      styleFormData.append('api_key', apiKey);
      styleFormData.append('model_name', selectedModel);

      const styleResponse = await fetch(`${apiUrl}/api/v1/analyze-style`, {
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
        glossaryFormData.append('api_key', apiKey);
        glossaryFormData.append('model_name', selectedModel);

        try {
          const glossaryResponse = await fetch(`${apiUrl}/api/v1/analyze-glossary`, {
            method: 'POST',
            body: glossaryFormData,
          });

          if (glossaryResponse.ok) {
            const glossaryResult = await glossaryResponse.json() as GlossaryAnalysisResponse;
            // Convert API glossary format to UI GlossaryTerm format
            result.glossaryData = (glossaryResult.glossary || []).map(item => {
              const [source, korean] = Object.entries(item)[0] || ['', ''];
              return { source, korean };
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
  }, [apiUrl, apiKey, selectedModel, isLoaded, isSignedIn, openSignIn]);

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

    setUploading(true);
    setError(null);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("api_key", apiKey);
    formData.append("model_name", selectedModel);
    // Convert UI StyleData format to API format
    const apiStyleData = {
      protagonist_name: styleData.protagonist_name || '',
      narration_style_endings: styleData.narration_style?.ending_style || '',
      tone_keywords: styleData.core_tone_keywords?.join(', ') || '',
      stylistic_rule: styleData.golden_rule || ''
    };
    formData.append("style_data", JSON.stringify(apiStyleData));
    
    if (glossaryData.length > 0) {
      // Convert UI GlossaryTerm format to API format
      const apiGlossaryData = glossaryData.map(term => ({
        [term.source]: term.korean
      }));
      formData.append("glossary_data", JSON.stringify(apiGlossaryData));
    }
    
    formData.append("segment_size", settings.segmentSize.toString());
    
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
  }, [apiUrl, apiKey, selectedModel, isLoaded, isSignedIn, getToken, openSignIn, onJobCreated]);

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