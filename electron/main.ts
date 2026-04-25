import { app, BrowserWindow, shell } from 'electron'
import path from 'path'
import { spawn, ChildProcess } from 'child_process'

let mainWindow: BrowserWindow | null = null
let backendProcess: ChildProcess | null = null

const VITE_DEV_SERVER_URL = process.env.VITE_DEV_SERVER_URL

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

function startBackend(): Promise<void> {
  return new Promise((resolve) => {
    const backendScript = VITE_DEV_SERVER_URL
      ? path.join(__dirname, '../../backend/main.py')
      : path.join(process.resourcesPath || '', 'backend/main.py')

    const pythonCmd = process.platform === 'win32' ? 'python' : 'python3'

    if (VITE_DEV_SERVER_URL) {
      backendProcess = spawn(pythonCmd, ['-m', 'backend.main'], {
        cwd: process.cwd(),
        stdio: ['pipe', 'pipe', 'pipe'],
        env: { ...process.env, PORT: '57621' }
      })

      backendProcess?.stderr?.on('data', (data) => {
        console.error(`[Backend] stderr: ${data}`)
      })

      backendProcess?.stdout?.on('data', (data) => {
        console.log(`[Backend] stdout: ${data}`)
      })
    } else {
      console.log(`[Backend] Production mode, backend script: ${backendScript}`)
    }

    setTimeout(resolve, 1000)
  })
}

app.whenReady().then(async () => {
  console.log('[Electron] App ready, starting backend...')

  try {
    await startBackend()
    console.log('[Electron] Backend started')
  } catch (err) {
    console.error('[Electron] Backend start failed:', err)
  }

  createWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    }
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    if (backendProcess) {
      backendProcess.kill()
    }
    app.quit()
  }
})

app.on('will-quit', () => {
  if (backendProcess) {
    backendProcess.kill()
  }
})
