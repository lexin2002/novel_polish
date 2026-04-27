import { app, BrowserWindow } from 'electron'
import path from 'path'
import { spawn } from 'child_process'

let mainWindow: BrowserWindow | null = null
let backendProcess: ReturnType<typeof spawn> | null = null

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

function startBackend() {
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
}

app.whenReady().then(async () => {
  startBackend()
  const ok = await waitForBackend()
  if (ok) createWindow()
  else {
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