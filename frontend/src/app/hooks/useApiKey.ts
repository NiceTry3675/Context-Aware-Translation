import { useState, useEffect } from 'react';
import { getDefaultModel } from '../utils/constants/models';

type ApiProvider = 'gemini' | 'openrouter';

export function useApiKey() {
  const [apiKey, setApiKey] = useState<string>('');
  const [apiProvider, setApiProvider] = useState<ApiProvider>('gemini');
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [isInitialized, setIsInitialized] = useState(false);

  // Load from localStorage on mount
  useEffect(() => {
    const storedApiKey = localStorage.getItem('geminiApiKey');
    const storedProvider = localStorage.getItem('apiProvider') as ApiProvider | null;
    
    if (storedApiKey) {
      const provider = storedProvider || (storedApiKey.startsWith('sk-or-') ? 'openrouter' : 'gemini');
      setApiProvider(provider);
      setApiKey(storedApiKey);

      if (provider === 'openrouter') {
        setSelectedModel(localStorage.getItem('openRouterModel') || getDefaultModel('openrouter'));
      } else {
        setSelectedModel(localStorage.getItem('geminiModel') || getDefaultModel('gemini'));
      }
    } else {
      setSelectedModel(getDefaultModel('gemini'));
    }
    setIsInitialized(true);
  }, []);

  // Save to localStorage when values change (only after initialization)
  useEffect(() => {
    if (isInitialized && apiKey) {
      localStorage.setItem('geminiApiKey', apiKey);
      localStorage.setItem('apiProvider', apiProvider);
    }
  }, [apiKey, apiProvider, isInitialized]);

  // Update model when provider changes (only after initialization)
  useEffect(() => {
    if (isInitialized) {
      const newModel = getDefaultModel(apiProvider);
      setSelectedModel(newModel);
      localStorage.setItem(apiProvider === 'gemini' ? 'geminiModel' : 'openRouterModel', newModel);
    }
  }, [apiProvider, isInitialized]);

  // Handle model change with persistence
  const handleModelChange = (newModel: string) => {
    setSelectedModel(newModel);
    if (apiProvider === 'gemini') {
      localStorage.setItem('geminiModel', newModel);
    } else {
      localStorage.setItem('openRouterModel', newModel);
    }
  };

  // Handle provider change
  const handleProviderChange = (newProvider: ApiProvider) => {
    if (newProvider) {
      setApiProvider(newProvider);
    }
  };

  // Clear API key
  const clearApiKey = () => {
    setApiKey('');
    localStorage.removeItem('geminiApiKey');
    localStorage.removeItem('apiProvider');
    localStorage.removeItem('geminiModel');
    localStorage.removeItem('openRouterModel');
  };

  return {
    apiKey,
    setApiKey,
    apiProvider,
    setApiProvider: handleProviderChange,
    selectedModel,
    setSelectedModel: handleModelChange,
    clearApiKey
  };
}