import { useState, useEffect } from 'react';
import { getDefaultModel } from '../utils/constants/models';

type ApiProvider = 'gemini' | 'openrouter';
type TaskKey = 'translate' | 'style' | 'glossary' | 'validation' | 'postedit';

export function useApiKey() {
  const [apiKey, setApiKey] = useState<string>('');
  const [apiProvider, setApiProvider] = useState<ApiProvider>('gemini');
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [useAdvancedTaskModels, setUseAdvancedTaskModels] = useState<boolean>(false);
  const [taskModels, setTaskModels] = useState<Record<TaskKey, string>>({
    translate: '',
    style: '',
    glossary: '',
    validation: '',
    postedit: ''
  });
  const [isInitialized, setIsInitialized] = useState(false);

  // Load from localStorage on mount
  useEffect(() => {
    const storedApiKey = localStorage.getItem('geminiApiKey');
    const storedProvider = localStorage.getItem('apiProvider') as ApiProvider | null;
    const storedAdvanced = localStorage.getItem('useAdvancedTaskModels');
    
    if (storedApiKey) {
      const provider = storedProvider || (storedApiKey.startsWith('sk-or-') ? 'openrouter' : 'gemini');
      setApiProvider(provider);
      setApiKey(storedApiKey);
      setUseAdvancedTaskModels(storedAdvanced === 'true');

      if (provider === 'openrouter') {
        const main = localStorage.getItem('openRouterModel') || getDefaultModel('openrouter');
        setSelectedModel(main);
        // Load task-specific models (fallback to main)
        try {
          const raw = localStorage.getItem('taskModels');
          if (raw) {
            const parsed = JSON.parse(raw) as Record<string, string>;
            setTaskModels({
              translate: parsed.translate || main,
              style: parsed.style || main,
              glossary: parsed.glossary || main,
              validation: parsed.validation || main,
              postedit: parsed.postedit || main,
            });
          } else {
            setTaskModels({ translate: main, style: main, glossary: main, validation: main, postedit: main });
          }
        } catch {
          setTaskModels({ translate: main, style: main, glossary: main, validation: main, postedit: main });
        }
      } else {
        const main = localStorage.getItem('geminiModel') || getDefaultModel('gemini');
        setSelectedModel(main);
        // Load task-specific models (fallback to main)
        try {
          const raw = localStorage.getItem('taskModels');
          if (raw) {
            const parsed = JSON.parse(raw) as Record<string, string>;
            setTaskModels({
              translate: parsed.translate || main,
              style: parsed.style || main,
              glossary: parsed.glossary || main,
              validation: parsed.validation || main,
              postedit: parsed.postedit || main,
            });
          } else {
            setTaskModels({ translate: main, style: main, glossary: main, validation: main, postedit: main });
          }
        } catch {
          setTaskModels({ translate: main, style: main, glossary: main, validation: main, postedit: main });
        }
      }
    } else {
      const main = getDefaultModel('gemini');
      setSelectedModel(main);
      setTaskModels({ translate: main, style: main, glossary: main, validation: main, postedit: main });
      setUseAdvancedTaskModels(false);
    }
    setIsInitialized(true);
  }, []);

  // Save to localStorage when values change (only after initialization)
  useEffect(() => {
    if (isInitialized && apiKey) {
      localStorage.setItem('geminiApiKey', apiKey);
      localStorage.setItem('apiProvider', apiProvider);
      localStorage.setItem('useAdvancedTaskModels', useAdvancedTaskModels ? 'true' : 'false');
    }
  }, [apiKey, apiProvider, useAdvancedTaskModels, isInitialized]);

  // Update model when provider changes (only after initialization)
  useEffect(() => {
    if (isInitialized) {
      const newModel = getDefaultModel(apiProvider);
      setSelectedModel(newModel);
      localStorage.setItem(apiProvider === 'gemini' ? 'geminiModel' : 'openRouterModel', newModel);
      // Reset task models to provider default on provider change
      const nextTasks = { translate: newModel, style: newModel, glossary: newModel, validation: newModel, postedit: newModel } as Record<TaskKey, string>;
      setTaskModels(nextTasks);
      localStorage.setItem('taskModels', JSON.stringify(nextTasks));
    }
  }, [apiProvider, isInitialized]);

  // When advanced is disabled, keep all tasks unified to the main model
  useEffect(() => {
    if (isInitialized && !useAdvancedTaskModels) {
      const unified = {
        translate: selectedModel,
        style: selectedModel,
        glossary: selectedModel,
        validation: selectedModel,
        postedit: selectedModel,
      } as Record<TaskKey, string>;
      setTaskModels(unified);
      localStorage.setItem('taskModels', JSON.stringify(unified));
    }
  }, [useAdvancedTaskModels, selectedModel, isInitialized]);

  // Handle model change with persistence
  const handleModelChange = (newModel: string) => {
    setSelectedModel(newModel);
    if (apiProvider === 'gemini') {
      localStorage.setItem('geminiModel', newModel);
    } else {
      localStorage.setItem('openRouterModel', newModel);
    }
    // By default, align translate task with main selection
    const updated = { ...taskModels, translate: newModel };
    setTaskModels(updated);
    localStorage.setItem('taskModels', JSON.stringify(updated));
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
    localStorage.removeItem('taskModels');
    localStorage.removeItem('useAdvancedTaskModels');
  };

  // Set a task-specific model
  const setTaskModel = (task: TaskKey, model: string) => {
    const updated = { ...taskModels, [task]: model } as Record<TaskKey, string>;
    setTaskModels(updated);
    localStorage.setItem('taskModels', JSON.stringify(updated));
  };

  return {
    apiKey,
    setApiKey,
    apiProvider,
    setApiProvider: handleProviderChange,
    selectedModel,
    setSelectedModel: handleModelChange,
    taskModels,
    setTaskModel,
    useAdvancedTaskModels,
    setUseAdvancedTaskModels,
    clearApiKey
  };
}
