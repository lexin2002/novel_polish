import * as React from 'react'

export interface ProgressInfo {
  chunk: number
  totalChunks: number
  iteration: number
  totalIterations: number
  message?: string
}

interface ProgressBarProps {
  progress: ProgressInfo | null
  idleText?: string
  className?: string
}

export const ProgressBar: React.FC<ProgressBarProps> = ({
  progress,
  idleText = '等待开始润色任务...',
  className = 'px-4 py-2 bg-gray-50 border-b border-border',
}) => {
  if (!progress) {
    return (
      <div className={className}>
        <span className="text-sm text-gray-400">{idleText}</span>
      </div>
    )
  }

  const { chunk, totalChunks, iteration, totalIterations, message } = progress
  const totalProgress = totalChunks > 0 && totalIterations > 0
    ? ((chunk * totalIterations + iteration) / (totalChunks * totalIterations)) * 100
    : 0

  return (
    <div className={className}>
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
