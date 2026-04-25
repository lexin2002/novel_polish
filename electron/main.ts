import { app, BrowserWindow, shell } from 'electron'
import path from 'path'
import { spawn, ChildProcess } from 'child_process'

let mainWindow: BrowserWindow | null = null
let backendProcess: ChildProcess | null = null

const VITE_DEV_SERVER_URL = process.env.VITE_DEV_SERVER_URL
const BACKEND_URL = 'http://localhost:57621'
const HEALTH_CHECK_TIMEOUT = 10000 // 10 seconds
const HEALTH_CHECK_INTERVAL = 500 // 500ms

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
      // Backend not ready yet
    }

    await new Promise(resolve => setTimeout(resolve, HEALTH_CHECK_INTERVAL))
  }

  log('error', 'Backend', `Health check timeout after ${HEALTH_CHECK_TIMEOUT}ms`)
  return false
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1200,
    minHeight: 700,
    backgroundColor: '#f9f9f9',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
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
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'))
  }

  mainWindow.on('closed', () => {
    mainWindow = null
  })
}

function startBackend(): Promise<boolean> {
  return new Promise((resolve) => {
    const backendDir = VITE_DEV_SERVER_URL
      ? path.join(__dirname, '../../backend')
      : path.join(process.resourcesPath || '', 'backend')

    const pythonCmd = process.platform === 'win32' ? 'python' : 'python3'

    log('info', 'Backend', `Starting backend from: ${backendDir}`)

    backendProcess = spawn(pythonCmd, ['-m', 'backend.main'], {
      cwd: process.cwd(),
      stdio: ['pipe', 'pipe', 'pipe'],
      env: { ...process.env, PORT: '57621' }
    })

    backendProcess?.stdout?.on('data', (data) => {
      const output = data.toString().trim()
      if (output) {
        log('info', 'Backend', output)
      }
    })

    backendProcess?.stderr?.on('data', (data) => {
      const output = data.toString().trim()
      if (output) {
        log('warn', 'Backend', output)
      }
    })

    backendProcess?.on('error', (err) => {
      log('error', 'Backend', `Process error: ${err.message}`)
    })

    backendProcess?.on('exit', (code, signal) => {
      log('info', 'Backend', `Process exited with code ${code}, signal ${signal}`)
    })

    // Give backend time to start
    setTimeout(resolve, 1000)
  })
}

app.whenReady().then(async () => {
  log('info', 'Electron', 'App ready, starting backend...')

  if (VITE_DEV_SERVER_URL) {
    // Dev mode: start backend directly
    await startBackend()
    log('info', 'Electron', 'Backend started (dev mode)')
    createWindow()
  } else {
    // Production mode: wait for health check
    await startBackend()
    log('info', 'Electron', 'Backend process started, running health check...')

    const healthy = await checkBackendHealth()

    if (healthy) {
      log('info', 'Electron', 'Backend health check passed, creating window')
      createWindow()
    } else {
      log('error', 'Electron', 'Backend health check failed, exiting')
      app.quit()
    }
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
    // SIGTERM for graceful shutdown
    backendProcess.kill('SIGTERM')

    // Force kill after 3 seconds if still running
    setTimeout(() => {
      if (backendProcess && !backendProcess.killed) {
        log('warn', 'Backend', 'Force killing backend process')
        backendProcess.kill('SIGKILL')
      }
    }, 3000)
  }
})