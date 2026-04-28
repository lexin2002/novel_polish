import React, { useEffect } from 'react'
import { useHistoryStore } from '@/store/historyStore'
import { Trash2, FileText, Clock, AlertCircle } from 'lucide-react'

export const Archive: React.FC = () => {
  const { 
    snapshots, 
    selectedSnapshot, 
    isLoading, 
    error, 
    fetchSnapshots, 
    fetchSnapshotDetail, 
    deleteSnapshot, 
    clearSelection 
  } = useHistoryStore()

  useEffect(() => {
    fetchSnapshots()
  }, [fetchSnapshots])

  if (error) {
    return (
      <div className="h-full flex items-center justify-center p-8 text-center">
        <div className="max-w-md">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold mb-2">加载历史记录失败</h3>
          <p className="text-gray-500 mb-4">{error}</p>
          <button 
            onClick={() => fetchSnapshots()}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
          >
            重试
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="h-full flex overflow-hidden bg-white">
      {/* Left: Snapshot List */}
      <div className="w-80 border-r flex flex-col bg-slate-50/50">
        <div className="p-4 border-b bg-white">
          <h3 className="font-semibold flex items-center gap-2">
            <Clock className="w-4 h-4" /> 
            历史快照 ({snapshots.length})
          </h3>
        </div>
        
        <div className="flex-1 overflow-y-auto">
          {isLoading && snapshots.length === 0 ? (
            <div className="p-8 text-center text-gray-400 text-sm">加载中...</div>
          ) : snapshots.length === 0 ? (
            <div className="p-8 text-center text-gray-400 text-sm">暂无润色历史</div>
          ) : (
            <div className="p-2 space-y-1">
              {snapshots.map((s) => (
                <button
                  key={s.id}
                  onClick={() => fetchSnapshotDetail(s.id)}
                  className={`w-full text-left p-3 rounded-lg transition-all group ${
                    selectedSnapshot?.id === s.id 
                    ? 'bg-blue-600 text-white shadow-sm' 
                    : 'hover:bg-slate-200 text-slate-700'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs opacity-80 font-mono">ID: {s.id}</span>
                    <span className="text-[10px] opacity-70">
                      {new Date(s.created_at).toLocaleString()}
                    </span>
                  </div>
                  <div className="text-sm font-medium truncate">
                    {s.original_text.slice(0, 30)}...
                  </div>
                  <div className="flex gap-2 mt-2">
                    <span className="text-[10px] bg-slate-200 text-slate-600 px-1 rounded">
                      {s.chunk_params.chunks_processed || 0} chunks
                    </span>
                    <span className="text-[10px] bg-slate-200 text-slate-600 px-1 rounded">
                      {s.chunk_params.total_tokens || 0} tokens
                    </span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Right: Detail View */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {selectedSnapshot ? (
          <>
            <div className="p-4 border-b flex items-center justify-between bg-white">
              <div className="flex items-center gap-3">
                <FileText className="w-5 h-5 text-slate-400" />
                <div>
                  <h3 className="font-semibold">快照详情 #{selectedSnapshot.id}</h3>
                  <p className="text-xs text-gray-400">
                    创建于 {new Date(selectedSnapshot.created_at).toLocaleString()}
                  </p>
                </div>
              </div>
              <div className="flex gap-2">
                <button 
                  onClick={clearSelection}
                  className="px-3 py-1 text-sm border rounded hover:bg-gray-50 transition-colors"
                >
                  关闭
                </button>
                <button 
                  onClick={async () => {
                    if (confirm('确定要删除此记录吗？')) {
                      await deleteSnapshot(selectedSnapshot.id)
                      clearSelection()
                    }
                  }}
                  className="px-3 py-1 text-sm bg-red-500 text-white rounded hover:bg-red-600 transition-colors flex items-center gap-1"
                >
                  <Trash2 className="w-4 h-4" />
                  删除
                </button>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-6 bg-slate-50">
              <div className="max-w-4xl mx-auto space-y-6">
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-4 bg-white rounded-xl border shadow-sm">
                    <label className="text-xs font-bold text-gray-400 uppercase block mb-2">原文</label>
                    <div className="text-sm whitespace-pre-wrap text-slate-800 leading-relaxed">
                      {selectedSnapshot.original_text}
                    </div>
                  </div>
                  <div className="p-4 bg-white rounded-xl border shadow-sm border-blue-200 ring-1 ring-blue-100">
                    <label className="text-xs font-bold text-blue-500 uppercase block mb-2">润色后</label>
                    <div className="text-sm whitespace-pre-wrap text-slate-800 leading-relaxed">
                      {selectedSnapshot.revised_text}
                    </div>
                  </div>
                </div>
                
                <div className="border-t pt-6">
                  <div className="grid grid-cols-2 gap-6">
                    <div className="space-y-3">
                      <h4 className="text-sm font-semibold">配置快照</h4>
                      <pre className="p-3 bg-slate-900 text-slate-300 rounded-lg text-xs overflow-auto max-h-40">
                        {JSON.stringify(selectedSnapshot.config_snapshot, null, 2)}
                      </pre>
                    </div>
                    <div className="space-y-3">
                      <h4 className="text-sm font-semibold">规则快照</h4>
                      <pre className="p-3 bg-slate-900 text-slate-300 rounded-lg text-xs overflow-auto max-h-40">
                        {JSON.stringify(selectedSnapshot.rules_snapshot, null, 2)}
                      </pre>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </>
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-gray-400 p-8 text-center">
            <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mb-4">
              <FileText className="w-8 h-8 text-slate-300" />
            </div>
            <h3 className="text-lg font-medium mb-2">暂无选中项</h3>
            <p className="text-sm max-w-xs">从左侧列表中选择一个历史快照以查看详细的润色对比和当时所用的配置。</p>
          </div>
        )}
      </div>
    </div>
  )
}
