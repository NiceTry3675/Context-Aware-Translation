import { useState, useEffect } from 'react';
import { getDefaultModel } from '../utils/constants/models';

export type ApiProvider = 'gemini' | 'vertex' | 'openrouter';

const MODEL_STORAGE_KEYS: Record<ApiProvider, string> = {
  gemini: 'geminiModel',
  vertex: 'vertexModel',
  openrouter: 'openRouterModel'
};

const CREDENTIAL_STORAGE_KEYS: Record<ApiProvider, string> = {
  gemini: 'geminiApiKey',
  vertex: 'vertexServiceAccount',
  openrouter: 'openrouterApiKey'
};

function resolveInitialProvider(
  storedProvider: string | null,
  credentials: Record<ApiProvider, string>
): ApiProvider {
  if (storedProvider && ['gemini', 'vertex', 'openrouter'].includes(storedProvider)) {
    return storedProvider as ApiProvider;
  }
  if (credentials.openrouter) {
    return 'openrouter';
  }
  if (credentials.vertex) {
    return 'vertex';
  }
  return 'gemini';
}

export function useApiKey() {
  const [credentials, setCredentials] = useState<Record<ApiProvider, string>>({
    gemini: '',
    vertex: '',
    openrouter: ''
  });
  const [apiProvider, setApiProvider] = useState<ApiProvider>('gemini');
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [vertexProjectId, setVertexProjectId] = useState<string>('');
  const [vertexLocation, setVertexLocation] = useState<string>('us-central1');
  const [isInitialized, setIsInitialized] = useState(false);

  // Load from localStorage on mount
  useEffect(() => {
    const storedGemini = localStorage.getItem(CREDENTIAL_STORAGE_KEYS.gemini) || '';
    const storedOpenRouter = localStorage.getItem(CREDENTIAL_STORAGE_KEYS.openrouter) || '';
    const storedVertex = localStorage.getItem(CREDENTIAL_STORAGE_KEYS.vertex) || '';

    let geminiKey = storedGemini;
    let openRouterKey = storedOpenRouter;

    // Migrate legacy OpenRouter keys that were stored in geminiApiKey
    if (!openRouterKey && geminiKey && geminiKey.startsWith('sk-or-')) {
      openRouterKey = geminiKey;
      geminiKey = '';
      localStorage.setItem(CREDENTIAL_STORAGE_KEYS.openrouter, openRouterKey);
    }

    const initialCredentials: Record<ApiProvider, string> = {
      gemini: geminiKey,
      vertex: storedVertex,
      openrouter: openRouterKey
    };

    setCredentials(initialCredentials);

    const storedProvider = localStorage.getItem('apiProvider');
    const resolvedProvider = resolveInitialProvider(storedProvider, initialCredentials);
    setApiProvider(resolvedProvider);

    const storedVertexProjectId = localStorage.getItem('vertexProjectId') || '';
    const storedVertexLocation = localStorage.getItem('vertexLocation') || '';
    if (storedVertexProjectId) {
      setVertexProjectId(storedVertexProjectId);
    }
    if (storedVertexLocation) {
      setVertexLocation(storedVertexLocation);
    }

    const storedModel = localStorage.getItem(MODEL_STORAGE_KEYS[resolvedProvider]);
    const initialModel = storedModel || getDefaultModel(resolvedProvider);
    setSelectedModel(initialModel);
    if (!storedModel) {
      localStorage.setItem(MODEL_STORAGE_KEYS[resolvedProvider], initialModel);
    }

    setIsInitialized(true);
  }, []);

  const apiKey = credentials[apiProvider] || '';

  // Persist provider selection once initialized
  useEffect(() => {
    if (isInitialized) {
      localStorage.setItem('apiProvider', apiProvider);
    }
  }, [apiProvider, isInitialized]);

  // Persist vertex project/location when updated
  useEffect(() => {
    if (isInitialized) {
      localStorage.setItem('vertexProjectId', vertexProjectId || '');
    }
  }, [vertexProjectId, isInitialized]);

  useEffect(() => {
    if (isInitialized) {
      localStorage.setItem('vertexLocation', vertexLocation || '');
    }
  }, [vertexLocation, isInitialized]);

  // Update selected model when provider changes (after initialization)
  useEffect(() => {
    if (!isInitialized) return;
    const storageKey = MODEL_STORAGE_KEYS[apiProvider];
    const storedModel = localStorage.getItem(storageKey);
    const newModel = storedModel || getDefaultModel(apiProvider);
    setSelectedModel(newModel);
    if (!storedModel) {
      localStorage.setItem(storageKey, newModel);
    }
  }, [apiProvider, isInitialized]);

  // Handle model change with persistence
  const handleModelChange = (newModel: string) => {
    setSelectedModel(newModel);
    const storageKey = MODEL_STORAGE_KEYS[apiProvider];
    localStorage.setItem(storageKey, newModel);
  };

  // Handle provider change
  const handleProviderChange = (newProvider: ApiProvider) => {
    if (newProvider) {
      setApiProvider(newProvider);
    }
  };

  // Handle API/service account update for current provider
  const handleApiKeyChange = (value: string) => {
    setCredentials(prev => {
      const next = { ...prev, [apiProvider]: value };
      localStorage.setItem(CREDENTIAL_STORAGE_KEYS[apiProvider], value);
      return next;
    });
  };

  // Clear credentials and selections
  const clearApiKey = () => {
    setCredentials({ gemini: '', vertex: '', openrouter: '' });
    setVertexProjectId('');
    setVertexLocation('us-central1');
    localStorage.removeItem('apiProvider');
    localStorage.removeItem(CREDENTIAL_STORAGE_KEYS.gemini);
    localStorage.removeItem(CREDENTIAL_STORAGE_KEYS.vertex);
    localStorage.removeItem(CREDENTIAL_STORAGE_KEYS.openrouter);
    localStorage.removeItem('vertexProjectId');
    localStorage.removeItem('vertexLocation');
    localStorage.removeItem(MODEL_STORAGE_KEYS.gemini);
    localStorage.removeItem(MODEL_STORAGE_KEYS.vertex);
    localStorage.removeItem(MODEL_STORAGE_KEYS.openrouter);
  };

  return {
    apiKey,
    setApiKey: handleApiKeyChange,
    apiProvider,
    setApiProvider: handleProviderChange,
    selectedModel,
    setSelectedModel: handleModelChange,
    vertexProjectId,
    setVertexProjectId,
    vertexLocation,
    setVertexLocation,
    clearApiKey
  };
}
