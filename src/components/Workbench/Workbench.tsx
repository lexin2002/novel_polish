import * as React from 'react'
import { DiffEditor } from '@monaco-editor/react'
import type * as monaco from 'monaco-editor'
import { Play, Square, Link, Link2Off, FileText } from 'lucide-react'
import { useWebSocket, ProgressInfo } from '../../hooks/useWebSocket'

interface WorkbenchProps {
  wsUrl?: string
}

const SAMPLE_ORIGINAL = `这是一个用于测试润色功能的小说文本。

 在古老的城堡深处，年轻的骑士亚历克斯正准备踏上寻找失落剑的旅程。他的师父曾经告诉他，那把剑拥有改变世界的力量，但也伴随着巨大的危险。

 "记住，"师父说道，"真正的力量不在于剑本身，而在于持剑之人的心。"
`

interface ControlBarProps {
  isRunning: boolean
  syncScroll: boolean
  onStart: () => void
  onStop: () => void
  onToggleSyncScroll: () => void
}

const ControlBar: React.FC<ControlBarProps> = ({
  isRunning,
  syncScroll,
  onStart,
  onStop,
  onToggleSyncScroll,
}) => (
  <div className="flex items-center justify-between px-4 py-2 bg-gray-100 border-b border-border">
    <div className="flex items-center gap-2">
      <button
        onClick={onStart}
        disabled={isRunning}
        className="flex items-center gap-1 px-3 py-1.5 text-sm text-white bg-green-600 hover:bg-green-700 rounded disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        <Play className="w-4 h-4" />
        启动润色
      </button>
      <button
        onClick={onStop}
        disabled={!isRunning}
        className="flex items-center gap-1 px-3 py-1.5 text-sm text-white bg-red-600 hover:bg-red-700 rounded disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        <Square className="w-4 h-4" />
        停止
      </button>
    </div>
    <div className="flex items-center gap-2">
      <span className="text-sm text-gray-500">同步滚动</span>
      <button
        onClick={onToggleSyncScroll}
        className={`p-1.5 rounded transition-colors ${
          syncScroll
            ? 'bg-primary text-white'
            : 'bg-gray-200 text-gray-600 hover:bg-gray-300'
        }`}
        title={syncScroll ? '取消同步滚动' : '启用同步滚动'}
      >
        {syncScroll ? <Link className="w-4 h-4" /> : <Link2Off className="w-4 h-4" />}
      </button>
    </div>
  </div>
)

interface ProgressBarProps {
  progress: ProgressInfo | null
}

const ProgressBar: React.FC<ProgressBarProps> = ({ progress }) => {
  if (!progress) {
    return (
      <div className="px-4 py-2 bg-gray-50 border-b border-border">
        <span className="text-sm text-gray-400">等待开始润色任务...</span>
      </div>
    )
  }

  const { chunk, totalChunks, iteration, totalIterations, message } = progress
  const totalProgress = totalChunks > 0 && totalIterations > 0
    ? ((chunk * totalIterations + iteration) / (totalChunks * totalIterations)) * 100
    : 0

  return (
    <div className="px-4 py-2 bg-gray-50 border-b border-border">
      <div className="flex items-center justify-between mb-1">
        <span className="text-sm font-medium text-gray-700">
          块 {chunk}/{totalChunks}，迭代 {iteration}/{totalIterations}
        </span>
        <span className="text-sm text-gray-500">{Math.round(totalProgress)}%</span>
      </div>
      <div className="h-2 bg-gray-300 rounded-full overflow-hidden">
        <div
          className="h-full bg-primary transition-all duration-300"
          style={{ width: `${totalProgress}%` }}
        />
      </div>
      {message && (
        <p className="text-xs text-gray-500 mt-1 truncate">{message}</p>
      )}
    </div>
  )
}

export const Workbench: React.FC<WorkbenchProps> = ({ wsUrl = 'ws://localhost:57621/ws/logs' }) => {
  const [originalText, setOriginalText] = React.useState(SAMPLE_ORIGINAL)
  const [revisedText, setRevisedText] = React.useState('')
  const [isRunning, setIsRunning] = React.useState(false)
  const [syncScroll, setSyncScroll] = React.useState(true)
  const abortControllerRef = React.useRef<AbortController | null>(null)

  const { progress } = useWebSocket({
    url: wsUrl,
    maxLogs: 100,
  })

  // Monaco editor refs for sync scroll
  const originalEditorRef = React.useRef<unknown>(null)
  const revisedEditorRef = React.useRef<unknown>(null)
  const isScrollingRef = React.useRef(false)
  const diffEditorRef = React.useRef<monaco.editor.IStandaloneDiffEditor | null>(null)
  const syncCleanupRef = React.useRef<(() => void) | null>(null)

  // Setup sync scroll when editors mount
  const setupSyncScroll = React.useCallback((originalEditor: unknown, revisedEditor: unknown, _diffEditor: monaco.editor.IStandaloneDiffEditor) => {
    if (syncCleanupRef.current) {
      syncCleanupRef.current()
      syncCleanupRef.current = null
    }
    if (!originalEditor || !revisedEditor || !syncScroll) return

    const originalDom = (originalEditor as { getDomNode?: () => HTMLElement }).getDomNode?.()
    const revisedDom = (revisedEditor as { getDomNode?: () => HTMLElement }).getDomNode?.()

    if (!originalDom || !revisedDom) return

    const originalScrollArea = originalDom.querySelector('.monaco-scrollable-element')
    const revisedScrollArea = revisedDom.querySelector('.monaco-scrollable-element')

    if (!originalScrollArea || !revisedScrollArea) return

    const syncHandler = (source: HTMLElement, target: HTMLElement) => (_e: Event) => {
      if (isScrollingRef.current) return
      isScrollingRef.current = true
      const scrollTop = source.scrollTop
      const scrollHeight = source.scrollHeight
      const clientHeight = source.clientHeight
      const scrollRatio = scrollTop / (scrollHeight - clientHeight)

      const targetScrollHeight = target.scrollHeight
      const targetClientHeight = target.clientHeight
      target.scrollTop = scrollRatio * (targetScrollHeight - targetClientHeight)

      setTimeout(() => {
        isScrollingRef.current = false
      }, 50)
    }

    const sourceEl = originalScrollArea as HTMLElement
    const targetEl = revisedScrollArea as HTMLElement
    const handler1 = syncHandler(sourceEl, targetEl)
    const handler2 = syncHandler(targetEl, sourceEl)
    sourceEl.addEventListener('scroll', handler1)
    revisedScrollArea.addEventListener('scroll', handler2)

    syncCleanupRef.current = () => {
      sourceEl.removeEventListener('scroll', handler1)
      revisedScrollArea.removeEventListener('scroll', handler2)
    }
  }, [syncScroll])

  React.useEffect(() => {
    return () => {
      // Abort any in-flight polish request on unmount (handles StrictMode & tab switch)
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
        abortControllerRef.current = null
      }
      if (diffEditorRef.current) {
        diffEditorRef.current.dispose()
        diffEditorRef.current = null
      }
      // Dispose individual editors
      if (originalEditorRef.current) {
        (originalEditorRef.current as { dispose?: () => void })?.dispose?.()
        originalEditorRef.current = null
      }
      if (revisedEditorRef.current) {
        (revisedEditorRef.current as { dispose?: () => void })?.dispose?.()
        revisedEditorRef.current = null
      }
      if (syncCleanupRef.current) {
        syncCleanupRef.current()
        syncCleanupRef.current = null
      }
    }
  }, [])

  const handleToggleSyncScroll = () => {
    setSyncScroll(!syncScroll)
  }

  const handleStart = async () => {
    setIsRunning(true)
    setRevisedText('')
    // Abort any previous controller before creating a new one
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
    abortControllerRef.current = new AbortController()

    try {
      const response = await fetch('/api/polish', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: originalText,
          enable_safety_exempt: true,
          enable_xml_isolation: true,
        }),
        signal: abortControllerRef.current.signal,
      })

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
        throw new Error(error.detail || `HTTP ${response.status}`)
      }

      const result = await response.json()
      setRevisedText(result.polished_text || '')
    } catch (err) {
      // Ignore abort errors
      if (err instanceof Error && err.name === 'AbortError') {
        setRevisedText('已取消')
        return
      }
      const message = err instanceof Error ? err.message : '润色失败'
      console.error('Polish error:', err)
      setRevisedText(`错误: ${message}`)
    } finally {
      setIsRunning(false)
      abortControllerRef.current = null
    }
  }

  const handleStop = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
    setIsRunning(false)
  }

  const MAX_FILE_SIZE = 10 * 1024 * 1024 // 10MB

  const handleLoadOriginal = () => {
    // Open file dialog to load original text
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = '.txt,.md,.text'
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0]
      if (file) {
        if (file.size > MAX_FILE_SIZE) {
          alert(`文件太大 (${(file.size / 1024 / 1024).toFixed(1)}MB). 最大允许 10MB`)
          return
        }
        const text = await file.text()
        setOriginalText(text)
      }
    }
    input.click()
  }

  return (
    <div className="h-full flex flex-col bg-white">
      <ControlBar
        isRunning={isRunning}
        syncScroll={syncScroll}
        onStart={handleStart}
        onStop={handleStop}
        onToggleSyncScroll={handleToggleSyncScroll}
      />

      <ProgressBar progress={progress} />

      <div className="flex items-center justify-between px-4 py-2 bg-gray-50 border-b border-border">
        <div className="flex items-center gap-4">
          <span className="text-sm font-medium text-gray-700">原文 (左) / 润色后 (右)</span>
        </div>
        <button
          onClick={handleLoadOriginal}
          className="flex items-center gap-1 px-2 py-1 text-sm text-gray-600 hover:bg-gray-200 rounded transition-colors"
        >
          <FileText className="w-4 h-4" />
          导入原文
        </button>
      </div>

      <div className="flex-1 overflow-hidden">
        <DiffEditor
          original={originalText}
          modified={revisedText || (isRunning ? '正在润色中...' : '点击"启动润色"开始处理')}
          language="markdown"
          theme="light"
          options={{
            readOnly: true,
            renderSideBySide: true,
            automaticLayout: true,
            scrollBeyondLastLine: false,
            minimap: { enabled: false },
            lineNumbers: 'on',
            wordWrap: 'on',
            fontSize: 14,
            fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
          }}
          onMount={(editor: monaco.editor.IStandaloneDiffEditor) => {
            diffEditorRef.current = editor
            originalEditorRef.current = editor.getOriginalEditor()
            revisedEditorRef.current = editor.getModifiedEditor()
            setupSyncScroll(originalEditorRef.current, revisedEditorRef.current, editor)
          }}
        />
      </div>
    </div>
  )
}