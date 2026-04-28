/* eslint-disable react-refresh/only-export-components */
import * as React from 'react'
import { useWebSocket, LogEntry, ProgressInfo } from '../hooks/useWebSocket'

interface WebSocketContextValue {
  logs: LogEntry[]
  progress: ProgressInfo | null
  isConnected: boolean
  isPaused: boolean
  error: string | null
  clearLogs: () => void
  setPaused: (paused: boolean) => void
}

const WebSocketContext = React.createContext<WebSocketContextValue | null>(null)

export const WebSocketProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // Use relative WebSocket URL to support different deployment environments
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${protocol}//${window.location.host}/ws/logs`
  const ws = useWebSocket({
    url: wsUrl,
    maxLogs: 2000,
  })

  return (
    <WebSocketContext.Provider value={ws}>
      {children}
    </WebSocketContext.Provider>
  )
}

export function useSharedWebSocket(): WebSocketContextValue {
  const ctx = React.useContext(WebSocketContext)
  if (!ctx) {
    throw new Error('useSharedWebSocket must be used within a WebSocketProvider')
  }
  return ctx
}
