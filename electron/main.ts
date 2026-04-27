import { app, BrowserWindow, ipcMain } from 'electron'
import path from 'path'
import { spawn, ChildProcess } from 'child_process'

let mainWindow: BrowserWindow | null = null
let backendProcess: ChildProcess | null = null
let restartAttempts = 0
const MAX_RESTARTS = 3

const isDev = !!process.env.VITE_DEV_SERVER_URL

function log(level: 'info' | 'error' | 'warn', msg: string) {
  console[level](`[${new Date().toISOString()}] [${level.toUpperCase()}] ${msg}`)
}

async function waitForBackend(): Promise<boolean> {
  const timeout = 10000
  const start = Date.now()
  while (Date.now() - start < timeout) {
    try {
      const res = await fetch('http://localhost:57621/api/health')
      if (res.ok) return true
    } catch (_e) {
      // ignore and retry
    }
    await new Promise(r => setTimeout(r, 500))
  }
  return false
}

function createWindow() {
  const baseDir = isDev ? process.cwd() : path.dirname(app.getPath('exe'))

  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    backgroundColor: '#f9f9f9',
    webPreferences: {
      preload: path.join(baseDir, 'dist-electron', 'preload.mjs'),
      nodeIntegration: false,
      contextIsolation: true
    },
    show: false,
    title: '小说智能润色工作台'
  })

  mainWindow.once('ready-to-show', () => mainWindow?.show())

  if (isDev) {
    mainWindow.loadURL('http://localhost:5173')
    mainWindow.webContents.openDevTools()
  } else {
    mainWindow.loadFile(path.join(baseDir, 'dist', 'index.html'))
  }

  mainWindow.on('closed', () => { mainWindow = null })
}

// ─── IPC Handlers (响应 preload.ts 的 electronAPI 调用) ────────────────

ipcMain.handle('start-backend', async () => {
  if (backendProcess) return { status: 'already-running' }
  startBackend()
  return { status: 'started' }
})

ipcMain.handle('stop-backend', async () => {
  if (backendProcess) {
    backendProcess.kill('SIGTERM')
    backendProcess = null
  }
  return { status: 'stopped' }
})

ipcMain.handle('get-backend-status', async () => {
  return { running: backendProcess !== null, url: 'http://localhost:57621' }
})

// ─── Backend Process Management ──────────────────────────────────────

function startBackend() {
  if (backendProcess) {
    log('warn', 'Backend is already running, skipping start')
    return
  }

  const python = process.platform === 'win32' ? 'python' : 'python3'
  const baseDir = isDev ? process.cwd() : path.dirname(app.getPath('exe'))
  const backendDir = path.join(baseDir, 'backend')

  log('info', `Starting backend from: ${backendDir}`)

  // Set PYTHONPATH to include backend directory
  const pythonPath = isDev 
    ? `${baseDir}:${path.delimiter}${process.env.PYTHONPATH || ''}`
    : `${baseDir}${path.delimiter}${baseDir}`

  backendProcess = spawn(python, ['app/main.py'], {
    cwd: backendDir,
    env: { ...process.env, PORT: '57621', PYTHONPATH: pythonPath },
    stdio: 'pipe'
  })

  backendProcess.stdout?.on('data', (data) => log('info', data.toString().trim()))
  backendProcess.stderr?.on('data', (data) => log('warn', data.toString().trim()))

  // 子进程退出监听（含自动重启）
  backendProcess.on('exit', (code) => {
    log('warn', `Backend exited with code ${code}`)
    backendProcess = null

    if (code !== null && code !== 0 && restartAttempts < MAX_RESTARTS) {
      restartAttempts++
      log('info', `Restarting backend (attempt ${restartAttempts}/${MAX_RESTARTS})...`)
      setTimeout(() => startBackend(), 2000)
    }
  })

  backendProcess.on('error', (err) => {
    log('error', `Backend spawn error: ${err.message}`)
    backendProcess = null
  })
}

app.whenReady().then(async () => {
  startBackend()
  const ok = await waitForBackend()
  if (ok) {
    restartAttempts = 0 // Reset on successful start
    createWindow()
  } else {
    // Wait 2s for graceful shutdown before force quit
    console.log('Backend failed to start, exiting...')
    setTimeout(() => {
      backendProcess?.kill('SIGTERM')
      app.exit(1)
    }, 2000)
  }
})

app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit() })
app.on('will-quit', () => { backendProcess?.kill() })