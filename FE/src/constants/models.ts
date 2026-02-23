export interface ModelOption {
  provider: 'ollama' | 'openrouter' | 'anthropic';
  modelName: string;
  displayName: string;
}

export const AVAILABLE_MODELS: ModelOption[] = [
  { provider: 'anthropic', modelName: 'claude-opus-4-6', displayName: 'Claude Opus 4.6' },
  { provider: 'anthropic', modelName: 'claude-sonnet-4-6', displayName: 'Claude Sonnet 4.6' },
  { provider: 'anthropic', modelName: 'claude-haiku-4-5-20251001', displayName: 'Claude Haiku 4.5' },
  { provider: 'openrouter', modelName: 'qwen/qwen3-vl-235b-a22b-thinking', displayName: 'Qwen 3 VL 235B Thinking' },
  { provider: 'openrouter', modelName: 'arcee-ai/trinity-large-preview:free', displayName: 'Trinity Large Preview' },
  { provider: 'openrouter', modelName: 'stepfun/step-3.5-flash:free', displayName: 'StepFun 3.5 Flash' },
  { provider: 'openrouter', modelName: 'z-ai/glm-4.5-air:free', displayName: 'GLM 4.5 Air' },
  { provider: 'ollama', modelName: 'llama3.1:8b', displayName: 'Llama 3.1 8B' },
  { provider: 'ollama', modelName: 'kimi-k2.5:cloud', displayName: 'Kimi K2.5 Cloud' },
  { provider: 'ollama', modelName: 'qwen3.5:cloud', displayName: 'Qwen 3.5 Cloud' },
  { provider: 'ollama', modelName: 'glm-5:cloud', displayName: 'GLM 5 Cloud' },
  { provider: 'ollama', modelName: 'minimax-m2.5:cloud', displayName: 'Minimax M2.5 Cloud' },
];

export const PROVIDER_LABELS: Record<string, string> = {
  anthropic: 'Anthropic',
  openrouter: 'OpenRouter',
  ollama: 'Ollama',
};

export const MODELS_BY_PROVIDER: Record<string, ModelOption[]> = AVAILABLE_MODELS.reduce(
  (acc, model) => {
    if (!acc[model.provider]) {
      acc[model.provider] = [];
    }
    acc[model.provider].push(model);
    return acc;
  },
  {} as Record<string, ModelOption[]>,
);
