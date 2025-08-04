export interface ModelOption {
  value: string;
  label: string;
  description: string;
  chip: string;
  chipColor: "primary" | "success" | "info" | "error" | "warning";
}

export const geminiModelOptions: ModelOption[] = [
  {
    value: "gemini-2.5-flash-lite",
    label: "Flash Lite (추천)",
    description: "가장 빠른 속도와 저렴한 비용으로 빠르게 결과물을 확인하고 싶을 때 적합합니다.",
    chip: "속도",
    chipColor: "primary",
  },
  {
    value: "gemini-2.5-flash",
    label: "Flash",
    description: "준수한 품질과 합리적인 속도의 균형을 원할 때 가장 이상적인 선택입니다.",
    chip: "균형",
    chipColor: "info",
  },
  {
    value: "gemini-2.5-pro",
    label: "Pro",
    description: "최고 수준의 문학적 번역 품질을 원하신다면 선택하세요. (느리고 비쌀 수 있음)",
    chip: "품질",
    chipColor: "error",
  },
];

export const openRouterModelOptions: ModelOption[] = [
  {
    value: "google/gemini-2.5-flash-lite",
    label: "Gemini 2.5 Flash Lite",
    description: " ",
    chip: "속도",
    chipColor: "primary",
  },
  {
    value: "google/gemini-2.5-flash",
    label: "Gemini 2.5 Flash",
    description: " ",
    chip: "균형",
    chipColor: "success",
  },
  {
    value: "google/gemini-2.5-pro",
    label: "Gemini 2.5 Pro",
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

export function getDefaultModel(apiProvider: 'gemini' | 'openrouter'): string {
  return apiProvider === 'gemini' ? geminiModelOptions[0].value : openRouterModelOptions[0].value;
}