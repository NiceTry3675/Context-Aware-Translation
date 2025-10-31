import { useState, useEffect } from 'react';
import { useAuth } from '@clerk/nextjs';
import { getDefaultModel, getPreferredDefaultModel, vertexModelOptions } from '../utils/constants/models';
import { getCachedClerkToken } from '../utils/authToken';

export type ApiProvider = 'gemini' | 'vertex' | 'openrouter';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const STORAGE_KEYS = {
  provider: 'apiProvider',
  credentials: {
    gemini: 'geminiApiKey',
    vertex: 'vertexProviderConfig',
    openrouter: 'openrouterApiKey',
  },
  model: {
    gemini: 'geminiModel',
    vertex: 'vertexModel',
    openrouter: 'openRouterModel',
  },
} as const;

export function useApiKey() {
  const { getToken, isSignedIn } = useAuth();
  const [apiKey, setApiKeyState] = useState<string>('');
  const [providerConfig, setProviderConfigState] = useState<string>('');
  const [apiProvider, setApiProvider] = useState<ApiProvider>('gemini');
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [isInitialized, setIsInitialized] = useState(false);

  useEffect(() => {
    const initializeApiConfig = async () => {
      // First, try to load from backend if user is signed in
      let backendConfig: any = null;
      if (isSignedIn) {
        try {
          const token = await getCachedClerkToken(getToken);
          if (token) {
            const response = await fetch(`${API_BASE_URL}/api/v1/users/me/api-config`, {
              headers: {
                Authorization: `Bearer ${token}`,
              },
            });
            if (response.ok) {
              backendConfig = await response.json();
            }
          }
        } catch (error) {
          console.warn('Failed to fetch API config from backend:', error);
        }
      }

      // If backend config exists, use it; otherwise fall back to localStorage
      const storedProvider =
        backendConfig?.api_provider ||
        (localStorage.getItem(STORAGE_KEYS.provider) as ApiProvider | null) ||
        'gemini';

      setApiProvider(storedProvider);

      if (storedProvider === 'vertex') {
        const vertexConfig =
          backendConfig?.provider_config ??
          localStorage.getItem(STORAGE_KEYS.credentials.vertex) ??
          '';
        setProviderConfigState(vertexConfig);
        setApiKeyState('');
      } else {
        const localKey =
          localStorage.getItem(STORAGE_KEYS.credentials[storedProvider]) ?? '';
        const apiKey = backendConfig?.api_key ?? localKey;
        setApiKeyState(apiKey);
        setProviderConfigState('');
      }

      // Determine model
      let modelFromBackend = '';
      if (backendConfig) {
        if (storedProvider === 'gemini') modelFromBackend = backendConfig.gemini_model || '';
        else if (storedProvider === 'vertex') modelFromBackend = backendConfig.vertex_model || '';
        else if (storedProvider === 'openrouter') modelFromBackend = backendConfig.openrouter_model || '';
      }

      const storedModel = modelFromBackend || localStorage.getItem(STORAGE_KEYS.model[storedProvider]);
      const preferredModel = getPreferredDefaultModel(storedProvider);
      const defaultModel = getDefaultModel(storedProvider);
      let normalizedModel = storedModel || preferredModel || defaultModel;

      if (storedProvider === 'vertex' && !vertexModelOptions.some((opt) => opt.value === normalizedModel)) {
        normalizedModel = defaultModel;
      }

      if (!storedModel && normalizedModel) {
        localStorage.setItem(STORAGE_KEYS.model[storedProvider], normalizedModel);
      } else if (storedModel && normalizedModel !== storedModel && storedProvider === 'vertex') {
        localStorage.setItem(STORAGE_KEYS.model.vertex, normalizedModel);
      }

      setSelectedModel(normalizedModel);
      setIsInitialized(true);
    };

    void initializeApiConfig();
  }, [getToken, isSignedIn]);

  const persistModel = (provider: ApiProvider, model: string) => {
    localStorage.setItem(STORAGE_KEYS.model[provider], model);
  };

  const handleModelChange = (newModel: string) => {
    setSelectedModel(newModel);
    if (isInitialized) {
      persistModel(apiProvider, newModel);
    }
  };

  const handleProviderChange = (newProvider: ApiProvider) => {
    if (!newProvider || newProvider === apiProvider) return;

    setApiProvider(newProvider);
    localStorage.setItem(STORAGE_KEYS.provider, newProvider);

    const storedModel = localStorage.getItem(STORAGE_KEYS.model[newProvider]);
    const preferredModel = getPreferredDefaultModel(newProvider);
    const defaultModel = getDefaultModel(newProvider);
    let normalizedModel = storedModel || preferredModel || defaultModel;

    if (newProvider === 'vertex' && !vertexModelOptions.some((opt) => opt.value === normalizedModel)) {
      normalizedModel = getDefaultModel('vertex');
    }

    if (!storedModel && normalizedModel) {
      localStorage.setItem(STORAGE_KEYS.model[newProvider], normalizedModel);
    } else if (storedModel && normalizedModel !== storedModel && newProvider === 'vertex') {
      localStorage.setItem(STORAGE_KEYS.model.vertex, normalizedModel);
    }

    setSelectedModel(normalizedModel);

    if (newProvider === 'vertex') {
      const storedConfig = localStorage.getItem(STORAGE_KEYS.credentials.vertex) || '';
      setProviderConfigState(storedConfig);
      setApiKeyState('');
    } else if (newProvider === 'openrouter') {
      const storedApiKey = localStorage.getItem(STORAGE_KEYS.credentials.openrouter) || '';
      setApiKeyState(storedApiKey);
      setProviderConfigState('');
    } else {
      const storedApiKey = localStorage.getItem(STORAGE_KEYS.credentials.gemini) || '';
      setApiKeyState(storedApiKey);
      setProviderConfigState('');
    }
  };

  const handleApiKeyChange = (value: string) => {
    setApiKeyState(value);
    if (!isInitialized) return;

    if (apiProvider === 'gemini') {
      localStorage.setItem(STORAGE_KEYS.credentials.gemini, value);
    } else if (apiProvider === 'openrouter') {
      localStorage.setItem(STORAGE_KEYS.credentials.openrouter, value);
    }
  };

  const handleProviderConfigChange = (value: string) => {
    setProviderConfigState(value);
    if (!isInitialized) return;

    if (apiProvider === 'vertex') {
      localStorage.setItem(STORAGE_KEYS.credentials.vertex, value);
    }
  };

  const clearCredentials = () => {
    setApiKeyState('');
    setProviderConfigState('');
    Object.values(STORAGE_KEYS.credentials).forEach((key) => localStorage.removeItem(key));
    Object.values(STORAGE_KEYS.model).forEach((key) => localStorage.removeItem(key));
    localStorage.removeItem(STORAGE_KEYS.provider);
  };

  return {
    apiKey,
    setApiKey: handleApiKeyChange,
    providerConfig,
    setProviderConfig: handleProviderConfigChange,
    apiProvider,
    setApiProvider: handleProviderChange,
    selectedModel,
    setSelectedModel: handleModelChange,
    clearCredentials,
  };
}
