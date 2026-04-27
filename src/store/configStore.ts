import { create } from 'zustand'
import axios from 'axios'
import debounce from 'lodash.debounce'

/**
 * 根据 base_url 自动检测 API 类型（只用于显示）
 * 实际调用由后端根据 base_url 自动路由
 */
export function detectApiType(baseUrl: string): 'openai' | 'anthropic' {
  if (!baseUrl) return 'openai'
  // Anthropic API endpoints contain /anthropic/ or are anthropic.com
  const lower = baseUrl.toLowerCase()
  if (lower.includes('anthropic.com') || lower.includes('/anthropic/') || lower.endsWith('/anthropic')) {
    return 'anthropic'
  }
  return 'openai'
}

export function getApiTypeName(api: 'openai' | 'anthropic'): string {
  return api === 'anthropic' ? 'Anthropic (Messages API)' : 'OpenAI 兼容 (Chat Completions)'
}

export interface ProviderConfig {
  name: string
  api: 'openai' | 'anthropic'  // API protocol type (auto-detected from base_url, for display only)
  api_key: string
  base_url: string
  models: string[]
  active_model: string
}

export interface ConfigState {
  priority_order: string[]
  llm: {
    active_provider: string
    temperature: number
    max_tokens: number
    safety_exempt_enabled: boolean
    xml_tag_isolation_enabled: boolean
    desensitize_mode: boolean
    providers: Record<string, ProviderConfig>
  }
  engine: {
    chunk_size: number
    chunk_size_min: number
    chunk_size_max: number
    max_workers: number
    max_revisions: number
    context_overlap_chars: number
    context_snap_to_punctuation: boolean
    request_jitter_range: [number, number]
    max_requests_per_second: number
    chunk_timeout_seconds: number
    enable_invalid_modification_break: boolean
  }
  network: {
    request_timeout: number
    retry_count: number
    circuit_breaker_threshold: number
  }
  ui: {
    log_to_file_enabled: boolean
    log_file_dir: string
    experimental_realtime_log: boolean
    sync_scroll_default: boolean
  }
  history: {
    max_snapshots: number
  }
}

interface ConfigStore {
  config: ConfigState | null
  isLoading: boolean
  isSyncing: boolean
  error: string | null

  // Actions
  fetchConfig: () => Promise<void>
  patchConfig: (patch: Partial<ConfigState>) => void
  resetConfig: () => Promise<void>
  testConnection: () => Promise<{ ok: boolean; error?: string }>
  updateConfig: (patch: Partial<ConfigState>) => void

  // Debounced patch (will be set up after store creation)
  debouncedPatch: ((patch: Partial<ConfigState>) => void) | null
}

// Default provider configs (matches backend LLM_PROVIDERS)
export const DEFAULT_PROVIDERS: Record<string, ProviderConfig> = {
  openai: {
    name: 'OpenAI',
    api: 'openai',
    api_key: '',
    base_url: 'https://api.openai.com/v1',
    models: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-3.5-turbo'],
    active_model: 'gpt-4o',
  },
  anthropic: {
    name: 'Anthropic',
    api: 'anthropic',
    api_key: '',
    base_url: 'https://api.anthropic.com/v1',
    models: ['claude-3-5-sonnet-latest', 'claude-3-opus-latest', 'claude-3-haiku-latest'],
    active_model: 'claude-3-5-sonnet-latest',
  },
  deepseek: {
    name: 'DeepSeek',
    api: 'openai',
    api_key: '',
    base_url: 'https://api.deepseek.com/v1',
    models: ['deepseek-chat', 'deepseek-coder'],
    active_model: 'deepseek-chat',
  },
  qwen: {
    name: '通义千问',
    api: 'openai',
    api_key: '',
    base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    models: ['qwen-turbo', 'qwen-plus', 'qwen-max'],
    active_model: 'qwen-turbo',
  },
  siliconflow: {
    name: 'SiliconFlow',
    api: 'openai',
    api_key: '',
    base_url: 'https://api.siliconflow.cn/v1',
    models: ['THUDM/GLM-4-32B-0414', 'Qwen/Qwen2-72B-Instruct', 'deepseek-ai/DeepSeek-V2.5'],
    active_model: 'THUDM/GLM-4-32B-0414',
  },
  custom: {
    name: '自定义',
    api: 'openai',
    api_key: '',
    base_url: '',
    models: [],
    active_model: '',
  },
}

export const useConfigStore = create<ConfigStore>((set, get) => ({
  config: null,
  isLoading: true,
  isSyncing: false,
  error: null,
  debouncedPatch: null,

  fetchConfig: async () => {
    set({ isLoading: true, error: null })
    try {
      const response = await axios.get<ConfigState>('/api/config')
      set({ config: response.data, isLoading: false })
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch config'
      console.error('[ConfigStore] fetchConfig error:', message, err)
      set({ error: message, isLoading: false })
    }
  },

  patchConfig: async (patch: Partial<ConfigState>) => {
    set({ isSyncing: true, error: null })
    try {
      const response = await axios.patch<ConfigState>('/api/config', patch)
      set({ config: response.data, isSyncing: false })
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to patch config'
      set({ error: message, isSyncing: false })
    }
  },

  resetConfig: async () => {
    set({ isLoading: true, error: null })
    try {
      await axios.post('/api/config/reset')
      const response = await axios.get<ConfigState>('/api/config')
      set({ config: response.data, isLoading: false })
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to reset config'
      set({ error: message, isLoading: false })
    }
  },

  testConnection: async (): Promise<{ ok: boolean; error?: string }> => {
    const { config } = get()
    if (!config) return { ok: false, error: 'Config not loaded' }
    try {
      const response = await axios.post<{ ok: boolean; error?: string }>(
        '/api/config/test-connection',
        config.llm
      )
      return response.data
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Connection test failed'
      return { ok: false, error: message }
    }
  },

  updateConfig: (newConfig: Partial<ConfigState>) => {
    const { debouncedPatch } = get()
    // newConfig is already a complete deep-cloned config from Sidebar's update function
    // Just set it directly without shallow merging
    set({ config: newConfig as ConfigState })

    if (debouncedPatch) {
      debouncedPatch(newConfig)
    }
  },
}))

// Set up debounced patch after store creation
const debouncedPatchFn = debounce((patch: Partial<ConfigState>) => {
  useConfigStore.getState().patchConfig(patch)
}, 500)

useConfigStore.setState({ debouncedPatch: debouncedPatchFn })