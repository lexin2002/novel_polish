import { create } from 'zustand'
import axios from 'axios'
import debounce from 'lodash.debounce'

export interface ConfigState {
  priority_order: string[]
  llm: {
    provider: string
    model: string
    api_key: string
    base_url: string
    temperature: number
    max_tokens: number
    safety_exempt_enabled: boolean
    xml_tag_isolation_enabled: boolean
    desensitize_mode: boolean
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
  updateConfig: (patch: Partial<ConfigState>) => void

  // Debounced patch (will be set up after store creation)
  debouncedPatch: ((patch: Partial<ConfigState>) => void) | null
}

const DEFAULT_CONFIG: ConfigState = {
  priority_order: ['P0', 'P1', 'P2', 'P3'],
  llm: {
    provider: 'openai',
    model: 'gpt-4o',
    api_key: '',
    base_url: 'https://api.openai.com/v1',
    temperature: 0.4,
    max_tokens: 4096,
    safety_exempt_enabled: true,
    xml_tag_isolation_enabled: true,
    desensitize_mode: false,
  },
  engine: {
    chunk_size: 1000,
    chunk_size_min: 500,
    chunk_size_max: 3000,
    max_workers: 3,
    max_revisions: 2,
    context_overlap_chars: 200,
    context_snap_to_punctuation: true,
    request_jitter_range: [0.2, 1.5],
    max_requests_per_second: 2,
    chunk_timeout_seconds: 60,
    enable_invalid_modification_break: true,
  },
  network: {
    request_timeout: 5,
    retry_count: 3,
    circuit_breaker_threshold: 3,
  },
  ui: {
    log_to_file_enabled: true,
    log_file_dir: './logs',
    experimental_realtime_log: false,
    sync_scroll_default: false,
  },
  history: {
    max_snapshots: 20,
  },
}

export const useConfigStore = create<ConfigStore>((set, get) => ({
  config: null,
  isLoading: false,
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
      // Fetch the default config after reset
      const response = await axios.get<ConfigState>('/api/config')
      set({ config: response.data, isLoading: false })
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to reset config'
      set({ error: message, isLoading: false })
    }
  },

  updateConfig: (patch: Partial<ConfigState>) => {
    const { config, debouncedPatch } = get()
    if (!config) return

    // Optimistically update local state
    set({ config: { ...config, ...patch } })

    // Trigger debounced API call if available
    if (debouncedPatch) {
      debouncedPatch(patch)
    }
  },
}))

// Set up debounced patch after store creation
const debouncedPatchFn = debounce((patch: Partial<ConfigState>) => {
  useConfigStore.getState().patchConfig(patch)
}, 500)

useConfigStore.setState({ debouncedPatch: debouncedPatchFn })
