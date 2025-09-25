import { useState, useEffect } from 'react';
import { getDefaultModel, getPreferredDefaultModel, vertexModelOptions } from '../utils/constants/models';

export type ApiProvider = 'gemini' | 'vertex' | 'openrouter';

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
  const [apiKey, setApiKeyState] = useState<string>('');
  const [providerConfig, setProviderConfigState] = useState<string>('');
  const [apiProvider, setApiProvider] = useState<ApiProvider>('gemini');
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [isInitialized, setIsInitialized] = useState(false);

  useEffect(() => {
    const storedProvider = (localStorage.getItem(STORAGE_KEYS.provider) as ApiProvider | null) || 'gemini';
    const geminiApiKey = localStorage.getItem(STORAGE_KEYS.credentials.gemini) || '';
    const openrouterApiKey = localStorage.getItem(STORAGE_KEYS.credentials.openrouter) || '';
    const vertexConfig = localStorage.getItem(STORAGE_KEYS.credentials.vertex) || '';

    setApiProvider(storedProvider);
    if (storedProvider === 'vertex') {
      setProviderConfigState(vertexConfig);
      setApiKeyState('');
    } else if (storedProvider === 'openrouter') {
      setApiKeyState(openrouterApiKey);
      setProviderConfigState('');
    } else {
      setApiKeyState(geminiApiKey);
      setProviderConfigState('');
    }

    const storedModel = localStorage.getItem(STORAGE_KEYS.model[storedProvider]);
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
  }, []);

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
