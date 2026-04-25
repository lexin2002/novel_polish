import { useEffect, useRef, useState, useCallback } from 'react'

export interface LogEntry {
  id: number
  timestamp: string
  level: 'INFO' | 'WARN' | 'ERROR' | 'DEBUG'
  message: string
  source?: string
}

export interface ProgressInfo {
  chunk: number
  totalChunks: number
  iteration: number
  totalIterations: number
  message?: string
}

interface UseWebSocketOptions {
  url: string
  maxLogs?: number
  reconnectInterval?: number
  onLog?: (log: LogEntry) => void
  onProgress?: (progress: ProgressInfo) => void
}

interface UseWebSocketReturn {
  logs: LogEntry[]
  progress: ProgressInfo | null
  isConnected: boolean
  isPaused: boolean
  error: string | null
  sendPing: () => void
  clearLogs: () => void
  setPaused: (paused: boolean) => void
}

let logIdCounter = 0

function parseLogMessage(data: string): LogEntry | null {
  try {
    // Format: "2026-04-25 22:00:00 - LEVEL - message"
    const match = data.match(/^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - (\w+) - (.+)$/)
    if (match) {
      const [, timestamp, level, message] = match
      const validLevels: LogEntry['level'][] = ['INFO', 'WARN', 'ERROR', 'DEBUG']
      const parsedLevel = validLevels.includes(level as LogEntry['level'])
        ? (level as LogEntry['level'])
        : 'INFO'
      return {
        id: ++logIdCounter,
        timestamp,
        level: parsedLevel,
        message,
      }
    }
    // Fallback: treat as INFO
    return {
      id: ++logIdCounter,
      timestamp: new Date().toISOString().replace('T', ' ').slice(0, 19),
      level: 'INFO',
      message: data,
    }
  } catch {
    return null
  }
}

function parseProgressMessage(data: string): ProgressInfo | null {
  try {
    const json = JSON.parse(data)
    if (json.type === 'progress' && json.data) {
      return {
        chunk: json.data.chunk ?? 0,
        totalChunks: json.data.total_chunks ?? 0,
        iteration: json.data.iteration ?? 0,
        totalIterations: json.data.total_iterations ?? 0,
        message: json.data.message,
      }
    }
  } catch {
    // Not JSON progress format
  }
  return null
}

export function useWebSocket({
  url,
  maxLogs = 2000,
  reconnectInterval = 3000,
  onLog,
  onProgress,
}: UseWebSocketOptions): UseWebSocketReturn {
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [progress, setProgress] = useState<ProgressInfo | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [isPaused, setIsPaused] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const mountedRef = useRef(true)

  const clearLogs = useCallback(() => {
    setLogs([])
  }, [])

  const setPaused = useCallback((paused: boolean) => {
    setIsPaused(paused)
  }, [])

  const sendPing = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send('ping')
    }
  }, [])

  const connect = useCallback(() => {
    if (!mountedRef.current) return

    try {
      const ws = new WebSocket(url)

      ws.onopen = () => {
        if (!mountedRef.current) return
        setIsConnected(true)
        setError(null)
        // Send initial ping to confirm connection
        ws.send('ping')
      }

      ws.onmessage = (event) => {
        if (!mountedRef.current) return

        const data = event.data

        // Try parse as progress first
        const progressData = parseProgressMessage(data)
        if (progressData) {
          setProgress(progressData)
          onProgress?.(progressData)
          return
        }

        // Try parse as log
        const logEntry = parseLogMessage(data)
        if (logEntry) {
          if (!isPaused) {
            setLogs((prev) => {
              const newLogs = [...prev, logEntry]
              // Keep maxLogs entries
              if (newLogs.length > maxLogs) {
                return newLogs.slice(-maxLogs)
              }
              return newLogs
            })
          }
          onLog?.(logEntry)
        }
      }

      ws.onerror = () => {
        if (!mountedRef.current) return
        setError('WebSocket connection error')
      }

      ws.onclose = () => {
        if (!mountedRef.current) return
        setIsConnected(false)

        // Auto reconnect after interval
        reconnectTimeoutRef.current = setTimeout(() => {
          if (mountedRef.current) {
            connect()
          }
        }, reconnectInterval)
      }

      wsRef.current = ws
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to connect')
    }
  }, [url, maxLogs, reconnectInterval, isPaused, onLog, onProgress])

  useEffect(() => {
    mountedRef.current = true
    connect()

    return () => {
      mountedRef.current = false
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [connect])

  return {
    logs,
    progress,
    isConnected,
    isPaused,
    error,
    sendPing,
    clearLogs,
    setPaused,
  }
}