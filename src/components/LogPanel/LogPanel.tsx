import * as React from 'react'
import { Pause, Play, Trash2, Wifi, WifiOff } from 'lucide-react'
import { useWebSocket, LogEntry } from '../../hooks/useWebSocket'
import { ProgressBar } from '../shared/ProgressBar'

interface LogPanelProps {
  url?: string
}

const LOG_LEVEL_CLASSES: Record<LogEntry['level'], string> = {
  INFO: 'text-gray-900',
  WARN: 'text-amber-600',
  ERROR: 'text-red-600',
  DEBUG: 'text-gray-500',
}

interface LogLineProps {
  entry: LogEntry
}

const LogLine: React.FC<LogLineProps> = ({ entry }) => (
  <div className="flex font-mono text-sm leading-5">
    <span className="text-gray-500 w-40 flex-shrink-0">{entry.timestamp}</span>
    <span className={`w-16 flex-shrink-0 font-medium ${LOG_LEVEL_CLASSES[entry.level]}`}>
      {entry.level}
    </span>
    <span className={`flex-1 ${LOG_LEVEL_CLASSES[entry.level]}`}>
      {entry.message}
    </span>
  </div>
)

export const LogPanel: React.FC<LogPanelProps> = ({ url = 'ws://localhost:57621/ws/logs' }) => {
  const {
    logs,
    progress,
    isConnected,
    isPaused,
    error,
    clearLogs,
    setPaused,
  } = useWebSocket({ url, maxLogs: 2000 })

  const logsEndRef = React.useRef<HTMLDivElement>(null)
  const containerRef = React.useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom unless paused; only scroll if user is near the bottom
  React.useEffect(() => {
    if (!isPaused && logsEndRef.current && containerRef.current) {
      const el = containerRef.current
      const isNearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 100
      if (isNearBottom) {
        logsEndRef.current.scrollIntoView({ behavior: 'smooth' })
      }
    }
  }, [logs, isPaused])

  const handleTogglePause = () => {
    setPaused(!isPaused)
  }

  return (
    <div className="h-full flex flex-col bg-[#f4f4f4]">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-gray-200 border-b border-gray-300">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-700">实时日志</span>
          <span className="text-xs text-gray-500">({logs.length} 条)</span>
          <span className={`flex items-center gap-1 text-xs ${isConnected ? 'text-green-600' : 'text-red-500'}`}>
            {isConnected ? <Wifi className="w-3 h-3" /> : <WifiOff className="w-3 h-3" />}
            {isConnected ? '已连接' : '已断开'}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleTogglePause}
            className="flex items-center gap-1 px-2 py-1 text-xs text-gray-600 hover:bg-gray-300 rounded transition-colors"
            title={isPaused ? '继续滚动' : '暂停滚动'}
          >
            {isPaused ? <Play className="w-3 h-3" /> : <Pause className="w-3 h-3" />}
            {isPaused ? '继续' : '暂停'}
          </button>
          <button
            onClick={clearLogs}
            className="flex items-center gap-1 px-2 py-1 text-xs text-gray-600 hover:bg-gray-300 rounded transition-colors"
            title="清空日志"
          >
            <Trash2 className="w-3 h-3" />
            清空
          </button>
        </div>
      </div>

      {/* Progress Bar */}
      {progress && <ProgressBar progress={progress} />}

      {/* Error Display */}
      {error && (
        <div className="px-4 py-2 bg-red-100 border-b border-red-200 text-red-700 text-sm">
          错误: {error}
        </div>
      )}

      {/* Log Terminal */}
      <div
        ref={containerRef}
        className="flex-1 overflow-y-auto p-2 font-mono"
      >
        {logs.length === 0 ? (
          <div className="text-gray-400 text-sm italic p-4 text-center">
            等待日志数据...
          </div>
        ) : (
          <div className="space-y-0.5">
            {logs.map((entry) => (
              <LogLine key={entry.id} entry={entry} />
            ))}
            <div ref={logsEndRef} />
          </div>
        )}
      </div>
    </div>
  )
}