import { useState, useEffect } from 'react'
import { BookOpen, Settings, History, FileText, Terminal } from 'lucide-react'
import { Sidebar } from './components/Sidebar'
import { RuleEditor } from './components/RuleEditor'
import { LogPanel } from './components/LogPanel'
import { Workbench } from './components/Workbench'

type TabType = 'polish' | 'rules' | 'history' | 'config'

function App() {
  const [activeTab, setActiveTab] = useState<TabType>('polish')
  const [backendStatus, setBackendStatus] = useState<string>('检查中...')
  const [showLogPanel, setShowLogPanel] = useState(false)

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
    { id: 'config' as TabType, label: '系统设置', icon: BookOpen },
  ]

  const toggleLogPanel = () => {
    setShowLogPanel(!showLogPanel)
  }

  const renderMainContent = () => {
    switch (activeTab) {
      case 'polish':
        return <Workbench />
      case 'rules':
        return <RuleEditor />
      case 'history':
      case 'config':
        return (
          <div className="bg-white border border-border rounded-lg p-8 text-center h-full flex flex-col items-center justify-center">
            <BookOpen className="w-16 h-16 text-primary mx-auto mb-4" />
            <h2 className="text-2xl font-bold text-foreground mb-2">
              {activeTab === 'history' ? '历史档案馆' : '系统设置'}
            </h2>
            <p className="text-muted-foreground">
              {activeTab === 'history' ? '查看历史润色记录' : '在左侧配置驾驶舱中调整系统参数'}
            </p>
          </div>
        )
      default:
        return null
    }
  }

  return (
    <div className="min-h-screen bg-background flex">
      {/* Left Sidebar - Config Cockpit */}
      {activeTab === 'config' && <Sidebar />}

      {/* Main Area */}
      <div className="flex-1 flex flex-col">
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
              <button
                onClick={toggleLogPanel}
                className={`flex items-center gap-1 px-3 py-1.5 text-sm rounded transition-colors ${
                  showLogPanel
                    ? 'bg-primary text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
                title="实时日志面板"
              >
                <Terminal className="w-4 h-4" />
                日志
              </button>
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
        <main className="flex-1 overflow-hidden">
          {renderMainContent()}
        </main>

        {/* Log Panel - Bottom Drawer */}
        {showLogPanel && (
          <div className="h-64 border-t border-border bg-[#f4f4f4]">
            <LogPanel />
          </div>
        )}

        {/* Footer */}
        <footer className="bg-white border-t border-border px-6 py-3">
          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <span>NovelPolish v1.0.0</span>
            <span>Electron + React + TypeScript</span>
          </div>
        </footer>
      </div>
    </div>
  )
}

export default App
