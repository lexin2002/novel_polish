import * as React from 'react'
import * as React from 'react'
import { Play, Square, Link, Link2Off, FileText, Check, X } from 'lucide-react'
import { useSharedWebSocket } from '../../contexts/WebSocketContext'
import { ProgressBar } from '../shared/ProgressBar'
import { computeTextDiff } from '@/utils/diff'

const SAMPLE_ORIGINAL = `这是一个用于测试润色功能的小说文本。

 在古老的城堡深处，年轻的骑士亚历克斯正准备踏上寻找失落剑的旅程。他的师父曾经告诉他，那把剑拥有改变世界的力量，但也伴随着巨大的危险。

 "记住，"师父说道，"真正的力量不在于剑本身，而在于持剑之人的心。"`

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

export const Workbench: React.FC = () => {
  const [originalText, setOriginalText] = React.useState(SAMPLE_ORIGINAL)
  const [revisedText, setRevisedText] = React.useState('')
  const [isRunning, setIsRunning] = React.useState(false)
  const [syncScroll, setSyncScroll] = React.useState(true)
  const [diffResult, setDiffResult] = React.useState<{ originalHtml: string; modifiedHtml: string } | null>(null)
  
  // State for interactive acceptance
  const [chunks, setChunks] = React.useState<Array<{ 
    index: number; 
    original: string; 
    polished: string; 
    status: 'pending' | 'accepted' | 'rejected' 
  }>>([])
  
  const abortControllerRef = React.useRef<AbortController | null>(null)
  const { progress } = useSharedWebSocket()
  
  const leftScrollRef = React.useRef<HTMLDivElement>(null)
  const rightScrollRef = React.useRef<HTMLDivElement>(null)
  const isSyncingRef = React.useRef(false)

  const handleSyncScroll = (source: HTMLElement, target: HTMLElement) => () => {
    if (!syncScroll || isSyncingRef.current) return;
    isSyncingRef.current = true;
    
    const scrollRatio = source.scrollTop / (source.scrollHeight - source.clientHeight || 1);
    target.scrollTop = scrollRatio * (target.scrollHeight - target.clientHeight);
    
    setTimeout(() => { isSyncingRef.current = false; }, 50);
  }

  const handleToggleSyncScroll = () => {
    setSyncScroll(!syncScroll)
  }

  const handleAcceptChunk = (index: number) => {
    setChunks(prev => prev.map(c => c.index === index ? { ...c, status: 'accepted' } : c))
  }

  const handleRejectChunk = (index: number) => {
    setChunks(prev => prev.map(c => c.index === index ? { ...c, status: 'rejected' } : c))
  }

  const handleStart = async () => {
    setIsRunning(true)
    setRevisedText('')
    setDiffResult(null)
    setChunks([])
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
    abortControllerRef.current = new AbortController()

    try {
      const response = await fetch('http://localhost:57621/api/polish', {
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

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()
      let accumulatedText = ''
      let buffer = ''

      while (true) {
        const { value, done } = await reader!.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const jsonStr = line.replace('data: ', '').trim()
              const event = JSON.parse(jsonStr)
              
              if (event.type === 'chunk') {
                const chunkData = event.data
                const polished = chunkData.polished_content || ''
                const original = chunkData.original_content || ''
                
                accumulatedText += polished
                setRevisedText(accumulatedText)
                
                setChunks(prev => [
                  ...prev, 
                  { index: chunkData.chunk_index, original, polished, status: 'pending' }
                ])
              } else if (event.type === 'error') {
                throw new Error(event.error)
              }
            } catch (e) {
              console.error('SSE parse error:', e)
            }
          }
        }
      }

      setDiffResult(computeTextDiff(originalText, accumulatedText))
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        setRevisedText('已取消')
        return
      }
      const message = err instanceof Error ? err.message : '润色失败'
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
          {chunks.length > 0 && (
            <span className="text-xs text-gray-400">
              已处理 {chunks.length} 个片段
            </span>
          )}
        </div>
        <button
          onClick={handleLoadOriginal}
          className="flex items-center gap-1 px-2 py-1 text-sm text-gray-600 hover:bg-gray-200 rounded transition-colors"
        >
          <FileText className="w-4 h-4" />
          导入原文
        </button>
      </div>

      <div className="flex-1 overflow-hidden flex">
        <div 
          ref={leftScrollRef}
          onScroll={handleSyncScroll(leftScrollRef.current!, rightScrollRef.current!)}
          className="flex-1 overflow-y-auto p-6 border-r border-border whitespace-pre-wrap font-serif text-lg leading-relaxed"
        >
          {diffResult ? (
            <div dangerouslySetInnerHTML={{ __html: diffResult.originalHtml }} />
          ) : (
            <div className="outline-none" contentEditable={true} onInput={(e) => setOriginalText(e.currentTarget.innerText)}>{originalText}</div>
          )}
        </div>
        <div 
          ref={rightScrollRef}
          onScroll={handleSyncScroll(rightScrollRef.current!, leftScrollRef.current!)}
          className="flex-1 overflow-y-auto p-6 whitespace-pre-wrap font-serif text-lg leading-relaxed relative"
        >
          {diffResult ? (
            <div dangerouslySetInnerHTML={{ __html: diffResult.modifiedHtml }} />
          ) : (
            <div className="space-y-4">
              {chunks.length === 0 && (
                <div className="text-gray-400 italic">
                  {revisedText || (isRunning ? '正在润色中...' : '点击"启动润色"开始处理')}
                </div>
              )}
              {chunks.map((chunk, idx) => (
                <div key={idx} className="group relative p-2 rounded border border-transparent hover:border-blue-200 hover:bg-blue-50 transition-all">
                  <div className="absolute right-2 top-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button 
                      onClick={() => handleAcceptChunk(chunk.index)}
                      className={`p-1 rounded ${chunk.status === 'accepted' ? 'bg-green-500 text-white' : 'bg-white text-gray-400 hover:text-green-600 border border-gray-200'}`}
                      title="采纳"
                    >
                      <Check className="w-3 h-3" />
                    </button>
                    <button 
                      onClick={() => handleRejectChunk(chunk.index)}
                      className={`p-1 rounded ${chunk.status === 'rejected' ? 'bg-red-500 text-white' : 'bg-white text-gray-400 hover:text-red-600 border border-gray-200'}`}
                      title="拒绝"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                  <div className={`transition-colors ${chunk.status === 'accepted' ? 'text-green-900' : chunk.status === 'rejected' ? 'text-red-900' : 'text-gray-800'}`}>
                    {chunk.polished}
                  </div>
                </div>
              ))}
              {isRunning && chunks.length > 0 && (
                <div className="text-gray-400 italic text-sm animate-pulse">正在生成后续内容...</div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
