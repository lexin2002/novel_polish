import { create } from 'zustand'
import axios from 'axios'

export interface Snapshot {
  id: number
  original_text: string
  revised_text: string
  rules_snapshot: any
  config_snapshot: any
  chunk_params: {
    chunks_processed?: number
    total_tokens?: number
    error?: string
  }
  created_at: string
}

interface HistoryState {
  snapshots: Snapshot[]
  selectedSnapshot: Snapshot | null
  isLoading: boolean
  error: string | null

  fetchSnapshots: (limit?: number) => Promise<void>
  fetchSnapshotDetail: (id: number) => Promise<void>
    deleteSnapshot: (id: number) => Promise<void>
    rollbackSnapshot: (id: number) => Promise<void>
    clearSelection: () => void
}

export const useHistoryStore = create<HistoryState>((set, get) => ({
  snapshots: [],
  selectedSnapshot: null,
  isLoading: false,
  error: null,

  fetchSnapshots: async (limit = 20) => {
    set({ isLoading: true, error: null })
    try {
      const response = await axios.get(`http://localhost:57621/api/history?limit=${limit}`)
      set({ snapshots: response.data, isLoading: false })
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Failed to fetch history', isLoading: false })
    }
  },

  fetchSnapshotDetail: async (id: number) => {
    set({ isLoading: true, error: null })
    try {
      const response = await axios.get(`http://localhost:57621/api/history/${id}`)
      set({ selectedSnapshot: response.data, isLoading: false })
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Failed to fetch snapshot detail', isLoading: false })
    }
  },

  deleteSnapshot: async (id: number) => {
    try {
      await axios.delete(`http://localhost:57621/api/history/${id}`)
      const { snapshots } = get()
      set({ snapshots: snapshots.filter(s => s.id !== id) })
    } catch (err) {
      console.error('Failed to delete snapshot:', err)
      throw err
    }
  },

  rollbackSnapshot: async (id: number) => {
    try {
      await axios.post(`http://localhost:57621/api/history/rollback/${id}`)
    } catch (err) {
      console.error('Failed to rollback snapshot:', err)
      throw err
    }
  },

  clearSelection: () => set({ selectedSnapshot: null }),
}))
