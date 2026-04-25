import { useState, useEffect } from 'react'
import { BookOpen, Settings, History, FileText } from 'lucide-react'

type TabType = 'polish' | 'rules' | 'history' | 'config'

function App() {
  const [activeTab, setActiveTab] = useState<TabType>('polish')
  const [backendStatus, setBackendStatus] = useState<string>('检查中...')

  useEffect(() => {
    if (window.electronAPI) {
      setBackendStatus('Electron 环境已加载')
    } else {
      setBackendStatus('浏览器开发模式')
    }
  }, [])

  const tabs = [
    { id: 'polish' as TabType, label: '润色工作台', icon: FileText },
    { id: 'rules' as TabType, label: '规则配置中心', icon: Settings },
    { id: 'history' as TabType, label: '历史档案馆', icon: History },
    { id: 'config' as TabType, label: '配置驾驶舱', icon: BookOpen },
  ]

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="bg-white border-b border-border px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <BookOpen className="w-8 h-8 text-primary" />
            <div>
              <h1 className="text-xl font-bold text-foreground">小说智能润色工作台</h1>
              <p className="text-sm text-muted-foreground">Novel Polish - AI-Powered Writing Assistant</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-muted-foreground">
              状态: <span className="text-primary">{backendStatus}</span>
            </span>
          </div>
        </div>
      </header>

      {/* Tab Navigation */}
      <nav className="bg-white border-b border-border px-6">
        <div className="flex gap-1">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors duration-200 ${
                activeTab === tab.id
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground hover:border-border'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>
      </nav>

      {/* Main Content */}
      <main className="p-6">
        <div className="card p-8 text-center">
          <BookOpen className="w-16 h-16 text-primary mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-foreground mb-2">
            {tabs.find((t) => t.id === activeTab)?.label}
          </h2>
          <p className="text-muted-foreground">
            {activeTab === 'polish' && '粘贴原文，开始智能润色之旅'}
            {activeTab === 'rules' && '配置和管理润色规则'}
            {activeTab === 'history' && '查看历史润色记录'}
            {activeTab === 'config' && '调整系统配置'}
          </p>
        </div>
      </main>

      {/* Footer */}
      <footer className="fixed bottom-0 left-0 right-0 bg-white border-t border-border px-6 py-3">
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <span>NovelPolish v1.0.0</span>
          <span>Electron + React + TypeScript</span>
        </div>
      </footer>
    </div>
  )
}

export default App
