import { app, BrowserWindow, shell } from 'electron'
import path from 'path'
import { spawn, ChildProcess } from 'child_process'

let mainWindow: BrowserWindow | null = null
let backendProcess: ChildProcess | null = null

const VITE_DEV_SERVER_URL = process.env.VITE_DEV_SERVER_URL
const BACKEND_URL = 'http://localhost:57621'
const HEALTH_CHECK_TIMEOUT = 10000
const HEALTH_CHECK_INTERVAL = 500

// Simple __dirname replacement using app.getAppPath()
function getBasePath(): string {
  if (VITE_DEV_SERVER_URL) {
    return process.cwd()
  }
  // Production: use app.getPath('exe') directory
  return path.dirname(app.getPath('exe'))
}

function log(level: 'info' | 'error' | 'warn', source: string, message: string) {
  const timestamp = new Date().toISOString()
  console[`${level}`](`[${timestamp}] [${source}] ${message}`)
}

async function checkBackendHealth(): Promise<boolean> {
  const startTime = Date.now()

  while (Date.now() - startTime < HEALTH_CHECK_TIMEOUT) {
    try {
      const response = await fetch(`${BACKEND_URL}/api/health`)
      if (response.ok) {
        log('info', 'Backend', 'Health check passed')
        return true
      }
    } catch {
      // Backend not ready
    }
    await new Promise(resolve => setTimeout(resolve, HEALTH_CHECK_INTERVAL))
  }
  log('error', 'Backend', `Health check timeout after ${HEALTH_CHECK_TIMEOUT}ms`)
  return false
}

function createWindow() {
  const basePath = getBasePath()

  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1200,
    minHeight: 700,
    backgroundColor: '#f9f9f9',
    webPreferences: {
      preload: path.join(basePath, 'dist-electron', 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: false
    },
    show: false,
    title: '小说智能润色工作台'
  })

  mainWindow.once('ready-to-show', () => {
    mainWindow?.show()
  })

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url)
    return { action: 'deny' }
  })

  if (VITE_DEV_SERVER_URL) {
    mainWindow.loadURL(VITE_DEV_SERVER_URL)
    mainWindow.webContents.openDevTools()
  } else {
    mainWindow.loadFile(path.join(basePath, 'dist', 'index.html'))
  }

  mainWindow.on('closed', () => {
    mainWindow = null
  })
}

function startBackend(): Promise<void> {
  return new Promise((resolve) => {
    const basePath = getBasePath()
    const backendPath = path.join(basePath, 'backend')
    const pythonCmd = process.platform === 'win32' ? 'python' : 'python3'

    log('info', 'Backend', `Starting backend from: ${backendPath}`)

    backendProcess = spawn(pythonCmd, ['-m', 'backend.main'], {
      cwd: basePath,
      stdio: ['pipe', 'pipe', 'pipe'],
      env: { ...process.env, PORT: '57621' },
      detached: false
    })

    backendProcess?.stdout?.on('data', (data) => {
      const output = data.toString().trim()
      if (output) log('info', 'Backend', output)
    })

    backendProcess?.stderr?.on('data', (data) => {
      const output = data.toString().trim()
      if (output) log('warn', 'Backend', output)
    })

    backendProcess?.on('error', (err) => {
      log('error', 'Backend', `Process error: ${err.message}`)
    })

    backendProcess?.on('exit', (code, signal) => {
      log('info', 'Backend', `Process exited with code ${code}, signal ${signal}`)
    })

    setTimeout(resolve, 1000)
  })
}

app.whenReady().then(async () => {
  log('info', 'Electron', 'App ready, starting backend...')

  await startBackend()
  log('info', 'Electron', 'Backend started')

  const healthy = await checkBackendHealth()

  if (healthy) {
    log('info', 'Electron', 'Backend healthy, creating window')
    createWindow()
  } else {
    log('error', 'Electron', 'Backend health check failed')
    app.quit()
  }

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    }
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

app.on('will-quit', () => {
  log('info', 'Electron', 'App will-quit, terminating backend...')
  if (backendProcess) {
    backendProcess.kill('SIGTERM')
  }
})