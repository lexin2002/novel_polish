import * as React from 'react'
import * as Accordion from '@radix-ui/react-accordion'
import * as Switch from '@radix-ui/react-switch'
import * as Slider from '@radix-ui/react-slider'
import * as Select from '@radix-ui/react-select'
import { ChevronDown, RotateCcw, Settings } from 'lucide-react'
import { useConfigStore, ConfigState, detectApiType, getApiTypeName } from '../../store/configStore'

interface ConfigItemProps {
  label: string
  description?: string
  children: React.ReactNode
}

const ConfigItem: React.FC<ConfigItemProps> = ({ label, description, children }) => (
  <div className="mb-4">
    <div className="flex items-center justify-between mb-1">
      <label className="text-sm font-medium text-foreground">{label}</label>
      {description && <span className="text-xs text-muted-foreground">{description}</span>}
    </div>
    {children}
  </div>
)

interface SliderItemProps {
  label: string
  value: number
  min: number
  max: number
  step?: number
  onChange: (value: number) => void
}

const SliderItem: React.FC<SliderItemProps> = ({ label, value, min, max, step = 1, onChange }) => (
  <ConfigItem label={label}>
    <div className="flex items-center gap-3">
      <Slider.Root
        className="relative flex items-center select-none touch-none w-full h-5"
        value={[value]}
        min={min}
        max={max}
        step={step}
        onValueChange={([v]) => onChange(v)}
      >
        <Slider.Track className="bg-border relative grow rounded-full h-2">
          <Slider.Range className="absolute bg-primary rounded-full h-full" />
        </Slider.Track>
        <Slider.Thumb
          className="block w-4 h-4 bg-primary rounded-full hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
          aria-label={label}
        />
      </Slider.Root>
      <span className="text-sm text-muted-foreground w-12 text-right">{value}</span>
    </div>
  </ConfigItem>
)

interface SwitchItemProps {
  label: string
  checked: boolean
  onChange: (checked: boolean) => void
}

const SwitchItem: React.FC<SwitchItemProps> = ({ label, checked, onChange }) => (
  <ConfigItem label={label}>
    <div className="flex items-center justify-between">
      <span className="text-sm text-muted-foreground">启用</span>
      <Switch.Root
        className="w-9 h-5 bg-border rounded-full relative data-[state=checked]:bg-primary cursor-pointer"
        checked={checked}
        onCheckedChange={onChange}
      >
        <Switch.Thumb className="block w-4 h-4 bg-white rounded-full transition-transform translate-x-0.5 data-[state=checked]:translate-x-4" />
      </Switch.Root>
    </div>
  </ConfigItem>
)

// Provider selector for LLM config - shows active provider name with dropdown
const ProviderSelector: React.FC<{
  activeProvider: string
  providers: Record<string, { name: string }>
  onChange: (providerId: string) => void
}> = ({ activeProvider, providers, onChange }) => (
  <ConfigItem label="当前提供商">
    <Select.Root value={activeProvider} onValueChange={onChange}>
      <Select.Trigger
        className="flex items-center justify-between w-full px-3 py-2.5 text-sm bg-primary/5 border border-primary/20 rounded-md hover:border-primary/50 focus:outline-none focus:ring-2 focus:ring-primary"
        aria-label="选择提供商"
      >
        <Select.Value>
          <span className="font-medium">{providers[activeProvider]?.name || activeProvider}</span>
        </Select.Value>
        <Select.Icon>
          <ChevronDown className="w-4 h-4 text-muted-foreground" />
        </Select.Icon>
      </Select.Trigger>
      <Select.Portal>
        <Select.Content className="overflow-hidden bg-white border border-border rounded-md shadow-lg z-50">
          <Select.Viewport className="p-1">
            {Object.entries(providers).map(([id, p]) => (
              <Select.Item
                key={id}
                value={id}
                className="relative flex items-center px-8 py-2 text-sm rounded-md cursor-pointer hover:bg-secondary data-[highlighted]:bg-secondary outline-none"
              >
                <Select.ItemText>{p.name}</Select.ItemText>
              </Select.Item>
            ))}
          </Select.Viewport>
        </Select.Content>
      </Select.Portal>
    </Select.Root>
  </ConfigItem>
)

interface NumberItemProps {
  label: string
  value: number
  min?: number
  max?: number
  onChange: (value: number) => void
}

const NumberItem: React.FC<NumberItemProps> = ({ label, value, min, max, onChange }) => (
  <ConfigItem label={label}>
    <input
      type="number"
      value={value}
      min={min}
      max={max}
      onChange={(e) => onChange(Number(e.target.value))}
      className="w-full px-3 py-2 text-sm bg-white border border-border rounded-md hover:border-primary/50 focus:outline-none focus:ring-2 focus:ring-primary"
    />
  </ConfigItem>
)

interface TextItemProps {
  label: string
  value: string
  placeholder?: string
  type?: 'text' | 'password'
  onChange: (value: string) => void
}

const TextItem: React.FC<TextItemProps> = ({ label, value, placeholder, type = 'text', onChange }) => (
  <ConfigItem label={label}>
    <input
      type={type}
      value={value}
      placeholder={placeholder}
      onChange={(e) => onChange(e.target.value)}
      className="w-full px-3 py-2 text-sm bg-white border border-border rounded-md hover:border-primary/50 focus:outline-none focus:ring-2 focus:ring-primary"
    />
  </ConfigItem>
)

export const Sidebar: React.FC = () => {
  const { config, isLoading, isSyncing, error, resetConfig, fetchConfig } = useConfigStore()
  const [testState, setTestState] = React.useState<{ testing: boolean; result: { ok: boolean; error?: string } | null }>({ testing: false, result: null })

  React.useEffect(() => {
    fetchConfig()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []) // fetchConfig is stable from store

  const handleTestConnection = async () => {
    setTestState({ testing: true, result: null })
    const result = await useConfigStore.getState().testConnection()
    setTestState({ testing: false, result })
  }

  if (isLoading) {
    return (
      <aside className="w-80 bg-white border-r border-border p-4">
        <div className="flex items-center gap-2 text-muted-foreground">
          <Settings className="w-4 h-4 animate-spin" />
          <span>加载配置中...</span>
        </div>
      </aside>
    )
  }

  if (error) {
    return (
      <aside className="w-80 bg-white border-r border-border overflow-y-auto">
        <div className="p-4 border-b border-border sticky top-0 bg-white z-10">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-foreground flex items-center gap-2">
              <Settings className="w-5 h-5" />
              系统设置
            </h2>
            <button
              onClick={fetchConfig}
              className="flex items-center gap-1 px-2 py-1 text-sm text-primary hover:bg-secondary rounded transition-colors"
              title="刷新"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
          </div>
        </div>
        <div className="p-4">
          <p className="text-destructive text-sm">加载配置失败</p>
          <p className="text-muted-foreground text-xs mt-1">错误: {error}</p>
          <button
            onClick={fetchConfig}
            className="mt-3 px-3 py-1.5 text-sm bg-primary text-white rounded hover:bg-primary/90"
          >
            重试
          </button>
        </div>
      </aside>
    )
  }

  if (!config) return null

  // Deep clone to avoid mutation issues
  const deepClone = <T,>(obj: T): T => JSON.parse(JSON.stringify(obj))

  const update = (path: string[], value: unknown) => {
    const patch = deepClone(config)
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let current: any = patch
    for (let i = 0; i < path.length - 1; i++) {
      current = current[path[i]]
    }
    current[path[path.length - 1]] = value
    useConfigStore.getState().updateConfig(patch as Partial<ConfigState>)
  }

  /** Batch multiple path updates into a single deepClone + updateConfig call */
  const batchUpdate = (updates: Array<{ path: string[]; value: unknown }>) => {
    const patch = deepClone(config)
    for (const { path, value } of updates) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      let current: any = patch
      for (let i = 0; i < path.length - 1; i++) {
        current = current[path[i]]
      }
      current[path[path.length - 1]] = value
    }
    useConfigStore.getState().updateConfig(patch as Partial<ConfigState>)
  }

  return (
    <aside className="w-80 bg-white border-r border-border overflow-y-auto">
      <div className="p-4 border-b border-border sticky top-0 bg-white z-10">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-foreground flex items-center gap-2">
            <Settings className="w-5 h-5" />
            系统设置
          </h2>
          <div className="flex items-center gap-2">
            <button
              onClick={resetConfig}
              className="flex items-center gap-1 px-2 py-1 text-sm text-muted-foreground hover:text-foreground hover:bg-secondary rounded transition-colors"
              title="重置为默认"
            >
              <RotateCcw className="w-4 h-4" />
              重置
            </button>
            <button
              onClick={fetchConfig}
              className="flex items-center gap-1 px-2 py-1 text-sm text-muted-foreground hover:text-foreground hover:bg-secondary rounded transition-colors"
              title="刷新"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
          </div>
        </div>
        {isSyncing && <span className="text-xs text-primary">同步中...</span>}
        {error && <span className="text-xs text-destructive">同步失败</span>}
      </div>

      <Accordion.Root className="w-full" type="multiple" defaultValue={['llm', 'engine']}>
        {/* LLM Configuration */}
        <Accordion.Item value="llm" className="border-b border-border">
          <Accordion.Trigger className="flex items-center justify-between w-full px-4 py-3 text-left group">
            <span className="text-sm font-medium text-foreground">LLM 配置</span>
            <ChevronDown className="w-4 h-4 text-muted-foreground transition-transform group-data-[state=open]:rotate-180" />
          </Accordion.Trigger>
          <Accordion.Content className="px-4 pb-4">
            {/* Provider Selector - the main control */}
            <ProviderSelector
              activeProvider={config.llm.active_provider}
              providers={config.llm.providers}
              onChange={(providerId) => update(['llm', 'active_provider'], providerId)}
            />

            {/* Divider */}
            <div className="border-t border-border my-3" />

            {/* Active Provider's Configuration */}
            {(() => {
              const active = config.llm.providers[config.llm.active_provider]
              if (!active) return null
              return (
                <>
                  <div className="text-xs font-medium text-muted-foreground mb-2 px-1">
                    {active.name} 配置
                  </div>
                  {/* API Type */}
                  <ConfigItem label="API 类型">
                    <div className="px-3 py-2 text-sm bg-muted/30 border border-border rounded-md text-muted-foreground">
                      {getApiTypeName(active.api || detectApiType(active.base_url))}
                    </div>
                  </ConfigItem>
                  <TextItem
                    label="API Key"
                    value={active.api_key}
                    placeholder="sk-..."
                    type="password"
                    onChange={(v) => update(['llm', 'providers', config.llm.active_provider, 'api_key'], v)}
                  />
                  <TextItem
                    label="Base URL"
                    value={active.base_url}
                    placeholder={active.api === 'anthropic' ? 'https://api.minimaxi.com/anthropic/v1' : 'https://api.openai.com/v1'}
                    onChange={(v) => {
                      // Strip trailing /messages or /chat/completions since backend appends them
                      const normalized = v
                        .replace(/\/messages\/?$/, '')
                        .replace(/\/chat\/completions\/?$/, '')
                        .replace(/\/$/, '')
                      // Auto-detect API type from base_url — single batch update
                      const detectedApi = detectApiType(normalized)
                      const providerPath = ['llm', 'providers', config.llm.active_provider]
                      batchUpdate([
                        { path: [...providerPath, 'base_url'], value: normalized },
                        { path: [...providerPath, 'api'], value: detectedApi },
                      ])
                    }}
                  />
                  {/* Custom provider name editing */}
                  {config.llm.active_provider === 'custom' && (
                    <TextItem
                      label="提供商名称"
                      value={active.name}
                      placeholder="e.g. 我的模型"
                      onChange={(v) => update(['llm', 'providers', config.llm.active_provider, 'name'], v)}
                    />
                  )}
                  {/* Model selector - allow custom input for all providers */}
                  <ConfigItem label="模型">
                    <input
                      type="text"
                      value={active.active_model}
                      placeholder={active.models.length > 0 ? "从下拉选择或直接输入" : "直接输入模型名称"}
                      onChange={(e) => update(['llm', 'providers', config.llm.active_provider, 'active_model'], e.target.value)}
                      list={active.models.length > 0 ? `models-list-${config.llm.active_provider}` : undefined}
                      className="w-full px-3 py-2 text-sm bg-white border border-border rounded-md hover:border-primary/50 focus:outline-none focus:ring-2 focus:ring-primary"
                    />
                    {active.models.length > 0 && (
                      <datalist id={`models-list-${config.llm.active_provider}`}>
                        {active.models.map((model) => (
                          <option key={model} value={model} />
                        ))}
                      </datalist>
                    )}
                  </ConfigItem>

                  {/* Test Connection Button */}
                  <div className="mt-3">
                    <button
                      onClick={handleTestConnection}
                      disabled={testState.testing || !active.api_key || !active.base_url || !active.active_model}
                      className="w-full px-3 py-2 text-sm font-medium rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed bg-green-600 text-white hover:bg-green-700"
                    >
                      {testState.testing ? (
                        <span className="flex items-center justify-center gap-2">
                          <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                          连接中...
                        </span>
                      ) : (
                        '测试连接'
                      )}
                    </button>
                    {testState.result && (
                      <div className={`mt-2 text-xs px-2 py-1.5 rounded ${testState.result.ok ? 'bg-green-50 text-green-700 border border-green-200' : 'bg-red-50 text-red-700 border border-red-200'}`}>
                        {testState.result.ok ? (
                          <span>✅ 连接成功！模型: {testState.result.error || 'OK'}</span>
                        ) : (
                          <span>❌ {testState.result.error}</span>
                        )}
                      </div>
                    )}
                  </div>
                  <div className="border-t border-border my-3" />
                </>
              )
            })()}

            {/* Shared LLM Parameters */}
            <div className="text-xs font-medium text-muted-foreground mb-2 px-1">
              通用参数
            </div>
            <SliderItem
              label="Temperature"
              value={config.llm.temperature}
              min={0}
              max={1}
              step={0.05}
              onChange={(v) => update(['llm', 'temperature'], v)}
            />
            <NumberItem
              label="Max Tokens"
              value={config.llm.max_tokens}
              min={100}
              max={32000}
              onChange={(v) => update(['llm', 'max_tokens'], v)}
            />
            <SwitchItem
              label="安全豁免"
              checked={config.llm.safety_exempt_enabled}
              onChange={(v) => update(['llm', 'safety_exempt_enabled'], v)}
            />
            <SwitchItem
              label="XML 标签隔离"
              checked={config.llm.xml_tag_isolation_enabled}
              onChange={(v) => update(['llm', 'xml_tag_isolation_enabled'], v)}
            />
            <SwitchItem
              label="脱敏模式"
              checked={config.llm.desensitize_mode}
              onChange={(v) => update(['llm', 'desensitize_mode'], v)}
            />
          </Accordion.Content>
        </Accordion.Item>

        {/* Engine Configuration */}
        <Accordion.Item value="engine" className="border-b border-border">
          <Accordion.Trigger className="flex items-center justify-between w-full px-4 py-3 text-left group">
            <span className="text-sm font-medium text-foreground">引擎性能参数</span>
            <ChevronDown className="w-4 h-4 text-muted-foreground transition-transform group-data-[state=open]:rotate-180" />
          </Accordion.Trigger>
          <Accordion.Content className="px-4 pb-4">
            <SliderItem
              label="切块大小"
              value={config.engine.chunk_size}
              min={config.engine.chunk_size_min}
              max={config.engine.chunk_size_max}
              step={100}
              onChange={(v) => update(['engine', 'chunk_size'], v)}
            />
            <NumberItem
              label="并发线程数"
              value={config.engine.max_workers}
              min={1}
              max={5}
              onChange={(v) => update(['engine', 'max_workers'], v)}
            />
            <NumberItem
              label="最大修复循环"
              value={config.engine.max_revisions}
              min={1}
              max={5}
              onChange={(v) => update(['engine', 'max_revisions'], v)}
            />
            <NumberItem
              label="滑动窗口重叠字符"
              value={config.engine.context_overlap_chars}
              min={0}
              max={500}
              onChange={(v) => update(['engine', 'context_overlap_chars'], v)}
            />
            <SwitchItem
              label="动态标点吸附"
              checked={config.engine.context_snap_to_punctuation}
              onChange={(v) => update(['engine', 'context_snap_to_punctuation'], v)}
            />
            <NumberItem
              label="每秒最大请求数"
              value={config.engine.max_requests_per_second}
              min={1}
              max={10}
              onChange={(v) => update(['engine', 'max_requests_per_second'], v)}
            />
            <NumberItem
              label="单块超时秒数"
              value={config.engine.chunk_timeout_seconds}
              min={30}
              max={120}
              onChange={(v) => update(['engine', 'chunk_timeout_seconds'], v)}
            />
            <SwitchItem
              label="无效修改熔断"
              checked={config.engine.enable_invalid_modification_break}
              onChange={(v) => update(['engine', 'enable_invalid_modification_break'], v)}
            />
          </Accordion.Content>
        </Accordion.Item>

        {/* Network Configuration */}
        <Accordion.Item value="network" className="border-b border-border">
          <Accordion.Trigger className="flex items-center justify-between w-full px-4 py-3 text-left group">
            <span className="text-sm font-medium text-foreground">网络请求配置</span>
            <ChevronDown className="w-4 h-4 text-muted-foreground transition-transform group-data-[state=open]:rotate-180" />
          </Accordion.Trigger>
          <Accordion.Content className="px-4 pb-4">
            <NumberItem
              label="请求超时(秒)"
              value={config.network.request_timeout}
              min={1}
              max={30}
              onChange={(v) => update(['network', 'request_timeout'], v)}
            />
            <NumberItem
              label="重试次数"
              value={config.network.retry_count}
              min={0}
              max={5}
              onChange={(v) => update(['network', 'retry_count'], v)}
            />
            <NumberItem
              label="熔断阈值"
              value={config.network.circuit_breaker_threshold}
              min={1}
              max={10}
              onChange={(v) => update(['network', 'circuit_breaker_threshold'], v)}
            />
          </Accordion.Content>
        </Accordion.Item>

        {/* UI Configuration */}
        <Accordion.Item value="ui" className="border-b border-border">
          <Accordion.Trigger className="flex items-center justify-between w-full px-4 py-3 text-left group">
            <span className="text-sm font-medium text-foreground">UI 行为配置</span>
            <ChevronDown className="w-4 h-4 text-muted-foreground transition-transform group-data-[state=open]:rotate-180" />
          </Accordion.Trigger>
          <Accordion.Content className="px-4 pb-4">
            <SwitchItem
              label="日志文件启用"
              checked={config.ui.log_to_file_enabled}
              onChange={(v) => update(['ui', 'log_to_file_enabled'], v)}
            />
            <TextItem
              label="日志目录"
              value={config.ui.log_file_dir}
              onChange={(v) => update(['ui', 'log_file_dir'], v)}
            />
            <SwitchItem
              label="实验性实时日志"
              checked={config.ui.experimental_realtime_log}
              onChange={(v) => update(['ui', 'experimental_realtime_log'], v)}
            />
            <SwitchItem
              label="同步滚动默认开启"
              checked={config.ui.sync_scroll_default}
              onChange={(v) => update(['ui', 'sync_scroll_default'], v)}
            />
          </Accordion.Content>
        </Accordion.Item>

        {/* History Configuration */}
        <Accordion.Item value="history" className="border-b border-border">
          <Accordion.Trigger className="flex items-center justify-between w-full px-4 py-3 text-left group">
            <span className="text-sm font-medium text-foreground">历史管理配置</span>
            <ChevronDown className="w-4 h-4 text-muted-foreground transition-transform group-data-[state=open]:rotate-180" />
          </Accordion.Trigger>
          <Accordion.Content className="px-4 pb-4">
            <NumberItem
              label="最大快照数量"
              value={config.history.max_snapshots}
              min={5}
              max={100}
              onChange={(v) => update(['history', 'max_snapshots'], v)}
            />
          </Accordion.Content>
        </Accordion.Item>
      </Accordion.Root>
    </aside>
  )
}
