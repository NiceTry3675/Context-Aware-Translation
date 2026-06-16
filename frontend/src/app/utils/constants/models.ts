export interface ModelOption {
  value: string;
  label: string;
  description: string;
  chip: string;
  chipColor: "primary" | "success" | "info" | "error" | "warning";
}

export const geminiModelOptions: ModelOption[] = [
  {
    value: "gemini-flash-lite-latest",
    label: "Flash Lite",
    description: "가장 빠른 속도와 저렴한 비용으로 빠르게 결과물을 확인하고 싶을 때 적합합니다.",
    chip: "속도",
    chipColor: "primary",
  },
  {
    value: "gemini-flash-latest",
    label: "Flash",
    description: "준수한 품질과 합리적인 속도의 균형을 원할 때 가장 이상적인 선택입니다.",
    chip: "균형",
    chipColor: "info",
  },
  {
    value: "gemini-pro-latest",
    label: "Pro",
    description: "최신 Gemini 3 Pro 모델입니다. 최고 수준의 문학적 번역 품질을 원하신다면 선택하세요.(느리고 비쌀 수 있음)",
    chip: "품질",
    chipColor: "error",
  },
];

export const openRouterModelOptions: ModelOption[] = [
  {
    value: "google/gemini-3.1-flash-lite",
    label: "Flash Lite",
    description: " ",
    chip: "속도",
    chipColor: "primary",
  },
  {
    value: "google/gemini-3.5-flash",
    label: "Flash",
    description: " ",
    chip: "균형",
    chipColor: "success",
  },
  {
    value: "google/gemini-3.1-pro-preview",
    label: "Pro",
    description: " ",
    chip: "품질",
    chipColor: "info",
  },
  {
    value: "openai/gpt-4o",
    label: "GPT-4o",
    description: " ",
    chip: "품질",
    chipColor: "warning",
  },
  {
    value: "openai/gpt-5.2",
    label: "GPT-5.2",
    description: " ",
    chip: "품질",
    chipColor: "error",
  },
  {
    value: "openai/gpt-5.2-chat",
    label: "GPT-5.2 Chat",
    description: " ",
    chip: "품질",
    chipColor: "error",
  },
  {
    value: "anthropic/claude-sonnet-4",
    label: "Claude Sonnet 4",
    description: " ",
    chip: "품질",
    chipColor: "info",
  },
  {
    value: "openai/gpt-4.1",
    label: "GPT-4.1",
    description: " ",
    chip: "속도",
    chipColor: "success",
  },
  {
    value: "x-ai/grok-4",
    label: "Grok-4",
    description: " ",
    chip: "품질",
    chipColor: "success",
  },
  {
    value: "x-ai/grok-4-fast",
    label: "Grok-4 Fast",
    description: " ",
    chip: "속도",
    chipColor: "success",
  },
  {
    value: "qwen/qwen3-235b-a22b:free",
    label: "Qwen3 235B A22B (무료)",
    description: " ",
    chip: "품질",
    chipColor: "success",
  },
  {
    value: "tngtech/deepseek-r1t2-chimera:free",
    label: "DeepSeek R1 T2 Chimera (무료)",
    description: " ",
    chip: "속도",
    chipColor: "success",
  },
  {
    value: "deepseek/deepseek-r1-0528:free",
    label: "DeepSeek R1 (무료)",
    description: " ",
    chip: "품질",
    chipColor: "success",
  },
];

export const vertexModelOptions: ModelOption[] = [
  {
    value: "gemini-3.1-flash-lite",
    label: "Flash Lite",
    description: "가장 저렴한 Vertex Gemini 옵션으로 빠른 번역과 검수를 위한 선택입니다.",
    chip: "속도",
    chipColor: "primary",
  },
  {
    value: "gemini-3.5-flash",
    label: "Flash",
    description: "품질과 속도의 균형이 좋은 Vertex Gemini 기본 모델입니다.",
    chip: "균형",
    chipColor: "info",
  },
  {
    value: "gemini-3.1-pro-preview",
    label: "Pro",
    description: "최신 Gemini 3 Pro 모델입니다. 최고 수준의 문학적 번역 품질을 원하신다면 선택하세요.(느리고 비쌀 수 있음)",
    chip: "품질",
    chipColor: "error",
  },
];

export const isOpenRouterGeminiModel = (model: string): boolean => model.startsWith('google/gemini');

export const openRouterGeminiModelOptions: ModelOption[] = openRouterModelOptions.filter((opt) =>
  isOpenRouterGeminiModel(opt.value)
);

export const getDefaultOpenRouterGeminiModel = (): string => {
  const preferred = openRouterGeminiModelOptions.find((opt) => opt.value === 'google/gemini-3.5-flash')?.value
    ?? openRouterGeminiModelOptions[0]?.value
    ?? openRouterModelOptions.find((opt) => isOpenRouterGeminiModel(opt.value))?.value
    ?? 'google/gemini-3.5-flash';
  return preferred;
};

export const ensureOpenRouterGeminiModel = (model?: string | null): string => {
  if (model && isOpenRouterGeminiModel(model)) {
    return model;
  }
  return getDefaultOpenRouterGeminiModel();
};

export function getPreferredDefaultModel(apiProvider: 'gemini' | 'vertex' | 'openrouter'): string {
  switch (apiProvider) {
    case 'openrouter':
      return 'google/gemini-3.5-flash';
    case 'vertex':
      return 'gemini-3.5-flash';
    case 'gemini':
    default:
      return 'gemini-flash-latest';
  }
}

export function getDefaultModel(apiProvider: 'gemini' | 'vertex' | 'openrouter'): string {
  switch (apiProvider) {
    case 'openrouter':
      return getDefaultOpenRouterGeminiModel();
    case 'vertex':
      return 'gemini-3.5-flash';
    case 'gemini':
    default:
      return 'gemini-flash-latest';
  }
}

export type GeminiThinkingLevel = 'minimal' | 'low' | 'medium' | 'high';

const shortModelName = (model: string): string => {
  const trimmed = (model || '').trim().toLowerCase();
  const parts = trimmed.split('/');
  return parts[parts.length - 1] || trimmed;
};

export const getAllowedThinkingLevels = (model: string): readonly GeminiThinkingLevel[] | null => {
  const short = shortModelName(model);
  if (
    short === 'gemini-flash-latest'
    || short === 'gemini-flash-lite-latest'
    || short === 'gemini-3.5-flash'
    || short === 'gemini-3.1-flash-lite'
    || short === 'gemini-3-flash-preview'
  ) {
    return ['minimal', 'low', 'medium', 'high'] as const;
  }
  if (
    short === 'gemini-pro-latest'
    || short === 'gemini-3.1-pro-preview'
    || short === 'gemini-3-pro-preview'
  ) {
    return ['low', 'medium', 'high'] as const;
  }
  return null;
};

export const getModelOptionsForProvider = (apiProvider: 'gemini' | 'vertex' | 'openrouter'): ModelOption[] => {
  switch (apiProvider) {
    case 'openrouter':
      return openRouterModelOptions;
    case 'vertex':
      return vertexModelOptions;
    case 'gemini':
    default:
      return geminiModelOptions;
  }
};
