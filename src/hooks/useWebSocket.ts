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
  // Track isPaused via Ref to avoid re-creating WebSocket on pause toggle
  const isPausedRef = useRef(isPaused)

  // Keep isPausedRef in sync without triggering connect rebuild
  useEffect(() => {
    isPausedRef.current = isPaused
  }, [isPaused])

  const clearLogs = useCallback(() => {
    setLogs([])
  }, [])

  const setPausedCallback = useCallback((paused: boolean) => {
    setIsPaused(paused)
  }, [])

  const sendPing = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send('ping')
    }
  }, [])

  const connect = useCallback(() => {
    if (!mountedRef.current) return

    // Close existing connection before creating a new one (handles StrictMode double-invoke)
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }

    try {
      const ws = new WebSocket(url)
      wsRef.current = ws

      ws.onopen = () => {
        if (!mountedRef.current) return
        // Check wsRef hasn't been replaced (StrictMode guard)
        if (wsRef.current !== ws) return
        setIsConnected(true)
        setError(null)
        // Send initial ping to confirm connection
        ws.send('ping')
      }

      ws.onmessage = (event) => {
        if (!mountedRef.current) return
        if (wsRef.current !== ws) return

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
          // Use ref-based isPaused to avoid stale closure when isPaused changes
          if (!isPausedRef.current) {
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
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to connect')
    }
  }, [url, maxLogs, reconnectInterval, onLog, onProgress])
  // Note: isPaused intentionally omitted — tracked via isPausedRef to prevent WS reconnect

  useEffect(() => {
    mountedRef.current = true
    connect()

    return () => {
      mountedRef.current = false
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
        reconnectTimeoutRef.current = null
      }
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
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
    setPaused: setPausedCallback,
  }
}